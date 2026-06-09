from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


class ExperimentReporter:
    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, file_name: str, payload: dict[str, Any]) -> str:
        output_path = self._reports_dir / file_name
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(output_path)
