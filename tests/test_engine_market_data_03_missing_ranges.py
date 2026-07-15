from app.engine_market_data.historical_backfill_planner import group_missing_open_times_into_ranges, split_backfill_range


def test_missing_opens_group_and_split_at_rest_limit():
    values = [index * 60_000 for index in range(1002)] + [1100 * 60_000]
    ranges = group_missing_open_times_into_ranges(values, "1m", "BTCUSDT")
    assert [item.expected_count for item in ranges] == [1002, 1]
    batches = split_backfill_range(ranges[0], 1000)
    assert [item.expected_count for item in batches] == [1000, 2]
    assert batches[1].start_time_ms == 1000 * 60_000


def test_empty_missing_set_has_no_ranges():
    assert group_missing_open_times_into_ranges([], "1m") == []

