from app.engine_market_data.historical_backfill_planner import HistoricalBackfillPlanner


def test_planner_uses_latest_fully_closed_boundary_and_exact_limit():
    now_ms = 10 * 900_000 + 123
    task = HistoricalBackfillPlanner().build_task("btcusdt", "15m", now_ms, 4)
    assert task.latest_closed_open_time_ms == 9 * 900_000
    assert task.end_open_time_ms == task.latest_closed_open_time_ms
    assert task.expected_open_times == [6 * 900_000, 7 * 900_000, 8 * 900_000, 9 * 900_000]
    assert not task.future_bars_used

