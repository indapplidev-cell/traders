from __future__ import annotations

from typing import Any

import torch

from app.models.model_factory import ModelFactory
from app.registry.artifact_storage import ArtifactStorage


class ModelLoader:
    def __init__(
        self,
        artifact_storage: ArtifactStorage,
        model_factory: ModelFactory | None = None,
    ) -> None:
        self._artifact_storage = artifact_storage
        self._model_factory = model_factory or ModelFactory()

    def load(self, model_version: str) -> tuple[torch.nn.Module, dict[str, Any], list[str], dict[str, Any], dict[str, Any]]:
        training_config = self._artifact_storage.load_json(model_version, "training_config.json")
        scaler = self._artifact_storage.load_json(model_version, "scaler.json")
        feature_columns = self._artifact_storage.load_json(model_version, "feature_columns.json")
        metrics = self._artifact_storage.load_json(model_version, "metrics.json")

        model = self._model_factory.create(
            model_name=training_config["model_name"],
            input_dim=len(feature_columns),
        )
        state_dict = torch.load(self._artifact_storage.get_model_path(model_version), map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
        return model, scaler, feature_columns, training_config, metrics
