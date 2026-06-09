from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.features.feature_models import FEATURE_NAMES
from app.registry.artifact_storage import ArtifactStorage


def test_overfit_check_learns_small_synthetic_dataset_better_than_random(tmp_path: Path) -> None:
    feature_repository = SyntheticFeatureRepository()
    dataset_builder = DatasetBuilder(
        feature_repository=feature_repository,
        label_repository=SyntheticLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    service = DiagnosticsService(
        dataset_builder=dataset_builder,
        feature_repository=feature_repository,
        model_registry_repository=FakeModelRegistryRepository(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=tmp_path / "reports",
    )

    result = service.overfit_check(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        rows=24,
        epochs=30,
    )

    assert result["is_better_than_random_baseline"] is True
    assert result["overfit_train_accuracy"] > (1.0 / 3.0)


class SyntheticFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        rows = []
        start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for index in range(24):
            label_index = index % 3
            base = {0: 2.0, 1: -2.0, 2: 0.0}[label_index]
            features = {name: base for name in FEATURE_NAMES}
            features["return_1"] = {0: 0.01, 1: -0.01, 2: 0.0}[label_index]
            features["ema_9"] = {0: 2.0, 1: -2.0, 2: 0.0}[label_index]
            features["ema_21"] = {0: 1.0, 1: -1.0, 2: 0.0}[label_index]
            features["close_to_ema_21"] = {0: 0.2, 1: -0.2, 2: 0.0}[label_index]
            rows.append(
                type(
                    "FeatureRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": start_at + timedelta(minutes=15 * index),
                        "feature_version": feature_version,
                        "features_json": features,
                    },
                )()
            )
        return rows


class SyntheticLabelRepository:
    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        rows = []
        start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        labels = ["UP", "DOWN", "FLAT"]
        for index in range(24):
            direction_label = labels[index % 3]
            rows.append(
                type(
                    "LabelRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": start_at + timedelta(minutes=15 * index),
                        "horizon_candles": horizon_candles,
                        "label_version": label_version,
                        "direction_label": direction_label,
                        "tp_before_sl": direction_label != "FLAT",
                        "future_return": 0.01 if direction_label == "UP" else (-0.01 if direction_label == "DOWN" else 0.0),
                        "future_move_atr": 1.0,
                        "max_favorable_move_atr": 1.5,
                        "max_adverse_move_atr": 0.5,
                    },
                )()
            )
        return rows


class FakeModelRegistryRepository:
    def get_by_model_version(self, model_version: str):
        return None
