from datetime import datetime, timezone

from app.dataset.dataset_models import DatasetRow
from app.dataset.dataset_splitter import DatasetSplitter


def test_dataset_splitter_splits_rows_by_time_without_randomization() -> None:
    splitter = DatasetSplitter()
    rows = [
        _dataset_row(datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 11, 1, tzinfo=timezone.utc)),
        _dataset_row(datetime(2026, 3, 1, tzinfo=timezone.utc)),
    ]

    result = splitter.split(rows)

    assert [row.candle_open_time for row in result["train"]] == [datetime(2025, 1, 2, tzinfo=timezone.utc)]
    assert [row.candle_open_time for row in result["validation"]] == [datetime(2025, 11, 1, tzinfo=timezone.utc)]
    assert [row.candle_open_time for row in result["test"]] == [datetime(2026, 3, 1, tzinfo=timezone.utc)]


def test_dataset_splitter_uses_fallback_when_default_boundaries_leave_no_test_rows() -> None:
    splitter = DatasetSplitter()
    rows = [
        _dataset_row(datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 3, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 4, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 5, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 6, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 7, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 8, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 9, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 10, tzinfo=timezone.utc)),
        _dataset_row(datetime(2025, 1, 11, tzinfo=timezone.utc)),
    ]

    result = splitter.split(rows)

    assert [row.candle_open_time for row in result["train"]] == [
        datetime(2025, 1, day, tzinfo=timezone.utc) for day in range(2, 9)
    ]
    assert [row.candle_open_time for row in result["validation"]] == [
        datetime(2025, 1, 9, tzinfo=timezone.utc)
    ]
    assert [row.candle_open_time for row in result["test"]] == [
        datetime(2025, 1, 10, tzinfo=timezone.utc),
        datetime(2025, 1, 11, tzinfo=timezone.utc),
    ]


def _dataset_row(open_time: datetime) -> DatasetRow:
    return DatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version="fv1",
        label_version="lv1",
        horizon_candles=8,
        features_json={"atr_14": 1.0},
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.01,
        future_move_atr=1.0,
        max_favorable_move_atr=2.0,
        max_adverse_move_atr=0.5,
    )
