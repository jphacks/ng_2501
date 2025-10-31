from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    import tomli as tomllib  # type: ignore


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
- Use manim==0.19.0 API strictly.
- One class only: class GeneratedScene(Scene):
- No external files, no I/O, no images, no sounds.
- Set a BLACK background (use self.camera.background_color=BLACK in construct()).
- Use only: from manim import *  and  import numpy as np  (optionally import math).
- Render dashed lines with 0.19-safe constructs (e.g., DashedVMobject(..., num_dashes=...)).
- Do NOT use deprecated params like x_min/x_max for Axes or plot; use x_range/y_range and x_range for plot.
- All math angles are radians unless degree text labeling is explicitly asked; when showing degrees in text, convert from radians safely.
- Only import manim, numpy, math. Do not import: os, sys, pathlib, subprocess, shutil, inspect.
- Do not assign to config; no external file I/O.
- Assume Manim 0.19.0 API.
- Use snake_case rate functions (e.g., linear, smooth, there_and_back, ease_in_out_sine). Never CamelCase.
- Do NOT use MathTex/Tex for continuously changing numbers; use DecimalNumber/Integer.
- Compose degree label as [DecimalNumber, MathTex(r"^\\circ")] where only the number updates.
- Avoid always_redraw for static objects; prefer one-time creation + add_updater to move/update.
- Keep sin/cos graphs static; only move markers/guide lines with updaters.
- Restrict color constants to: BLACK, WHITE, BLUE, BLUE_A, BLUE_C, GREEN, GREEN_C, ORANGE, RED, RED_C, TEAL, YELLOW.

[HOW TO USE REFERENCES]
- The reference code bundles below (multiple .py) are examples you can adapt.
- Your output must still be a single file with one GeneratedScene.

[ENGLISH USER REQUEST]
{single_request_en}

[REFERENCE CODE BUNDLES]
{code_bundles}

[OUTPUT FORMAT]
- Reply ONLY with Python code. No explanation and no backticks.
- The file must import from manim import * and define class GeneratedScene(Scene).
"""


DEFAULT_PATCH_PROMPT = r"""
You are a senior Python/Manim engineer. The Manim version is 0.19.0 (Community).

Goal: Produce a **minimal unified-diff patch** that fixes the runtime error(s) without rewriting the whole file.
Patch only the necessary lines. Keep the overall structure and style unchanged.

[HARD RULES]
- Keep exactly ONE class: GeneratedScene(Scene).
- Use only: from manim import *, import numpy as np, optional import math.
- No forbidden imports: os, sys, pathlib, subprocess, shutil, inspect.
- Do not assign to config.
- Use Manim 0.19.0 APIs (x_range/y_range, snake_case rate functions).
- Prefer adding try/except guards over big refactors.
- If MathTex has dynamic numbers, prefer DecimalNumber.
- Avoid non-ASCII in Tex/MathTex strings.
- Restrict color constants to: BLACK, WHITE, BLUE, BLUE_A, BLUE_C, GREEN, GREEN_C, ORANGE, RED, RED_C, TEAL, YELLOW.

[CURRENT FILE: generated_scene.py]
{current_code}

[ERROR LOG (tail)]
{error_tail}

[OUTPUT FORMAT]
- Output ONLY a unified diff. No prose, no code fences.
- Must start with:
  --- a/generated_scene.py
  +++ b/generated_scene.py
  @@ ...
- Keep the patch as small as possible. Do not reformat unrelated lines.
"""


def _load_prompts_file(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        with path.open("rb") as fp:
            return tomllib.load(fp)
    except Exception:
        return {}


@dataclass
class PromptStore:
    ja2en: str
    single_edit_en: str
    patch: str

    def build(self, template: str, **kwargs: Any) -> str:
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            placeholder = "{" + str(exc) + "}"
            return template.replace(placeholder, f"<missing:{exc}>")


def load_prompt_store(prompts_path: Path | None) -> PromptStore:
    raw = _load_prompts_file(prompts_path)

    def _fetch(key: str, default: str) -> str:
        value = raw.get(key, {})
        if isinstance(value, dict):
            template = value.get("template")
            if isinstance(template, str) and template.strip():
                return template
        return default

    return PromptStore(
        ja2en=_fetch("ja2en", DEFAULT_JA2EN_PROMPT),
        single_edit_en=_fetch("single_edit_en", DEFAULT_SINGLE_EDIT_EN),
        patch=_fetch("patch", DEFAULT_PATCH_PROMPT),
    )
