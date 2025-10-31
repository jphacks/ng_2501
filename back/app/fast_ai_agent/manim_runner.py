from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class ManimExecutionConfig:
    output_file: Path | None = None
    resolution: str | None = None
    fps: int | None = None
    quality: str = "m"  # l/m/h/k


def run_manim_capture(script_path: Path, cfg: ManimExecutionConfig) -> Tuple[int, str, str]:
    qflag = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}.get(cfg.quality, "-qm")
    cmd: List[str] = [
        "manim",
        qflag,
    ]
    if cfg.resolution:
        width, height = cfg.resolution.split("x")
        cmd.extend(["-r", f"{int(width)},{int(height)}"])
    if cfg.fps:
        cmd.extend(["--fps", str(int(cfg.fps))])
    if cfg.output_file is not None:
        cmd.extend(["-o", str(cfg.output_file)])
    cmd.extend([str(script_path), "GeneratedScene"])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr
