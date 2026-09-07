"""Small OS and identifier utilities without research behavior."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess


def generate_run_id(output_root: Path, *, now: datetime | None = None) -> str:
    moment = now or datetime.now().astimezone()
    base = moment.strftime("%Y%m%d_%H%M%S_%f")[:19]
    candidate = base
    suffix = 1
    while (output_root / candidate).exists():
        candidate = f"{base}_{suffix:02d}"
        suffix += 1
    return candidate


def open_directory(path: Path) -> None:
    target = path.resolve(strict=True)
    if not target.is_dir():
        raise NotADirectoryError(target)
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif os.uname().sysname == "Darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def format_duration(seconds: float | None) -> str:
    total = max(0, int(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
