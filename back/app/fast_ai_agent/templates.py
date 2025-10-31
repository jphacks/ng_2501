from __future__ import annotations

from pathlib import Path
from typing import Dict


def read_reference_templates(directory: Path) -> Dict[str, str]:
    """Return mapping of {filename: file_contents} for *.py templates."""
    if not directory.exists():
        return {}
    templates: Dict[str, str] = {}
    for path in sorted(directory.glob("*.py")):
        try:
            templates[path.name] = path.read_text(encoding="utf-8")
        except Exception:
            continue
    return templates


def build_code_bundle_text(templates: Dict[str, str]) -> str:
    chunks = []
    for name, content in sorted(templates.items()):
        chunks.append(f"[{name} (full text)]\n{content}")
    return "\n".join(chunks)
