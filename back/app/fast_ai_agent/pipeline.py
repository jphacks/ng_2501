from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .diff_utils import apply_unified_diff
from .gemini_client import GeminiClientError, GeminiTextClient, load_api_key
from .manim_runner import ManimExecutionConfig, run_manim_capture
from .prompts import PromptStore, load_prompt_store
from .sanitizers import (
    ban_tex_usage,
    force_class_name,
    patch_manim_019_compat,
    py_compile_check,
    sanitize,
    strict_guard_check,
    strip_forbidden_imports,
)
from .templates import build_code_bundle_text, read_reference_templates
from app.tools.secure import is_code_safe


def _normalize_generated_code(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0]
    return cleaned.strip()


def _compose_user_prompt(content: str, enhance_prompt: str) -> str:
    if not enhance_prompt:
        return content.strip()
    return f"{content.strip()}\n\n[Additional Instruction]\n{enhance_prompt.strip()}"


@dataclass
class PipelineConfig:
    translator_model: str | None = "gemini-2.5-flash-lite"
    generator_model: str = "gemini-2.5-pro"
    patch_model: str = "gemini-2.5-flash"
    max_patch_attempts: int = 3
    quality: str = "l"


class ArtifactWriter:
    def __init__(self, root: Optional[Path]):
        self.root = root
        if root is not None:
            root.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, content: str) -> None:
        if self.root is None:
            return
        (self.root / name).write_text(content, encoding="utf-8")


class FastAIPipeline:
    def __init__(self, base_dir: Path, env_path: str | None = None, *, config: PipelineConfig | None = None):
        self.base_dir = base_dir
        self.prompts: PromptStore = load_prompt_store(base_dir / "prompts.toml")
        templates_dir = base_dir / "manim_template_code"
        self.templates = read_reference_templates(templates_dir)
        if not self.templates:
            raise FileNotFoundError(f"No reference templates found under {templates_dir}")
        self.code_bundles = build_code_bundle_text(self.templates)
        api_key = load_api_key(env_path)
        self.gemini = GeminiTextClient(api_key)
        self.config = config or PipelineConfig()

    def _artifact_writer(self, video_id: str) -> ArtifactWriter:
        stamp = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
        root = Path("tmp") / "fast_ai_agent" / f"{stamp}_{video_id}"
        return ArtifactWriter(root)

    def _translate(self, text: str, writer: ArtifactWriter) -> str:
        if not self.config.translator_model:
            return text
        prompt = self.prompts.build(self.prompts.ja2en, ja_text=text)
        writer.write("prompt_translate.txt", prompt)
        return self.gemini.generate(self.config.translator_model, prompt)

    def _generate_code(self, en_text: str, writer: ArtifactWriter) -> str:
        tpl = self.prompts.single_edit_en
        if "{single_request_en}" not in tpl and "{user_request}" not in tpl:
            tpl += "\nUser Request: {single_request_en}\n"
        prompt = self.prompts.build(
            tpl,
            single_request_en=en_text,
            user_request=en_text,
            code_bundles=self.code_bundles,
        )
        writer.write("prompt_generate.txt", prompt)
        response = self.gemini.generate(self.config.generator_model, prompt)
        writer.write("raw_code.txt", response)
        code = _normalize_generated_code(response)
        code = sanitize(code)
        code, compat_log = patch_manim_019_compat(code)
        if compat_log:
            writer.write("compat_patches.log", "\n".join(compat_log))
        return code

    def _static_issues(self, code: str) -> list[str]:
        issues: list[str] = []
        ok_tex, tex_reason = ban_tex_usage(code)
        if not ok_tex and tex_reason:
            issues.append(tex_reason)
        ok_syn, syn_reason = py_compile_check(code)
        if not ok_syn and syn_reason:
            issues.append(syn_reason)
        ok_guard, guard_reason = strict_guard_check(code)
        if not ok_guard and guard_reason:
            issues.append(guard_reason)
        return issues

    def _build_patch_prompt(self, code: str, error_tail: str, writer: ArtifactWriter, attempt: int) -> str:
        prompt = self.prompts.build(
            self.prompts.patch,
            current_code=code,
            error_tail=error_tail,
        )
        writer.write(f"prompt_patch_{attempt}.txt", prompt)
        return prompt

    def _apply_patch(self, current_code: str, diff_text: str, writer: ArtifactWriter, attempt: int) -> tuple[bool, str]:
        applied, new_code, reason = apply_unified_diff(current_code, diff_text)
        if not applied:
            writer.write(f"patch_failure_{attempt}.log", f"apply failed: {reason}\n{diff_text}")
            return False, current_code
        new_code = strip_forbidden_imports(force_class_name(new_code))
        writer.write(f"patched_code_{attempt}.py", new_code)
        return True, new_code

    def generate_video(self, video_id: str, content: str, enhance_prompt: str) -> str:
        writer = self._artifact_writer(video_id)
        composed = _compose_user_prompt(content, enhance_prompt)
        writer.write("user_request.txt", composed)

        try:
            en_request = self._translate(composed, writer)
        except GeminiClientError as exc:
            writer.write("error.log", str(exc))
            raise
        writer.write("translated.txt", en_request)

        try:
            code = self._generate_code(en_request, writer)
        except GeminiClientError as exc:
            writer.write("error.log", f"code generation failed: {exc}")
            raise
        if not is_code_safe(code):
            writer.write("final_error.log", "Generated code failed security checks.")
            return "bad_request"
        issues = self._static_issues(code)
        writer.write("generated_scene.initial.py", code)

        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)
        script_path = tmp_dir / f"{video_id}.py"
        script_path.write_text(code, encoding="utf-8")

        cfg = ManimExecutionConfig(
            output_file=None,
            quality=self.config.quality,
        )

        rc, stdout, stderr = run_manim_capture(script_path, cfg)
        writer.write("manim_stdout_0.txt", stdout)
        writer.write("manim_stderr_0.txt", stderr)

        attempt = 0
        current_code = code
        while rc != 0 and attempt < max(0, self.config.max_patch_attempts):
            attempt += 1
            tail = stderr or "(no stderr)"
            static = issues or self._static_issues(current_code)
            if static:
                tail = tail + "\n\n[STATIC CHECKS]\n- " + "\n- ".join(static)

            patch_prompt = self._build_patch_prompt(current_code, tail, writer, attempt)
            try:
                diff_text = self.gemini.generate(self.config.patch_model, patch_prompt)
            except GeminiClientError as exc:
                writer.write(f"error_patch_{attempt}.log", str(exc))
                break
            writer.write(f"patch_diff_{attempt}.diff", diff_text)
            applied, new_code = self._apply_patch(current_code, diff_text, writer, attempt)
            if not applied:
                continue
            current_code = new_code
            script_path.write_text(current_code, encoding="utf-8")
            issues = self._static_issues(current_code)
            rc, stdout, stderr = run_manim_capture(script_path, cfg)
            writer.write(f"manim_stdout_{attempt}.txt", stdout)
            writer.write(f"manim_stderr_{attempt}.txt", stderr)

        if rc != 0:
            writer.write("final_error.log", stderr)
            return "error"
        return "Success"
