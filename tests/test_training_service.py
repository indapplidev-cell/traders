from datetime import datetime, timezone
from pathlib import Path

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.features.feature_models import FEATURE_NAMES
from app.registry.artifact_storage import ArtifactStorage
from app.registry.model_registry import ModelRegistry
from app.training.trainer import Trainer
from app.training.training_service import TrainingService


def test_training_service_trains_and_registers_model(tmp_path: Path) -> None:
    dataset_builder = DatasetBuilder(
        feature_repository=FakeFeatureRepository(),
        label_repository=FakeLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    registry_repository = FakeModelRegistryRepository()
    training_run_repository = FakeTrainingRunRepository()
    artifact_storage = ArtifactStorage(base_dir=tmp_path / "artifacts")
    model_registry = ModelRegistry(repository=registry_repository, artifact_storage=artifact_storage)
    service = TrainingService(
        dataset_builder=dataset_builder,
        model_registry=model_registry,
        training_run_repository=training_run_repository,
        artifact_storage=artifact_storage,
        trainer=Trainer(epochs=2),
    )

    result = service.train(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        model_name="candle_mlp",
    )

    assert result["model_version"].startswith("ml_candle_mlp_v1_")
    assert training_run_repository.finished_status == "completed"
    assert len(registry_repository.created_payloads) == 1
    assert artifact_storage.exists(result["model_version"]) is True

    training_config = artifact_storage.load_json(result["model_version"], "training_config.json")
    metrics = artifact_storage.load_json(result["model_version"], "metrics.json")
    assert "probability_calibration" in training_config
    assert "probability_calibration" in metrics
    assert "selected_temperature" in training_config["probability_calibration"]


class FakeFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        rows = []
        for index, open_time in enumerate(
            [
                datetime(2025, 1, 10, tzinfo=timezone.utc),
                datetime(2025, 1, 11, tzinfo=timezone.utc),
                datetime(2025, 11, 10, tzinfo=timezone.utc),
                datetime(2026, 3, 10, tzinfo=timezone.utc),
            ]
        ):
            rows.append(
                type(
                    "FeatureRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": open_time,
                        "feature_version": feature_version,
                        "features_json": {name: float(index + feature_index + 1) for feature_index, name in enumerate(FEATURE_NAMES)},
                    },
                )()
            )
        return rows


class FakeLabelRepository:
    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        labels = [
            ("UP", True, 0.02, 1.4, 2.0, 0.8, datetime(2025, 1, 10, tzinfo=timezone.utc)),
            ("DOWN", False, -0.03, -1.8, 2.5, 0.7, datetime(2025, 1, 11, tzinfo=timezone.utc)),
            ("FLAT", None, 0.001, 0.1, 0.3, 0.2, datetime(2025, 11, 10, tzinfo=timezone.utc)),
            ("UP", True, 0.04, 2.0, 2.7, 1.1, datetime(2026, 3, 10, tzinfo=timezone.utc)),
        ]
        rows = []
        for direction_label, tp_before_sl, future_return, future_move_atr, max_favorable_move_atr, max_adverse_move_atr, open_time in labels:
            rows.append(
                type(
                    "LabelRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": open_time,
                        "horizon_candles": horizon_candles,
                        "label_version": label_version,
                        "direction_label": direction_label,
                        "tp_before_sl": tp_before_sl,
                        "future_return": future_return,
                        "future_move_atr": future_move_atr,
                        "max_favorable_move_atr": max_favorable_move_atr,
                        "max_adverse_move_atr": max_adverse_move_atr,
                    },
                )()
            )
        return rows


class FakeModelRegistryRepository:
    def __init__(self) -> None:
        self.created_payloads = []

    def create(self, payload):
        self.created_payloads.append(payload)
        return payload

    def get_by_model_version(self, model_version: str):
        return None


class FakeTrainingRunRepository:
    def __init__(self) -> None:
        self.created_payloads = []
        self.finished_status = None

    def create(self, payload):
        self.created_payloads.append(payload)
        return payload

    def finish(self, run_id, status, finished_at, metrics_json, error_message):
        self.finished_status = status
