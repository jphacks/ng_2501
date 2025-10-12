import re
from typing import Dict, Optional, Tuple

SITE_PKGS_MARKER = "/site-packages/"

def _pick_best_frame(frames: list[Tuple[str, int, Optional[str]]]) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Prefer the last frame not in site-packages; otherwise use the last frame."""
    if not frames:
        return None, None, None
    for path, line, func in reversed(frames):
        if path and SITE_PKGS_MARKER not in path:
            return path, line, func
    return frames[-1]

def _extract_code_from_rich_block(tb_text: str, target_line: int) -> Optional[str]:
    """
    Extract code line shown by Rich-style frames like:
    '│   13 │ │ coin_int = VGroup(... )'
    """
    # Examples this tries to match:
    # "│   13 │ │ coin_int = VGroup(Circle(...), Text(...))"
    rich_code_pat = re.compile(
        r"""^[^\S\r\n]*[^\w\r\n]*\s*
            (?P<lineno>\d+)\s*             # line number
            [│|]\s*                        # box separator
            (?P<rest>.+?)\s*$              # the rest is code snippet
        """,
        re.VERBOSE | re.MULTILINE,
    )
    candidate = None
    for m in rich_code_pat.finditer(tb_text):
        try:
            ln = int(m.group("lineno"))
        except ValueError:
            continue
        if ln == target_line:
            candidate = m.group("rest")
    return candidate

def _extract_code_after_frame_line(tb_text: str, frame_path: str, target_line: int) -> Optional[str]:
    """
    Fallback: from the frame line '/path/file.py:13 in ...', pick the next
    non-empty textual line as the code snippet (heuristic).
    """
    # Find the exact frame line index
    frame_pat = re.compile(re.escape(frame_path) + r":" + str(target_line) + r"\b")
    lines = tb_text.splitlines()
    for i, line in enumerate(lines):
        if frame_pat.search(line):
            # Scan forward for a plausible code line
            for j in range(i + 1, min(i + 6, len(lines))):
                s = lines[j].strip("\n")
                # skip borders only; accept content even if it starts with box char
                if s.strip():
                    # Remove leading box/pipe and spacing
                    s = re.sub(r"^[^\w\r\n]*\s*", "", s)
                    return s
    return None

def _read_code_from_file(path: str, target_line: int) -> Optional[str]:
    """Final fallback: read the source file directly."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, start=1):
                if i == target_line:
                    return line.rstrip("\n")
    except Exception:
        return None
    return None

def parse_manim_or_python_traceback(tb_text: str) -> Dict[str, Optional[str]]:
    """
    Extract essential info from Manim/Rich or standard Python tracebacks.

    Returns:
        {
          "file": str | None,
          "line": int | None,
          "function": str | None,
          "error_type": str | None,
          "message": str | None,
          "code": str | None
        }
    """
    text = tb_text.strip("\n")

    frames: list[Tuple[str, int, Optional[str]]] = []

    # Pattern A: Manim/Rich style: '/path/to/file.py:123 in construct'
    rich_pat = re.compile(
        r"""^[^\S\r\n]*[^\w\r\n]*\s*
            (?P<path>/[^\s:]+?)      # absolute path up to colon
            :(?P<line>\d+)           # :LINE
            (?:\s+in\s+(?P<func>[^\s│]+))?  # optional " in function"
        """,
        re.VERBOSE | re.MULTILINE,
    )
    for m in rich_pat.finditer(text):
        frames.append((m.group("path"), int(m.group("line")), m.group("func")))

    # Pattern B: Standard Python style
    std_pat = re.compile(
        r"""File\s+"(?P<path>[^"]+)",\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\s]+))?""",
        re.MULTILINE,
    )
    for m in std_pat.finditer(text):
        frames.append((m.group("path"), int(m.group("line")), m.group("func")))

    best_path, best_line, best_func = _pick_best_frame(frames)

    # Exception type & message (last '<Type>Error|Exception: ...' line)
    error_type = None
    message = None
    exc_pat = re.compile(r"""(?P<etype>[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\s*:\s*(?P<msg>.+)\s*$""")
    for line in reversed(text.splitlines()):
        s = line.strip()
        if not s:
            continue
        m = exc_pat.search(s)
        if m:
            error_type = m.group("etype")
            message = m.group("msg").strip()
            break
    if error_type is None or message is None:
        # Fallback to the last non-empty line
        for line in reversed(text.splitlines()):
            s = line.strip()
            if s:
                error_type = error_type or "UnknownError"
                message = message or s
                break

    # Code snippet: try (1) rich line, (2) next line after frame, (3) read file
    code = None
    if isinstance(best_line, int):
        code = _extract_code_from_rich_block(text, best_line) or (
            best_path and _extract_code_after_frame_line(text, best_path, best_line)
        ) or (best_path and _read_code_from_file(best_path, best_line))

    return {
        "file": best_path,
        "line": best_line,
        "function": best_func,
        "error_type": error_type,
        "message": message,
        "code": code,
    }

def format_error_for_llm(err: Dict[str, Optional[str]]) -> str:
    """
    Minimal, structured text for LLM input (includes the exact source line).
    """
    return (
        "[Error]\n"
        f"file: {err.get('file')}\n"
        f"line: {err.get('line')}\n"
        f"type: {err.get('error_type')}\n"
        f"message: {err.get('message')}\n"
        f"code: {err.get('code')}\n"
    )

# ------- Example -------
if __name__ == "__main__":
    sample = r"""
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/cli/render/commands.py:125 in │
│ render                                                                                           │
│                                                                                                  │
│   122 │   │   │   try:                                                                           │
│   123 │   │   │   │   with tempconfig({}):                                                       │
│   124 │   │   │   │   │   scene = SceneClass()                                                   │
│ ❱ 125 │   │   │   │   │   scene.render()                                                         │
│   126 │   │   │   except Exception:                                                              │
│   127 │   │   │   │   error_console.print_exception()                                            │
│   128 │   │   │   │   sys.exit(1)                                                                │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/scene/scene.py:237 in render  │
│                                                                                                  │
│    234 │   │   \"""                                                                               │
│    235 │   │   self.setup()                                                                      │
│    236 │   │   try:                                                                              │
│ ❱  237 │   │   │   self.construct()                                                              │
│    238 │   │   except EndSceneEarlyException:                                                    │
│    239 │   │   │   pass                                                                          │
│    240 │   │   except RerunSceneException:                                                       │
│                                                                                                  │
│ /workspaces/ai_agent/back/tmp/vis.py:18 in construct                                             │
│                                                                                                  │
│    15 │   │   self.camera.background_color = "#0b0f17"                                           │
│    16 │   │                                                                                      │
│    17 │   │   # === 0. タイトル ===                                                              │
│ ❱  18 │   │   title = Tex(                                                                       │
│    19 │   │   │   r"\# 【高校1年生向け】三角関数の“動き”を単位円で体感しよう",                   │
│    20 │   │   │   tex_environment=None                                                           │
│    21 │   │   ).scale(0.7).to_edge(UP)                                                           │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/mobject/text/tex_mobject.py:4 │
│ 52 in __init__                                                                                   │
│                                                                                                  │
│   449 │   def __init__(                                                                          │
│   450 │   │   self, *tex_strings, arg_separator="", tex_environment="center", **kwargs           │
│   451 │   ):                                                                                     │
│ ❱ 452 │   │   super().__init__(                                                                  │
│   453 │   │   │   *tex_strings,                                                                  │
│   454 │   │   │   arg_separator=arg_separator,                                                   │
│   455 │   │   │   tex_environment=tex_environment,                                               │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/mobject/text/tex_mobject.py:2 │
│ 98 in __init__                                                                                   │
│                                                                                                  │
│   295 │   │   │   │   │   │   \""",                                                               │
│   296 │   │   │   │   │   ),                                                                     │
│   297 │   │   │   │   )                                                                          │
│ ❱ 298 │   │   │   raise compilation_error                                                        │
│   299 │   │   self.set_color_by_tex_to_color_map(self.tex_to_color_map)                          │
│   300 │   │                                                                                      │
│   301 │   │   if self.organize_left_to_right:                                                    │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/mobject/text/tex_mobject.py:2 │
│ 77 in __init__                                                                                   │
│                                                                                                  │
│   274 │   │   self.brace_notation_split_occurred = False                                         │
│   275 │   │   self.tex_strings = self._break_up_tex_strings(tex_strings)                         │
│   276 │   │   try:                                                                               │
│ ❱ 277 │   │   │   super().__init__(                                                              │
│   278 │   │   │   │   self.arg_separator.join(self.tex_strings),                                 │
│   279 │   │   │   │   tex_environment=self.tex_environment,                                      │
│   280 │   │   │   │   tex_template=self.tex_template,                                            │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/mobject/text/tex_mobject.py:8 │
│ 0 in __init__                                                                                    │
│                                                                                                  │
│    77 │   │                                                                                      │
│    78 │   │   assert isinstance(tex_string, str)                                                 │
│    79 │   │   self.tex_string = tex_string                                                       │
│ ❱  80 │   │   file_name = tex_to_svg_file(                                                       │
│    81 │   │   │   self._get_modified_expression(tex_string),                                     │
│    82 │   │   │   environment=self.tex_environment,                                              │
│    83 │   │   │   tex_template=self.tex_template,                                                │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/utils/tex_file_writing.py:65  │
│ in tex_to_svg_file                                                                               │
│                                                                                                  │
│    62 │   if svg_file.exists():                                                                  │
│    63 │   │   return svg_file                                                                    │
│    64 │                                                                                          │
│ ❱  65 │   dvi_file = compile_tex(                                                                │
│    66 │   │   tex_file,                                                                          │
│    67 │   │   tex_template.tex_compiler,                                                         │
│    68 │   │   tex_template.output_format,                                                        │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/utils/tex_file_writing.py:211 │
│ in compile_tex                                                                                   │
│                                                                                                  │
│   208 │   │   cp = subprocess.run(command, stdout=subprocess.DEVNULL)                            │
│   209 │   │   if cp.returncode != 0:                                                             │
│   210 │   │   │   log_file = tex_file.with_suffix(".log")                                        │
│ ❱ 211 │   │   │   print_all_tex_errors(log_file, tex_compiler, tex_file)                         │
│   212 │   │   │   raise ValueError(                                                              │
│   213 │   │   │   │   f"{tex_compiler} error converting to"                                      │
│   214 │   │   │   │   f" {output_format[1:]}. See log output above or"                           │
│                                                                                                  │
│ /workspaces/ai_agent/back/.venv/lib/python3.11/site-packages/manim/utils/tex_file_writing.py:286 │
│ in print_all_tex_errors                                                                          │
│                                                                                                  │
│   283 │   │   │   "Check your LaTeX installation.",                                              │
│   284 │   │   )                                                                                  │
│   285 │   with log_file.open(encoding="utf-8") as f:                                             │
│ ❱ 286 │   │   tex_compilation_log = f.readlines()                                                │
│   287 │   error_indices = [                                                                      │
│   288 │   │   index for index, line in enumerate(tex_compilation_log) if line.startswith("!")    │
│   289 │   ]                                                                                      │
│ in decode:322                                                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
"""
    info = parse_manim_or_python_traceback(sample)
    print(format_error_for_llm(info))
