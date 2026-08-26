import pytest

from app.engine_position.scalping_monitor import observe_scalping_position


def test_long_observation_tracks_mfe_mae_market_and_distances():
    row = observe_scalping_position(
        position_id="p1", side="BULLISH", entry_price=100, stop_price=99,
        target_price=102, opened_at_ms=1_000, observed_at_ms=61_000,
        current_price=101, highest_price=101.5, lowest_price=99.5,
        spread_bps=2, momentum=.4, relative_volume=1.2, structure="UP",
    )
    assert row.holding_time_ms == 60_000
    assert row.mfe_bps == pytest.approx(150)
    assert row.mae_bps == pytest.approx(50)
    assert row.spread_bps == 2 and row.structure == "UP"
    assert row.distance_to_target_bps > 0 and row.distance_to_stop_bps > 0


def test_unknown_optional_metrics_remain_none_not_zero():
    row = observe_scalping_position(
        position_id="p2", side="BEARISH", entry_price=100, stop_price=101,
        target_price=98, opened_at_ms=1_000, observed_at_ms=2_000,
        current_price=99, highest_price=100.5, lowest_price=98.5,
    )
    assert row.spread_bps is None
    assert row.momentum is None
    assert row.relative_volume is None
    assert row.structure is None
