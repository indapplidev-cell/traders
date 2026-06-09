from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


class DatasetExporter:
    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def export_summary(
        self,
        summary: dict[str, Any],
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
    ) -> str:
        file_name = (
            f"dataset_summary_{symbol.lower()}_{interval}_h{horizon_candles}_{feature_version}_{label_version}.json"
        )
        output_path = self._reports_dir / file_name
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return str(output_path)
