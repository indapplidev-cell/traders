from datetime import datetime, timezone
from pathlib import Path

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.features.feature_models import FEATURE_NAMES
from app.registry.artifact_storage import ArtifactStorage


def test_dataset_diagnostics_reports_label_distribution_per_split(tmp_path: Path) -> None:
    feature_repository = FakeFeatureRepository()
    dataset_builder = DatasetBuilder(
        feature_repository=feature_repository,
        label_repository=FakeLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    service = DiagnosticsService(
        dataset_builder=dataset_builder,
        feature_repository=feature_repository,
        model_registry_repository=FakeModelRegistryRepository(),
        artifact_storage=ArtifactStorage(base_dir=tmp_path / "artifacts"),
        reports_dir=tmp_path / "reports",
    )

    result = service.dataset_report(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        train_end=datetime(2025, 3, 1, tzinfo=timezone.utc).date(),
        validation_end=datetime(2025, 3, 16, tzinfo=timezone.utc).date(),
    )

    assert result["label_counts_train"]["UP"] == 2
    assert result["label_counts_validation"]["DOWN"] == 1
    assert result["label_counts_test"]["FLAT"] == 1
    assert "body_size" in result["feature_min_max_mean"]


class FakeFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        rows = []
        for index, open_time in enumerate(
            [
                datetime(2025, 1, 10, tzinfo=timezone.utc),
                datetime(2025, 1, 11, tzinfo=timezone.utc),
                datetime(2025, 3, 5, tzinfo=timezone.utc),
                datetime(2025, 3, 20, tzinfo=timezone.utc),
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
            ("UP", datetime(2025, 1, 10, tzinfo=timezone.utc)),
            ("UP", datetime(2025, 1, 11, tzinfo=timezone.utc)),
            ("DOWN", datetime(2025, 3, 5, tzinfo=timezone.utc)),
            ("FLAT", datetime(2025, 3, 20, tzinfo=timezone.utc)),
        ]
        return [
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
                    "tp_before_sl": None,
                    "future_return": 0.0,
                    "future_move_atr": 1.0,
                    "max_favorable_move_atr": 1.0,
                    "max_adverse_move_atr": 0.5,
                },
            )()
            for direction_label, open_time in labels
        ]


class FakeModelRegistryRepository:
    def get_by_model_version(self, model_version: str):
        return None
