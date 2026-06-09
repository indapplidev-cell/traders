from datetime import datetime, timezone
from pathlib import Path

import torch

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.diagnostics.diagnostics_service import DiagnosticsService
from app.features.feature_models import FEATURE_NAMES
from app.registry.artifact_storage import ArtifactStorage


def test_model_diagnostics_detects_prediction_collapse(tmp_path: Path) -> None:
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
        model_loader=FakeModelLoader(),
    )

    result = service.model_report(
        model_version="mv_flat",
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        train_end=datetime(2025, 3, 1, tzinfo=timezone.utc).date(),
        validation_end=datetime(2025, 3, 16, tzinfo=timezone.utc).date(),
    )

    assert result["collapse_detected"] is True
    assert result["predicted_counts_test"]["FLAT"] == result["actual_counts_test"]["UP"] + result["actual_counts_test"]["DOWN"] + result["actual_counts_test"]["FLAT"]


class FakeFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        rows = []
        open_times = [
            datetime(2025, 1, 10, tzinfo=timezone.utc),
            datetime(2025, 1, 11, tzinfo=timezone.utc),
            datetime(2025, 3, 5, tzinfo=timezone.utc),
            datetime(2025, 3, 6, tzinfo=timezone.utc),
            datetime(2025, 3, 20, tzinfo=timezone.utc),
            datetime(2025, 3, 21, tzinfo=timezone.utc),
        ]
        for index, open_time in enumerate(open_times):
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
            ("DOWN", datetime(2025, 1, 11, tzinfo=timezone.utc)),
            ("UP", datetime(2025, 3, 5, tzinfo=timezone.utc)),
            ("DOWN", datetime(2025, 3, 6, tzinfo=timezone.utc)),
            ("UP", datetime(2025, 3, 20, tzinfo=timezone.utc)),
            ("FLAT", datetime(2025, 3, 21, tzinfo=timezone.utc)),
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
        return type("ModelRow", (), {"is_active": True})()


class FakeModelLoader:
    def load(self, model_version: str):
        return ConstantFlatModel(), {"mean": [0.0] * len(FEATURE_NAMES), "std": [1.0] * len(FEATURE_NAMES)}, list(FEATURE_NAMES), {}, {}


class ConstantFlatModel:
    def eval(self):
        return self

    def __call__(self, features):
        batch = features.shape[0]
        return {
            "direction_logits": torch.tensor([[0.0, 0.0, 5.0]] * batch, dtype=torch.float32),
            "tp_sl_logits": torch.zeros((batch,), dtype=torch.float32),
            "expected_move_atr": torch.zeros((batch,), dtype=torch.float32),
            "risk_score": torch.zeros((batch,), dtype=torch.float32),
        }
