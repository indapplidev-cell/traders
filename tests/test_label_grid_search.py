from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.experiments.experiment_reporter import ExperimentReporter
from app.experiments.label_grid_search import LabelGridSearchService


def test_label_grid_search_rejects_imbalanced_configuration(tmp_path: Path) -> None:
    service = LabelGridSearchService(
        candle_repository=FakeCandleRepository(),
        feature_repository=FakeFeatureRepository(),
        label_repository=FakeLabelRepository(),
        dataset_builder=FakeDatasetBuilder(),
        baseline_service=FakeBaselineService(),
        reporter=ExperimentReporter(reports_dir=tmp_path),
        label_builder=FakeLabelBuilder(),
    )
    service.HORIZONS = [8]
    service.DIRECTION_THRESHOLDS = [0.3]
    service.TAKE_PROFITS = [1.5]
    service.STOP_LOSSES = [1.0]

    result = service.run(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv1",
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2025, 4, 1, tzinfo=timezone.utc),
    )

    assert result["candidates"][0]["reject_reason"] == "class_distribution_too_imbalanced"


class FakeCandleRepository:
    def get_range(self, symbol, interval, start_at, end_at):
        return [object()]


class FakeLabelRepository:
    def upsert_many(self, labels):
        return len(labels)


class FakeFeatureRepository:
    def get_all(self, symbol, interval, feature_version):
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rows = []
        for _ in range(5000):
            rows.append(
                type(
                    "FeatureRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": base_time,
                        "feature_version": feature_version,
                        "features_json": {
                            "return_1": 0.001,
                            "ema_9": 101.0,
                            "ema_21": 100.0,
                            "close_to_ema_21": 0.5,
                        },
                    },
                )()
            )
            base_time += timedelta(minutes=1)
        return rows


class FakeLabelBuilder:
    def build(self, symbol, interval, horizon_candles, label_version, **kwargs):
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rows = []
        for _ in range(5000):
            rows.append(
                type(
                    "LabelRow",
                    (),
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "candle_open_time": base_time,
                        "label_version": label_version,
                        "horizon_candles": horizon_candles,
                        "direction_label": "UP",
                        "tp_before_sl": True,
                        "future_return": 0.01,
                        "future_move_atr": 0.5,
                        "max_favorable_move_atr": 1.0,
                        "max_adverse_move_atr": 0.2,
                    },
                )()
            )
            base_time += timedelta(minutes=1)
        return rows


class FakeDatasetBuilder:
    def build(self, **kwargs):
        return {
            "dataset_rows": 5000,
            "train_rows": 3000,
            "validation_rows": 1000,
            "test_rows": 1000,
        }

    def build_rows(self, **kwargs):
        return [], {}

    def split_rows(self, dataset_rows, train_end=None, validation_end=None):
        def make_rows(label, count):
            rows = []
            for index in range(count):
                sign = 1.0 if label == "UP" else -1.0 if label == "DOWN" else 0.0
                rows.append(
                    type(
                        "Row",
                        (),
                        {
                            "direction_label": label,
                            "features_json": {
                                "return_1": sign * 0.001,
                                "ema_9": 101.0 + sign,
                                "ema_21": 100.0,
                                "close_to_ema_21": sign * 0.5,
                            },
                        },
                    )()
                )
            return rows

        return {
            "train": make_rows("UP", 1000) + make_rows("DOWN", 1000) + make_rows("FLAT", 1000),
            "validation": make_rows("UP", 300) + make_rows("DOWN", 300) + make_rows("FLAT", 400),
            "test": make_rows("UP", 800) + make_rows("DOWN", 100) + make_rows("FLAT", 100),
        }


class FakeBaselineService:
    def evaluate(self, **kwargs):
        return {
            "baselines": {
                "majority_class": {"test": {"accuracy": 0.35, "brier_score": 1.2}},
            }
        }
