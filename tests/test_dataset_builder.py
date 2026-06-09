from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_exporter import DatasetExporter
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository
from app.features.feature_models import feature_names_for_version


def test_dataset_builder_drops_incomplete_and_missing_label_rows(tmp_path: Path) -> None:
    feature_repository = FakeFeatureRepository(
        [
            _feature_row(datetime(2025, 1, 2, tzinfo=timezone.utc), {"atr_14": 1.0, "ema_9": 2.0, "rsi_14": 60.0}),
            _feature_row(datetime(2025, 1, 3, tzinfo=timezone.utc), {"atr_14": None, "ema_9": 2.0, "rsi_14": 60.0}),
            _feature_row(datetime(2025, 11, 2, tzinfo=timezone.utc), {"atr_14": 1.0, "ema_9": 2.0, "rsi_14": 60.0}),
            _feature_row(datetime(2026, 3, 2, tzinfo=timezone.utc), {"atr_14": 1.0, "ema_9": 2.0, "rsi_14": 60.0}),
        ]
    )
    label_repository = FakeLabelRepository(
        [
            _label_row(datetime(2025, 1, 2, tzinfo=timezone.utc)),
            _label_row(datetime(2026, 3, 2, tzinfo=timezone.utc)),
        ]
    )
    exporter = DatasetExporter(reports_dir=tmp_path)
    builder = DatasetBuilder(
        feature_repository=feature_repository,
        label_repository=label_repository,
        dataset_exporter=exporter,
    )

    summary = builder.build(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
    )

    assert summary["dataset_rows"] == 2
    assert summary["dropped_incomplete_features"] == 1
    assert summary["dropped_missing_labels"] == 1
    assert summary["train_rows"] == 1
    assert summary["validation_rows"] == 0
    assert summary["test_rows"] == 1
    assert Path(summary["summary_path"]).exists()


def test_dataset_builder_drops_incomplete_fv2_regime_rows(tmp_path: Path) -> None:
    complete_features = {name: 1.0 for name in feature_names_for_version("fv2_regime")}
    incomplete_features = dict(complete_features)
    incomplete_features["ema_200_slope_10"] = None

    feature_repository = FakeFeatureRepository(
        [
            _feature_row(
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                complete_features,
                feature_version="fv2_regime",
            ),
            _feature_row(
                datetime(2025, 1, 3, tzinfo=timezone.utc),
                incomplete_features,
                feature_version="fv2_regime",
            ),
        ]
    )
    label_repository = FakeLabelRepository(
        [
            _label_row(datetime(2025, 1, 2, tzinfo=timezone.utc), label_version="lv_h16_thr03_tp15_sl10", horizon_candles=16),
            _label_row(datetime(2025, 1, 3, tzinfo=timezone.utc), label_version="lv_h16_thr03_tp15_sl10", horizon_candles=16),
        ]
    )
    exporter = DatasetExporter(reports_dir=tmp_path)
    builder = DatasetBuilder(
        feature_repository=feature_repository,
        label_repository=label_repository,
        dataset_exporter=exporter,
    )

    summary = builder.build(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=16,
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp15_sl10",
    )

    assert summary["dataset_rows"] == 1
    assert summary["dropped_incomplete_features"] == 1
    assert summary["dropped_missing_labels"] == 0


class FakeFeatureRepository(FeatureRepository):
    def __init__(self, rows):
        self._rows = rows

    def get_all(self, symbol: str, interval: str, feature_version: str):
        return list(self._rows)


class FakeLabelRepository(LabelRepository):
    def __init__(self, rows):
        self._rows = rows

    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        return list(self._rows)


def _feature_row(open_time: datetime, features_json: dict, feature_version: str = "fv1") -> SimpleNamespace:
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version=feature_version,
        features_json=features_json,
    )


def _label_row(open_time: datetime, label_version: str = "lv1", horizon_candles: int = 8) -> SimpleNamespace:
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        horizon_candles=horizon_candles,
        label_version=label_version,
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.01,
        future_move_atr=1.0,
        max_favorable_move_atr=2.0,
        max_adverse_move_atr=0.5,
    )
