from app.engine_paper.scalping_execution_readiness import (
    SCALP_CANCEL_ENTRY_PRICE_MOVED,
    check_scalping_execution_readiness,
)


def check(**changes):
    values = dict(
        decision_timestamp_ms=1_000_000, now_ms=1_030_000,
        decision_entry=100, current_price=100.05, spread_bps=2,
        depth_impact_bps=3, expected_slippage_bps=2, quantity=1,
        entry_ttl_seconds=60, max_price_drift_bps=10,
    )
    values.update(changes)
    return check_scalping_execution_readiness(**values)


def test_fresh_bounded_entry_is_ready():
    assert check().ready


def test_expired_signal_and_moved_price_cancel_entry():
    assert check(now_ms=1_060_001).reason == "SCALP_CANCEL_ENTRY_TTL_EXPIRED"
    moved = check(current_price=100.11)
    assert moved.ready is False
    assert moved.reason == SCALP_CANCEL_ENTRY_PRICE_MOVED


def test_missing_current_microstructure_or_quantity_fails_closed():
    for name in ("spread_bps", "depth_impact_bps", "expected_slippage_bps", "quantity"):
        assert check(**{name: None}).reason == "SCALP_CANCEL_EXECUTION_INPUT_MISSING"
