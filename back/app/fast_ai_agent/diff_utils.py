from __future__ import annotations

import re
from typing import List, Tuple

_HUNK_RE = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@")


def _strip_diff_fences(diff_text: str) -> str:
    text = diff_text.strip()
    text = re.sub(r"^```(?:diff)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def apply_unified_diff(original: str, diff_text: str) -> Tuple[bool, str, str]:
    """Apply unified diff to original string. Returns (applied, new_text, reason)."""
    diff_text = _strip_diff_fences(diff_text)
    if not diff_text:
        return False, original, "empty diff"

    lines = diff_text.splitlines()
    i = 0
    if i < len(lines) and lines[i].startswith("--- "):
        i += 1
    if i < len(lines) and lines[i].startswith("+++ "):
        i += 1

    orig_lines = original.splitlines()
    new_lines: List[str] = []
    idx = 0
    any_hunk = False

    while i < len(lines):
        match = _HUNK_RE.match(lines[i])
        if not match:
            if not any_hunk:
                return False, original, f"not a unified diff (line={lines[i][:40]!r})"
            if lines[i].strip():
                return False, original, f"unexpected content after hunks: {lines[i]!r}"
            i += 1
            continue

        any_hunk = True
        i += 1
        start_old = int(match.group(1)) - 1
        if start_old < idx or start_old > len(orig_lines):
            return False, original, "hunk position out of range"
        new_lines.extend(orig_lines[idx:start_old])
        idx = start_old

        while i < len(lines):
            line = lines[i]
            if line.startswith("@@"):
                break
            if not line:
                new_lines.append("")
                if idx < len(orig_lines):
                    idx += 1
                i += 1
                continue

            tag, content = line[0], line[1:]
            if tag == " ":
                if idx >= len(orig_lines):
                    return False, original, "context beyond EOF"
                new_lines.append(orig_lines[idx])
                idx += 1
            elif tag == "-":
                if idx >= len(orig_lines):
                    return False, original, "deletion beyond EOF"
                idx += 1
            elif tag == "+":
                new_lines.append(content)
            else:
                return False, original, f"unexpected diff tag: {tag!r}"
            i += 1

    new_lines.extend(orig_lines[idx:])
    if not any_hunk:
        return False, original, "no hunks found"
    trailing_newline = "\n" if original.endswith("\n") else ""
    return True, "\n".join(new_lines) + trailing_newline, ""
