from app.dataset.gap_aware_dataset_filter import GapAwareDatasetFilter


def test_gap_aware_dataset_filter_excludes_rows_around_detailed_gap() -> None:
    rows = [
        {"candle_open_time": f"2025-03-01T0{hour}:00:00+00:00", "row_id": hour}
        for hour in range(6)
    ]

    filtered_rows, summary = GapAwareDatasetFilter().apply(
        rows=rows,
        symbol="BTCUSDT",
        interval="15m",
        gap_count=1,
        missing_open_times=["2025-03-01T02:30:00+00:00"],
        lookback_bars=1,
        lookahead_bars=1,
    )

    assert [row["row_id"] for row in filtered_rows] == [0, 1, 5]
    assert summary["filter_version"] == "ml30"
    assert summary["excluded_rows"] == 3
    assert summary["detail_gap_data_available"] is True
    assert summary["filter_applied"] is True


def test_gap_aware_dataset_filter_marks_dataset_unsafe_without_gap_details() -> None:
    filtered_rows, summary = GapAwareDatasetFilter().apply(
        rows=[{"candle_open_time": "2025-03-01T00:00:00+00:00"}],
        symbol="BTCUSDT",
        interval="15m",
        gap_count=4,
        missing_open_times=None,
    )

    assert len(filtered_rows) == 1
    assert summary["detail_gap_data_available"] is False
    assert summary["dataset_safe_for_training"] is False
    assert summary["warnings"] == ["detail_gap_data_unavailable"]
