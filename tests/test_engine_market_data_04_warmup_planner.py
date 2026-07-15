from app.engine_market_data.continuous_sync_daemon import WarmupPlanner


def test_empty_uses_depth_and_existing_uses_only_tail():
    planner = WarmupPlanner({"1m": 3})
    assert planner.expected_open_times("1m", 180_000, None) == [60_000, 120_000, 180_000]
    assert planner.expected_open_times("1m", 180_000, 120_000) == [180_000]
