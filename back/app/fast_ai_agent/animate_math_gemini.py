# animate_math_gemini.py
# ------------------------------------------------------------
# TWO-STAGE GENERATION PIPELINE
#   1) Translate user's Japanese request -> concise English prompt
#      (Gemini 2.5 Flash-Lite)
#   2) Feed the English prompt + reference code bundles to
#      Gemini 2.5 Pro to generate the final Manim code.
#
# NEW:
#   3) If manim run fails, send CURRENT CODE + ERROR LOG to
#      gemini-2.5-flash and request a minimal unified-diff patch.
#      Apply the patch (only the target parts), then retry manim.
#
# Reference .py files under a directory are bundled and shown
# to the generator as "code_bundles". The generated code is
# sanitized, guarded, compiled, and then rendered by manim.
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import ast
import os
import re
import shlex
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, List


# ===== .env ロード =====
def load_api_key_from_dotenv(env_path: Optional[str] = None) -> str:
    try:
        from dotenv import load_dotenv, find_dotenv  # pip install python-dotenv
    except Exception as e:
        raise RuntimeError(
            "google-generativeai を使う前に python-dotenv をインストールしてください: pip install python-dotenv"
        ) from e

    loaded_path = None
    if env_path:
        if not os.path.exists(env_path):
            raise RuntimeError(f"--env-file で指定した .env が存在しません: {env_path}")
        load_dotenv(env_path)
        loaded_path = env_path
    else:
        found = find_dotenv(usecwd=True)
        if found:
            load_dotenv(found)
            loaded_path = found
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "環境変数 GEMINI_API_KEY が見つかりません。.env に GEMINI_API_KEY=... を設定してください。"
        )
    if loaded_path:
        print(f"[.env] loaded from: {loaded_path}")
    return key


# ===== prompts.toml =====
def load_prompts_toml(path: Optional[str]) -> Dict:
    p = Path(path or "prompts.toml")
    if not p.exists():
        return {}
    try:
        if sys.version_info >= (3, 11):
            import tomllib

            with open(p, "rb") as f:
                return tomllib.load(f)
        else:
            import tomli  # type: ignore

            with open(p, "rb") as f:
                return tomli.load(f)
    except Exception as e:
        print(f"[warn] TOML parse failed: {e}")
        return {}


def safe_fill(tpl: str, **kwargs) -> str:
    try:
        return tpl.format(**kwargs)
    except KeyError as e:
        miss = e.args[0]
        return tpl.replace("{" + miss + "}", f"<{miss}:MISSING>")


# ===== Gemini API ラッパ（テキスト生成のみ） =====
def create_gemini_model(name: str, api_key: str):
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError(
            "google-generativeai をインストールしてください: pip install google-generativeai"
        ) from e
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(name)


def gemini_generate_text(model, prompt: str) -> str:
    resp = model.generate_content(prompt)
    return getattr(resp, "text", "") or ""


# ===== 参照コード読み込み =====
def read_reference_templates(refdir: str) -> Dict[str, str]:
    d = Path(refdir)
    if not d.exists():
        raise SystemExit(f"参照ディレクトリが見つかりません: {refdir}")
    out: Dict[str, str] = {}
    for p in sorted(d.glob("*.py")):
        try:
            out[p.name] = p.read_text(encoding="utf-8")
        except Exception:
            continue
    return out


# ===== ガード類 =====
FORBIDDEN_IMPORTS = re.compile(
    r"^\s*import\s+(os|sys|pathlib|subprocess|shutil|inspect)\b|^\s*from\s+(os|sys|pathlib|subprocess|shutil|inspect)\s+import\b",
    flags=re.MULTILINE,
)


def strip_forbidden_imports(code: str) -> str:
    return FORBIDDEN_IMPORTS.sub("# [stripped forbidden import]", code)


# MathTex の f-string 禁止（LaTeX の { } と衝突しやすい）
_MATHTEX_CALL = re.compile(r"(MathTex|Tex)\s*\(\s*f(['\"])", flags=re.DOTALL)


def _convert_mathtex(m: re.Match) -> str:
    head = m.group(1) + "("
    quote = m.group(2)
    text = m.string[m.end() :]
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                break
            depth -= 1
        i += 1
    inner = text[:i]
    # f"{...}" を "..." + str(...) + "..." に
    parts = []
    s = inner
    j = 0
    while j < len(s):
        if s[j : j + 1] == "{":
            k = s.find("}", j + 1)
            if k == -1:
                break
            expr = s[j + 1 : k].strip()
            parts.append(f"str({expr})")
            j = k + 1
        else:
            k = s.find("{", j)
            if k == -1:
                k = len(s)
            body = s[j:k].replace("\\", "\\\\").replace(quote, "\\" + quote)
            parts.append(f'r"{body}"')
            j = k
    expr = " + ".join(parts) if parts else 'r""'
    return f"{head}{expr})"


def ban_fstrings_in_mathtex(code: str) -> str:
    return _MATHTEX_CALL.sub(_convert_mathtex, code)


def force_class_name(code: str) -> str:
    return re.sub(
        r"class\s+\w+\s*\(\s*Scene\s*\)\s*:",
        "class GeneratedScene(Scene):",
        code,
        count=1,
    )


def ban_tex_usage(code: str) -> tuple[bool, str]:
    bad = []
    for m in re.finditer(r'Tex\s*\(\s*([rRuU]?[\'"])(.*?)\1', code, re.DOTALL):
        s = m.group(2)
        if re.search(r"[^\x00-\x7F]", s):  # 非ASCIIを含む
            bad.append(s[:30])
    if bad:
        return (
            False,
            "Tex() に日本語など非ASCIIが含まれています。日本語は Text を使ってください。",
        )
    return True, ""


def sanitize(code: str) -> str:
    code = strip_forbidden_imports(code)
    code = force_class_name(code)
    return code


# ===== Manim 0.19 compatibility patcher (static replacements) =====
_PLOT_MINMAX = re.compile(
    r"(\b[A-Za-z_][A-Za-z0-9_]*\s*\.\s*plot\s*\(\s*[^,]+),(?P<rest>[^)]*?)\)",
    flags=re.DOTALL,
)


def _fix_plot_minmax(m):
    head, rest = m.group(1), m.group("rest")
    xmin = re.search(r"\bx_min\s*=\s*([^,)\s]+)", rest)
    xmax = re.search(r"\bx_max\s*=\s*([^,)\s]+)", rest)
    if xmin and xmax:
        rest = re.sub(r"\bx_min\s*=\s*([^,)\s]+)\s*,?\s*", "", rest)
        rest = re.sub(r"\bx_max\s*=\s*([^,)\s]+)\s*,?\s*", "", rest)
        xr = f"x_range=[{xmin.group(1)}, {xmax.group(1)}]"
        if rest.strip():
            rest = xr + ", " + rest.strip().strip(",")
        else:
            rest = xr
    return head + ", " + rest + ")"


_AXES_MINMAX = re.compile(r"\bAxes\s*\((?P<args>.*?)\)", flags=re.DOTALL)


def _fix_axes_minmax(args):
    def take(key):
        m = re.search(rf"\b{key}\s*=\s*([^,)\s]+)", args)
        return m.group(1) if m else None

    xmin, xmax = take("x_min"), take("x_max")
    ymin, ymax = take("y_min"), take("y_max")
    out = args
    for k in ("x_min", "x_max", "y_min", "y_max"):
        out = re.sub(rf"\b{k}\s*=\s*([^,)\s]+)\s*,?\s*", "", out)
    if xmin and xmax and "x_range" not in out:
        out = f"x_range=[{xmin}, {xmax}, 1], " + out.strip().strip(",")
    if ymin and ymax and "y_range" not in out:
        out = f"y_range=[{ymin}, {ymax}, 1], " + out.strip().strip(",")
    return out


def patch_manim_019_compat(code: str) -> tuple[str, list[str]]:
    import textwrap

    log: list[str] = []
    new_code = _PLOT_MINMAX.sub(_fix_plot_minmax, code)
    if new_code != code:
        log.append("plot(): x_min/x_max -> x_range patched")
    code = new_code

    def axes_repl(m):
        new_args = _fix_axes_minmax(m.group("args"))
        return f"Axes({new_args})"

    new_code = _AXES_MINMAX.sub(axes_repl, code)
    if new_code != code:
        log.append("Axes(): *_min/*_max -> *_range patched")
    code = new_code
    before = code
    code = re.sub(r"\bHGroup\s*\(", "VGroup(", code)
    if code != before:
        log.append("HGroup -> VGroup patched")
    before = code
    code = re.sub(
        r'([xy]_axis_config\s*=\s*\{[^}]*?)((?:["\'])?add_tick_labels(?:["\'])?\s*:\s*)(True|False)',
        r'\1"include_numbers": \3',
        code,
    )
    if code != before:
        log.append("Axis config: add_tick_labels -> include_numbers patched")
    before = code
    code = re.sub(
        r"\brate_func\s*=\s*easeInOutSine\b", "rate_func=ease_in_out_sine", code
    )
    code = re.sub(r"\brate_func\s*=\s*easeInSine\b", "rate_func=ease_in_sine", code)
    code = re.sub(r"\brate_func\s*=\s*easeOutSine\b", "rate_func=ease_out_sine", code)
    if code != before:
        log.append("rate_func: CamelCase -> snake_case patched (sine easings)")
    before = code
    code = re.sub(r",\s*aligned_edge\s*=\s*CENTER\b", "", code)
    if code != before:
        log.append("arrange(..., aligned_edge=CENTER) removed")
    before = code
    code = re.sub(r"(\balign_to\([^,]+,\s*)CENTER\b", r"\1ORIGIN", code)
    if code != before:
        log.append("align_to(..., CENTER) -> align_to(..., ORIGIN) patched")
    if "Angle(" in code and "_safe_Angle_injected" not in code:
        helper = (
            textwrap.dedent(
                r"""
            # --- injected: safe Angle wrapper to avoid parallel/colinear crash ---
            _safe_Angle_injected = True
            def _safe_Angle(obj1, obj2, **kwargs):
                try:
                    l1 = Line(obj1.get_start(), obj1.get_end())
                    l2 = Line(obj2.get_start(), obj2.get_end())
                    v1 = l1.get_end() - l1.get_start()
                    v2 = l2.get_end() - l2.get_start()
                    cross = v1[0]*v2[1] - v1[1]*v2[0]
                    if abs(cross) < 1e-7:
                        return VGroup()
                    return Angle(l1, l2, **kwargs)
                except Exception:
                    return VGroup()
            """
            ).strip()
            + "\n"
        )
        m = re.search(r"(^|\n)(from\s+manim\s+import\s+\*.*?\n)", code)
        if m:
            insert_at = m.end()
            code = code[:insert_at] + helper + code[insert_at:]
        else:
            code = helper + code
        code = re.sub(r"\bAngle\s*\(", "_safe_Angle(", code)
        log.append("Angle(): wrapped with _safe_Angle to avoid parallel/colinear crash")
    return code, log


def py_compile_check(code: str) -> Tuple[bool, Optional[str]]:
    try:
        compile(code, "<generated>", "exec")
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


# ===== strict guard (ast で危険構文を弾く) =====
def strict_guard_check(code: str) -> Tuple[bool, Optional[str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            top = (
                n.names[0].name if isinstance(n, ast.Import) else (n.module or "")
            ).split(".")[0]
            if top in {"os", "sys", "pathlib", "subprocess", "shutil", "inspect"}:
                return False, f"Forbidden import: {top}"
        if isinstance(n, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "config" for t in n.targets):
                return False, "Direct assignment to config is prohibited."
    return True, None


# ===== Gemini プロンプト（デフォルト） =====
DEFAULT_JA2EN_PROMPT = """
You are a precise technical translator and prompt composer.
Translate the following Japanese description into concise English for a Manim scene request.
Keep essential math terms, remove fluff, and keep it under 100 words.

[Japanese]
{ja_text}
"""

DEFAULT_SINGLE_EDIT_EN = r"""
You are a senior Manim engineer (v0.19.0, Community).
Task: Write ONE self-contained Python file that defines exactly ONE class `GeneratedScene(Scene)` and nothing else.
Follow these HARD RULES:

[HARD RULES]
- Use **manim==0.19.0** API strictly.
- One class only: `class GeneratedScene(Scene):`
- No external files, no I/O, no images, no sounds.
- Set a white background (config.background_color=WHITE is NOT allowed; use self.camera.background_color=WHITE in construct()).
- Use only `from manim import *` and `import numpy as np` (optionally `import math`).
- Render vectors/axes using 0.19-safe constructs (e.g., `DashedVMobject(..., num_dashes=...)`).
- Do not use deprecated params like `x_min/x_max` for Axes or plot; use x_range/y_range and x_range for plot.
- All math angles are radians unless degree text labeling is explicitly asked; when showing degrees in text, convert from radians, e.g.:
  MathTex(r"\\theta=" + str(val) + r"^\\circ").
- **Only import manim, numpy, math**. Do not import: os, sys, pathlib, subprocess, shutil, inspect.
- **Do not assign to config.***; no external file I/O.
- Allowed colors: WHITE, GRAY, YELLOW, BLUE, RED, GREEN, ORANGE, PURPLE.
- Assume Manim 0.19.0 API.

[HOW TO USE REFERENCES]
- The **reference code bundles** below (multiple .py) are examples you can adapt.
- Your final answer must be a **single file** with one `GeneratedScene`.

[REQUEST]
{single_request_en}

[REFERENCE CODE BUNDLES]
{code_bundles}

[OUTPUT FORMAT]
- Reply ONLY with Python code. No explanation or backticks.
- The file must import `from manim import *` and define class `GeneratedScene(Scene)`.
"""

# ===== 失敗時パッチ生成プロンプト =====
PATCH_PROMPT = r"""
You are a senior Python/Manim engineer. The Manim version is 0.19.0 (Community).

Goal: Produce a **minimal unified-diff patch** that fixes the runtime error(s) without rewriting the whole file.
Patch only the necessary lines. Keep the overall structure and style unchanged.

[HARD RULES]
- Keep exactly ONE class: `GeneratedScene(Scene)`.
- Use only: `from manim import *`, `import numpy as np`, optional `import math`.
- No forbidden imports: os, sys, pathlib, subprocess, shutil, inspect.
- Do not assign to `config`.
- Use Manim 0.19.0 APIs (x_range/y_range, snake_case rate functions).
- Prefer adding try/except guards over big refactors.
- If MathTex has dynamic numbers, prefer DecimalNumber.
- Avoid non-ASCII in Tex/MathTex strings.

[CURRENT FILE: generated_scene.py]
{current_code}

[ERROR LOG (tail)]
{error_tail}

[OUTPUT FORMAT]
- Output ONLY a **unified diff**. No prose, no code fences.
- Must start with:
  --- a/generated_scene.py
  +++ b/generated_scene.py
  @@ ...
- Keep the patch as small as possible. Do not reformat unrelated lines.
"""


@dataclass
class ManimCfg:
    out: Path
    resolution: str = "640x360"
    fps: int = 20
    quality: str = "m"  # l/m/h/k


def run_manim_capture(scene_path: Path, cfg: ManimCfg) -> Tuple[int, str, str]:
    """Run manim and capture stdout/stderr."""
    qflag = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}.get(cfg.quality, "-qm")
    w, h = cfg.resolution.split("x")
    cmd = f"manim {qflag} -r {int(w)},{int(h)} --fps {int(cfg.fps)} -o {shlex.quote(str(cfg.out))} {shlex.quote(str(scene_path))} GeneratedScene"
    print("[manim]", cmd)
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_log_dir() -> Path:
    from datetime import datetime, timezone, timedelta

    base = Path("log")
    base.mkdir(exist_ok=True)
    jst = timezone(timedelta(hours=9))
    ts = datetime.now(jst).strftime("%Y%m%d_%H%M%S")
    d = base / ts
    d.mkdir(exist_ok=True)
    print(f"[log] directory: {d}")
    return d


def normalize_generated_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:python)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


# ===== unified diff パッチ適用器（最小実装） =====
_HUNK_RE = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@")


def _strip_diff_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:diff)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def apply_unified_diff(original: str, diff_text: str) -> Tuple[bool, str, str]:
    """
    Apply a unified diff to original text. Returns (applied, new_text, reason).
    Only supports a single-file diff targeting generated_scene.py.
    """
    diff_text = _strip_diff_fences(diff_text)
    if not diff_text:
        return False, original, "empty diff"
    lines = diff_text.splitlines()
    # optional headers
    i = 0
    saw_header = False
    if i < len(lines) and lines[i].startswith("--- "):
        saw_header = True
        i += 1
    if i < len(lines) and lines[i].startswith("+++ "):
        i += 1
    # Parse hunks
    orig_lines = original.splitlines(keepends=False)
    new_lines: List[str] = []
    idx = 0  # 0-based pointer in original
    any_hunk = False
    while i < len(lines):
        m = _HUNK_RE.match(lines[i])
        if not m:
            # tolerate noise (e.g., model accidentally adds blank line)
            if lines[i].strip() == "":
                i += 1
                continue
            # if we haven't seen any hunk yet, bail
            if not any_hunk:
                return False, original, f"not a unified diff (line={lines[i][:40]!r})"
            else:
                # otherwise treat remaining as noise
                break
        any_hunk = True
        i += 1
        start_old = int(m.group(1)) - 1  # convert to 0-based
        # flush unchanged up to start_old
        if start_old < idx or start_old > len(orig_lines):
            return False, original, "hunk position out of range"
        new_lines.extend(orig_lines[idx:start_old])
        idx = start_old
        # now process hunk lines
        while i < len(lines):
            if lines[i].startswith("@@"):
                break
            if not lines[i]:
                # blank context line
                new_lines.append("")
                if idx < len(orig_lines):
                    idx += 1  # treat as context without marker? (rare)
                i += 1
                continue
            tag = lines[i][0]
            content = lines[i][1:]
            if tag == " ":
                # context, must match
                if idx >= len(orig_lines):
                    return False, original, "context beyond EOF"
                # be lenient: don't hard-check equality (model might trim spaces)
                new_lines.append(orig_lines[idx])
                idx += 1
            elif tag == "-":
                # deletion
                if idx >= len(orig_lines):
                    return False, original, "deletion beyond EOF"
                idx += 1
            elif tag == "+":
                # insertion
                new_lines.append(content)
            else:
                # unexpected line tag
                return False, original, f"unexpected diff tag: {tag!r}"
            i += 1
    # append the rest
    new_lines.extend(orig_lines[idx:])
    if not any_hunk:
        return False, original, "no hunks found"
    return True, "\n".join(new_lines) + ("\n" if original.endswith("\n") else ""), ""


# ===== パッチ用プロンプト作成 =====
def build_patch_prompt(current_code: str, error_tail: str) -> str:
    return safe_fill(PATCH_PROMPT, current_code=current_code, error_tail=error_tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--topic", required=True, help="日本語の要求文（高校数学の説明など）"
    )
    ap.add_argument("--prompts-file", default="prompts.toml")
    ap.add_argument("--ref-dir", default="manimコード")
    ap.add_argument("--out", default="preview.mp4")
    ap.add_argument("--quality", default="l", choices=("l", "m", "h", "k"))
    ap.add_argument("--resolution", default="640x360")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--model", default="")
    ap.add_argument("--translator-model", default="")
    ap.add_argument("--generator-model", default="")
    ap.add_argument("--env-file", default=None)
    ap.add_argument(
        "--no-translate",
        action="store_true",
        help="翻訳をスキップ（入力をそのまま英語として扱う）",
    )
    ap.add_argument("--no-save-prompts", action="store_true")
    # NEW: patch options
    ap.add_argument(
        "--patch-model",
        default="gemini-2.5-flash",
        help="manim失敗時のパッチ生成に使うモデル名",
    )
    ap.add_argument(
        "--max-patch-attempts", type=int, default=3, help="パッチ適用の最大試行回数"
    )
    args = ap.parse_args()

    logdir = ensure_log_dir()
    api_key = load_api_key_from_dotenv(args.env_file)
    prompts = load_prompts_toml(args.prompts_file)

    # 参照コードの読み込み
    templates = read_reference_templates(args.ref_dir)
    if not templates:
        raise SystemExit(f"{args.ref_dir}/ 配下に参照用の *.py が見つかりません。")
    code_bundles = "\n".join(
        [f"[{fname} (full text)]\n{txt}" for fname, txt in sorted(templates.items())]
    )

    # ===== Stage 1: JA -> EN =====
    ja_text = args.topic
    if args.no_translate:
        en_request = ja_text
    else:
        ja2en_tpl = prompts.get("ja2en", {}).get("template", DEFAULT_JA2EN_PROMPT)
        ja2en_prompt = safe_fill(ja2en_tpl, ja_text=ja_text)
        if not args.no_save_prompts:
            (logdir / "ja2en_prompt.txt").write_text(ja2en_prompt, encoding="utf-8")
        translator_model_name = (
            args.model or args.translator_model
        ) or "gemini-2.5-flash-lite"
        model = create_gemini_model(translator_model_name, api_key)
        en_request = gemini_generate_text(model, ja2en_prompt)
        (logdir / "ja2en.txt").write_text(en_request, encoding="utf-8")

    # ===== Stage 2: Code generation =====
    single_tpl = prompts.get("single_edit_en", {}).get(
        "template", DEFAULT_SINGLE_EDIT_EN
    )
    missing_req = ("{single_request_en}" not in single_tpl) and (
        "{user_request}" not in single_tpl
    )
    if missing_req:
        print(
            "[warn] prompts.single_edit_en.template is missing both {single_request_en} and {user_request}. Fallback to DEFAULT_SINGLE_EDIT_EN."
        )
        single_tpl = DEFAULT_SINGLE_EDIT_EN

    single_prompt_en = safe_fill(
        single_tpl,
        single_request_en=en_request,
        user_request=en_request,
        code_bundles=code_bundles,
    )
    if not args.no_save_prompts:
        (logdir / "single_prompt_en.txt").write_text(single_prompt_en, encoding="utf-8")

    generator_model_name = args.model or args.generator_model or "gemini-2.5-pro"
    model = create_gemini_model(generator_model_name, api_key)
    raw = gemini_generate_text(model, single_prompt_en)
    (logdir / "raw_single.txt").write_text(raw, encoding="utf-8")

    code = normalize_generated_code(raw)
    code = sanitize(code)

    # --- Manim 0.19 compatibility patcher (one-time only before first run) ---
    code, _compat_log = patch_manim_019_compat(code)
    if _compat_log:
        (logdir / "compat_patcher.log").write_text(
            "\n".join(_compat_log), encoding="utf-8"
        )

    ok_tex, tex_reason = ban_tex_usage(code)
    ok_syn, syn_reason = py_compile_check(code)
    ok_guard, guard_reason = strict_guard_check(code)
    (logdir / "generated_scene.initial.py").write_text(code, encoding="utf-8")

    if not (ok_tex and ok_syn and ok_guard):
        msgs = []
        if not ok_tex:
            msgs.append(tex_reason)
        if not ok_syn and syn_reason:
            msgs.append(syn_reason)
        if not ok_guard and guard_reason:
            msgs.append(guard_reason)
        print("⚠ 生成コードに問題があります:\n- " + "\n- ".join(msgs))
        # ここでは終了せず、とりあえず manim に投げて詳細をログで確認可能にする

    # ===== manim 実行 =====
    scene_path = logdir / "generated_scene.py"
    scene_path.write_text(code, encoding="utf-8")
    rc, out, err = run_manim_capture(
        scene_path,
        ManimCfg(
            out=Path(args.out),
            resolution=args.resolution,
            fps=args.fps,
            quality=args.quality,
        ),
    )
    (logdir / "manim_stdout_0.txt").write_text(out, encoding="utf-8")
    (logdir / "manim_stderr_0.txt").write_text(err, encoding="utf-8")

    # ===== 失敗時: パッチ処理 & 再実行ループ =====
    attempt = 0
    if rc != 0:
        print("⚠ manim 実行失敗。自動パッチを試みます。")
    while rc != 0 and attempt < max(0, args.max_patch_attempts):
        attempt += 1
        # 直近エラー末尾のみ抽出（あまり長すぎるとプロンプトが膨らむ）
        tail = err or "(no stderr)"
        # guard系のエラーもあれば追記
        guard_msgs: List[str] = []
        ok_guard, guard_reason = strict_guard_check(code)
        if not ok_guard and guard_reason:
            guard_msgs.append(guard_reason)
        ok_syn, syn_reason = py_compile_check(code)
        if not ok_syn and syn_reason:
            guard_msgs.append(syn_reason)
        ok_tex, tex_reason = ban_tex_usage(code)
        if not ok_tex and tex_reason:
            guard_msgs.append(tex_reason)
        if guard_msgs:
            tail = tail + "\n\n[STATIC CHECKS]\n- " + "\n- ".join(guard_msgs)

        patch_prompt = build_patch_prompt(code, tail)
        if not args.no_save_prompts:
            (logdir / f"patch_prompt_{attempt}.txt").write_text(
                patch_prompt, encoding="utf-8"
            )

        patch_model = create_gemini_model(
            args.patch_model or "gemini-2.5-flash", api_key
        )
        diff_text = gemini_generate_text(patch_model, patch_prompt)
        (logdir / f"patch_diff_{attempt}.diff").write_text(diff_text, encoding="utf-8")

        applied, new_code, reason = apply_unified_diff(code, diff_text)
        if not applied:
            (logdir / f"patch_apply_{attempt}.log").write_text(
                f"APPLY FAILED: {reason}", encoding="utf-8"
            )
            print(f"⚠ パッチ適用失敗（{reason}）。再試行します...")
            # 失敗した場合も別案を求めるためループ継続（同じ attempt カウントは進む）
            continue

        # 追加のサニタイズ（禁則のみ）：過剰変換は避ける
        new_code = strip_forbidden_imports(new_code)
        # class 名の安全化
        new_code = force_class_name(new_code)

        # 保存＆再実行
        (logdir / f"generated_scene.after_patch_{attempt}.py").write_text(
            new_code, encoding="utf-8"
        )
        scene_path.write_text(new_code, encoding="utf-8")
        rc, out, err = run_manim_capture(
            scene_path,
            ManimCfg(
                out=Path(args.out),
                resolution=args.resolution,
                fps=args.fps,
                quality=args.quality,
            ),
        )
        (logdir / f"manim_stdout_{attempt}.txt").write_text(out, encoding="utf-8")
        (logdir / f"manim_stderr_{attempt}.txt").write_text(err, encoding="utf-8")
        code = new_code  # 次のループではこの内容をベースにさらにパッチする

    if rc != 0:
        print(
            "❌ すべてのパッチ試行でも manim が失敗しました。最終コードとエラーログは以下に保存されています。"
        )
        print(f"   {scene_path}")
        sys.exit(rc)

    print("✅ 完了")


if __name__ == "__main__":
    main()
