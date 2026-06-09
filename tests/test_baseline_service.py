from datetime import datetime, timezone
from pathlib import Path

from app.baseline.baseline_service import BaselineService
from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.features.feature_models import FEATURE_NAMES


def test_baseline_service_reports_always_flat_and_majority_from_train(tmp_path: Path) -> None:
    dataset_builder = DatasetBuilder(
        feature_repository=FakeFeatureRepository(),
        label_repository=FakeLabelRepository(),
        dataset_exporter=DatasetExporter(reports_dir=tmp_path / "reports"),
    )
    service = BaselineService(dataset_builder=dataset_builder, reports_dir=tmp_path / "reports")

    result = service.evaluate(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        train_end=datetime(2025, 3, 1, tzinfo=timezone.utc).date(),
        validation_end=datetime(2025, 3, 16, tzinfo=timezone.utc).date(),
    )

    assert result["baselines"]["always_flat"]["validation"]["predicted_counts"]["FLAT"] == 2
    assert result["baselines"]["majority_class"]["majority_class"] == "UP"
    assert result["baselines"]["majority_class"]["test"]["predicted_counts"]["UP"] == 1


class FakeFeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        rows = []
        for index, open_time in enumerate(
            [
                datetime(2025, 1, 10, tzinfo=timezone.utc),
                datetime(2025, 1, 11, tzinfo=timezone.utc),
                datetime(2025, 1, 12, tzinfo=timezone.utc),
                datetime(2025, 3, 5, tzinfo=timezone.utc),
                datetime(2025, 3, 6, tzinfo=timezone.utc),
                datetime(2025, 3, 20, tzinfo=timezone.utc),
            ]
        ):
            features = {name: float(index + feature_index + 1) for feature_index, name in enumerate(FEATURE_NAMES)}
            features["return_1"] = [0.01, 0.02, -0.01, -0.01, 0.0, -0.02][index]
            features["ema_9"] = [2.0, 2.1, 1.8, 1.5, 2.0, 1.4][index]
            features["ema_21"] = [1.0, 1.2, 2.0, 1.8, 2.0, 1.9][index]
            features["close_to_ema_21"] = [0.1, 0.2, -0.1, -0.2, 0.0, -0.3][index]
            rows.append(
                type(
                    "FeatureRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": open_time,
                        "feature_version": feature_version,
                        "features_json": features,
                    },
                )()
            )
        return rows


class FakeLabelRepository:
    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        labels = [
            ("UP", True, datetime(2025, 1, 10, tzinfo=timezone.utc)),
            ("UP", True, datetime(2025, 1, 11, tzinfo=timezone.utc)),
            ("DOWN", False, datetime(2025, 1, 12, tzinfo=timezone.utc)),
            ("DOWN", False, datetime(2025, 3, 5, tzinfo=timezone.utc)),
            ("FLAT", None, datetime(2025, 3, 6, tzinfo=timezone.utc)),
            ("DOWN", False, datetime(2025, 3, 20, tzinfo=timezone.utc)),
        ]
        rows = []
        for direction_label, tp_before_sl, open_time in labels:
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
                        "future_return": 0.01,
                        "future_move_atr": 1.0,
                        "max_favorable_move_atr": 1.5,
                        "max_adverse_move_atr": 0.5,
                    },
                )()
            )
        return rows
