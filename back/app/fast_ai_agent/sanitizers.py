from __future__ import annotations

import ast
import re
import textwrap
from typing import List, Tuple

FORBIDDEN_IMPORTS = re.compile(
    r"^\s*import\s+(os|sys|pathlib|subprocess|shutil|inspect)\b|^\s*from\s+(os|sys|pathlib|subprocess|shutil|inspect)\s+import\b",
    flags=re.MULTILINE,
)

_MATHTEX_CALL = re.compile(r"(MathTex|Tex)\s*\(\s*f(['\"])", flags=re.DOTALL)


def strip_forbidden_imports(code: str) -> str:
    return FORBIDDEN_IMPORTS.sub("# [stripped forbidden import]", code)


def _convert_mathtex(match: re.Match) -> str:
    head = match.group(1) + "("
    quote = match.group(2)
    text = match.string[match.end() :]
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
    bad: List[str] = []
    for match in re.finditer(r"Tex\s*\(\s*([rRuU]?[\'\"])(.*?)\1", code, re.DOTALL):
        snippet = match.group(2)
        if re.search(r"[^\x00-\x7F]", snippet):
            bad.append(snippet[:30])
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


_PLOT_MINMAX = re.compile(
    r"(\b[A-Za-z_][A-Za-z0-9_]*\s*\.\s*plot\s*\(\s*[^,]+),(?P<rest>[^)]*?)\)",
    flags=re.DOTALL,
)

_AXES_MINMAX = re.compile(r"\bAxes\s*\((?P<args>.*?)\)", flags=re.DOTALL)


def _fix_plot_minmax(match: re.Match) -> str:
    head, rest = match.group(1), match.group("rest")
    xmin = re.search(r"\bx_min\s*=\s*([^,)\s]+)", rest)
    xmax = re.search(r"\bx_max\s*=\s*([^,)\s]+)", rest)
    if xmin and xmax:
        rest = re.sub(r"\bx_min\s*=\s*([^,)\s]+)\s*,?\s*", "", rest)
        rest = re.sub(r"\bx_max\s*=\s*([^,)\s]+)\s*,?\s*", "", rest)
        xr = f"x_range=[{xmin.group(1)}, {xmax.group(1)}]"
        rest = (xr + ", " + rest.strip().strip(",")) if rest.strip() else xr
    return head + ", " + rest + ")"


def _take_arg(args: str, key: str):
    match = re.search(rf"\b{key}\s*=\s*([^,)\s]+)", args)
    return match.group(1) if match else None


def _fix_axes_minmax(args: str) -> str:
    xmin, xmax = _take_arg(args, "x_min"), _take_arg(args, "x_max")
    ymin, ymax = _take_arg(args, "y_min"), _take_arg(args, "y_max")
    out = args
    for key in ("x_min", "x_max", "y_min", "y_max"):
        out = re.sub(rf"\b{key}\s*=\s*([^,)\s]+)\s*,?\s*", "", out)
    if xmin and xmax and "x_range" not in out:
        out = f"x_range=[{xmin}, {xmax}, 1], " + out.strip().strip(",")
    if ymin and ymax and "y_range" not in out:
        out = f"y_range=[{ymin}, {ymax}, 1], " + out.strip().strip(",")
    return out


def patch_manim_018_compat(code: str) -> tuple[str, List[str]]:
    """
    Heuristically rewrite common patterns to be safer for manim==0.18.1,
    and inject safe helpers for Angle + angle labels.

    Returns:
        (patched_code, log_messages)
    """
    log: List[str] = []

    # --- plot(x_min=..., x_max=...) -> plot(..., x_range=[..., ...]) ---
    new_code = _PLOT_MINMAX.sub(_fix_plot_minmax, code)
    if new_code != code:
        log.append("plot(): x_min/x_max -> x_range patched")
    code = new_code

    # --- Axes(x_min=..., x_max=..., y_min=..., y_max=...) -> Axes(x_range=[...], y_range=[...]) ---
    def axes_repl(match: re.Match) -> str:
        return f"Axes({_fix_axes_minmax(match.group('args'))})"

    new_code = _AXES_MINMAX.sub(axes_repl, code)
    if new_code != code:
        log.append("Axes(): *_min/*_max -> *_range patched")
    code = new_code

    # --- HGroup -> VGroup (HGroup is not available in 0.18.1) ---
    before = code
    code = re.sub(r"\bHGroup\s*\(", "VGroup(", code)
    if code != before:
        log.append("HGroup -> VGroup patched")

    # --- add_tick_labels -> include_numbers for axis configs ---
    before = code
    code = re.sub(
        r'([xy]_axis_config\s*=\s*\{[^}]*?)((?:["\'])?add_tick_labels(?:["\'])?\s*:\s*)(True|False)',
        r'\1"include_numbers": \3',
        code,
    )
    if code != before:
        log.append("Axis config: add_tick_labels -> include_numbers patched")

    # --- rate_func camelCase -> snake_case ---
    before = code
    code = re.sub(r"\brate_func\s*=\s*easeInOutSine\b", "rate_func=ease_in_out_sine", code)
    code = re.sub(r"\brate_func\s*=\s*easeInSine\b", "rate_func=ease_in_sine", code)
    code = re.sub(r"\brate_func\s*=\s*easeOutSine\b", "rate_func=ease_out_sine", code)
    if code != before:
        log.append("rate_func: CamelCase -> snake_case patched (sine easings)")

    # --- Inject _safe_Angle / _safe_angle_label if Angle() is used ---
    # IMPORTANT:
    # 1. We FIRST rewrite user code Angle(...) -> _safe_Angle(...),
    #    so we don't accidentally touch the helper's internal Angle(...).
    # 2. THEN we inject the helper right after `from manim import *`.
    if "Angle(" in code and "_safe_Angle_injected" not in code:
        # 1. Replace in user code BEFORE helper goes in
        code = re.sub(r"\bAngle\s*\(", "_safe_Angle(", code)

        # 2. Prepare helper block (safe _safe_Angle + label helper)
        helper = (
            textwrap.dedent(
                r"""
            # --- injected: safe Angle wrapper & label helper (manim 0.18.1) ---
            _safe_Angle_injected = True

            def _safe_Angle(obj1, obj2, **kwargs):
                '''
                Return an Angle(l1, l2, ...) if it is well-defined.
                If the two lines are (near-)parallel or something explodes,
                return an empty VGroup() instead of raising.
                '''
                try:
                    l1 = Line(obj1.get_start(), obj1.get_end())
                    l2 = Line(obj2.get_start(), obj2.get_end())
                    v1 = l1.get_end() - l1.get_start()
                    v2 = l2.get_end() - l2.get_start()
                    cross = v1[0]*v2[1] - v1[1]*v2[0]
                    # cross ≈ 0 → lines almost parallel/colinear → Angle() is unstable
                    if abs(cross) < 1e-7:
                        return VGroup()
                    return Angle(l1, l2, **kwargs)
                except Exception:
                    return VGroup()

            def _safe_angle_label(angle_mobj, tex_str, scale_val=0.7):
                '''
                Safely create "[angle arc] + [MathTex label]" as one VGroup.

                Behavior:
                - If angle_mobj is effectively empty (no points), return VGroup()
                  so caller can safely self.add(...) without crashing.
                - Otherwise:
                    * Make MathTex(tex_str).scale(scale_val)
                    * Try to move it near the middle of the angle arc
                      using point_from_proportion(0.5).
                    * Fall back to get_center() if that fails.
                '''
                # angle_mobj might be an empty VGroup() from _safe_Angle(...)
                if len(angle_mobj.points) == 0:
                    return VGroup()

                label = MathTex(tex_str).scale(scale_val)
                try:
                    label.move_to(angle_mobj.point_from_proportion(0.5))
                except Exception:
                    label.move_to(angle_mobj.get_center())

                return VGroup(angle_mobj, label)
            """
            ).strip()
            + "\n"
        )

        # 3. Inject helper right after `from manim import *`
        m = re.search(r"(^|\n)(from\s+manim\s+import\s+\*.*?\n)", code)
        insert_at = m.end() if m else 0
        code = code[:insert_at] + helper + code[insert_at:]

        log.append("Angle(): wrapped with _safe_Angle and _safe_angle_label to avoid crash")

    return code, log


def py_compile_check(code: str) -> Tuple[bool, str | None]:
    try:
        compile(code, "<generated>", "exec")
        return True, None
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"


def strict_guard_check(code: str) -> Tuple[bool, str | None]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            top = (node.names[0].name if isinstance(node, ast.Import) else (node.module or "")).split(".")[0]
            if top in {"os", "sys", "pathlib", "subprocess", "shutil", "inspect"}:
                return False, f"Forbidden import: {top}"
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "config" for target in node.targets):
                return False, "Direct assignment to config is prohibited."
    return True, None
