from __future__ import annotations

from typing import Any

from app.registry.artifact_storage import ArtifactStorage


class ModelRegistry:
    BASELINE_ACCURACY = 1.0 / 3.0
    BASELINE_BRIER_SCORE = 2.0 / 3.0

    def __init__(self, repository, artifact_storage: ArtifactStorage) -> None:
        self._repository = repository
        self._artifact_storage = artifact_storage

    def register(self, payload: dict[str, Any]):
        return self._repository.create(payload)

    def list_models(self) -> list[dict[str, Any]]:
        return self._repository.list_all()

    def activate(self, model_version: str) -> dict[str, Any]:
        model_row = self._repository.get_by_model_version(model_version)
        if model_row is None:
            raise ValueError(f"Unknown model_version: {model_version}")
        if not self._artifact_storage.exists(model_version):
            raise ValueError("Cannot activate model without artifact.")
        if model_row.accuracy is None or model_row.brier_score is None:
            raise ValueError("Cannot activate model without test metrics.")

        self._repository.deactivate_scope(
            symbol=model_row.symbol,
            interval=model_row.interval,
            horizon_candles=model_row.horizon_candles,
        )
        self._repository.set_active(model_version=model_version, is_active=True)

        warning = None
        accuracy = float(model_row.accuracy)
        brier_score = float(model_row.brier_score)
        if accuracy < self.BASELINE_ACCURACY or brier_score > self.BASELINE_BRIER_SCORE:
            warning = (
                f"Model metrics look weak versus baseline: accuracy={accuracy:.4f}, "
                f"brier_score={brier_score:.4f}"
            )

        return {
            "model_version": model_version,
            "activated": True,
            "warning": warning,
        }
