"""Shared parameter-sweep front-end models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunRequest:
    config_path: Path
    run_id: str
    resume: bool = False
    max_configs: int | None = None
    max_rows: int | None = None
    database_url: str | None = None
