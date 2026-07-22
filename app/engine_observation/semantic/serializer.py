from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.engine_observation.observer_reliability import canonical_json


def append_canonical_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
