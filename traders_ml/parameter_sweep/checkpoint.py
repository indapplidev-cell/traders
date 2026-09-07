"""Checkpoint compatibility helpers shared by CLI and GUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


IMMUTABLE_RESUME_FIELDS = (
    "run_id", "git_commit", "config_hash", "search_space_hash",
    "dataset_fingerprint", "strategy", "seed",
)


def load_checkpoint(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def compatible(existing: Mapping[str, object], expected: Mapping[str, object]) -> bool:
    return all(existing.get(key) == expected.get(key) for key in IMMUTABLE_RESUME_FIELDS)
