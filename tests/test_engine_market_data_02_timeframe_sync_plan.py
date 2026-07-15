from app.engine_market_data.timeframe_sync_plan import build_sync_tasks_for_boundary, expected_open_times_for_boundary


def test_15m_plan_has_exact_opens():
    assert expected_open_times_for_boundary("15m", "15m", 0) == [0]
    assert expected_open_times_for_boundary("15m", "5m", 0) == [0, 300_000, 600_000]
    assert expected_open_times_for_boundary("15m", "1m", 0) == list(range(0, 900_000, 60_000))


def test_slow_boundaries_have_one_task_and_one_open():
    for timeframe in ("1h", "4h", "1d"):
        tasks = build_sync_tasks_for_boundary("BTCUSDT", timeframe, 0)
        assert len(tasks) == 1 and tasks[0].expected_open_times == [0]
