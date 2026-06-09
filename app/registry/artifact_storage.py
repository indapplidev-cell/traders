from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from app.config.settings import PROJECT_ROOT


class ArtifactStorage:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or (PROJECT_ROOT / "artifacts" / "models")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model_version: str,
        model: torch.nn.Module,
        scaler: dict[str, Any],
        feature_columns: list[str],
        training_config: dict[str, Any],
        metrics: dict[str, Any],
    ) -> str:
        output_dir = self.get_model_dir(model_version)
        output_dir.mkdir(parents=True, exist_ok=True)

        torch.save(model.state_dict(), output_dir / "model.pt")
        (output_dir / "scaler.json").write_text(json.dumps(scaler, indent=2), encoding="utf-8")
        (output_dir / "feature_columns.json").write_text(json.dumps(feature_columns, indent=2), encoding="utf-8")
        (output_dir / "training_config.json").write_text(json.dumps(training_config, indent=2), encoding="utf-8")
        (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return str(output_dir)

    def exists(self, model_version: str) -> bool:
        model_dir = self.get_model_dir(model_version)
        required = ["model.pt", "scaler.json", "feature_columns.json", "training_config.json", "metrics.json"]
        return all((model_dir / file_name).exists() for file_name in required)

    def load_json(self, model_version: str, file_name: str) -> dict[str, Any] | list[Any]:
        return json.loads((self.get_model_dir(model_version) / file_name).read_text(encoding="utf-8"))

    def get_model_path(self, model_version: str) -> Path:
        return self.get_model_dir(model_version) / "model.pt"

    def get_model_dir(self, model_version: str) -> Path:
        return self._base_dir / model_version
