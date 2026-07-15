from app.engine_market_data.continuous_sync_daemon import ContinuousBoundaryScheduler


def test_boundary_is_emitted_once_after_allowance():
    scheduler = ContinuousBoundaryScheduler(["BTCUSDT"], ["15m"], {"15m": 20_000})
    boundary = 15 * 60_000 * 10
    assert scheduler.get_due_tasks(boundary + 19_999)[0].expected_open_time_ms == boundary - 15 * 60_000 * 2
    assert scheduler.get_due_tasks(boundary + 20_000)[0].expected_open_time_ms == boundary - 15 * 60_000
    assert scheduler.get_due_tasks(boundary + 20_000) == []
