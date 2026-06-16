from datetime import datetime, timezone
from types import SimpleNamespace

from app.dataset.dataset_builder import DatasetBuilder


def test_dataset_builder_uses_date_range_when_provided(tmp_path) -> None:
    feature_repo = FakeFeatureRepository()
    label_repo = FakeLabelRepository()
    builder = DatasetBuilder(feature_repository=feature_repo, label_repository=label_repo)

    start_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 6, 16, tzinfo=timezone.utc)

    rows, summary = builder.build_rows(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv3_candle_ta_context",
        label_version="lv2_h08_thr03_tp10_sl10",
        start_at=start_at,
        end_at=end_at,
    )

    assert feature_repo.get_range_called is True
    assert label_repo.get_range_called is True
    assert feature_repo.get_all_called is False
    assert label_repo.get_all_called is False
    assert len(rows) == 2
    assert summary["feature_rows"] == 2
    assert summary["label_rows"] == 2
    assert summary["dataset_rows"] == 2
    assert summary["date_range_limited"] is True
    assert summary["start_at"] == start_at.isoformat()
    assert summary["end_at"] == end_at.isoformat()


class FakeFeatureRepository:
    def __init__(self) -> None:
        self.get_range_called = False
        self.get_all_called = False

    def get_range(self, **kwargs):
        self.get_range_called = True
        return [
            _feature_row(datetime(2026, 5, 1, tzinfo=timezone.utc)),
            _feature_row(datetime(2026, 5, 2, tzinfo=timezone.utc)),
        ]

    def get_all(self, **kwargs):
        self.get_all_called = True
        return []


class FakeLabelRepository:
    def __init__(self) -> None:
        self.get_range_called = False
        self.get_all_called = False

    def get_range(self, **kwargs):
        self.get_range_called = True
        return [
            _label_row(datetime(2026, 5, 1, tzinfo=timezone.utc)),
            _label_row(datetime(2026, 5, 2, tzinfo=timezone.utc)),
        ]

    def get_all(self, **kwargs):
        self.get_all_called = True
        return []


def _feature_row(open_time: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version="fv3_candle_ta_context",
        features_json={"atr_14": 1.0, "ema_9": 2.0, "rsi_14": 55.0},
    )


def _label_row(open_time: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        horizon_candles=8,
        label_version="lv2_h08_thr03_tp10_sl10",
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.01,
        future_move_atr=1.0,
        max_favorable_move_atr=2.0,
        max_adverse_move_atr=0.5,
    )
