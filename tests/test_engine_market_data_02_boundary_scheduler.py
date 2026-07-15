from app.engine_market_data.boundary_scheduler import BoundaryScheduler, latest_closed_boundary_open_time


def test_scheduler_waits_for_delay_and_deduplicates():
    scheduler = BoundaryScheduler(safety_delay_ms=2_000, timeframes=("15m",))
    assert scheduler.due_boundaries(900_001) == []
    events = scheduler.due_boundaries(902_000)
    assert events[0].open_time_ms == 0 and events[0].close_time_ms == 899_999
    assert scheduler.due_boundaries(902_001) == []
    assert latest_closed_boundary_open_time("1h", 7_202_000) == 3_600_000
