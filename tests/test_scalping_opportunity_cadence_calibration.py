from scripts.calibrate_scalping_opportunity_cadence import (
    ReplayCandidate,
    SearchConfig,
    metrics,
)


def candidate(*, stop_width=0.30, target=101.0, path=((1_000, 101.1, 99.9, 100.5),)):
    return ReplayCandidate(
        observation_id="obs", segment_id="segment", parameter_set_id="parameters",
        boundary_ms=0, day="2026-01-01", symbol="BTCUSDT",
        opportunity_id="opportunity", direction="BULLISH", setup_type="SCALP_BREAKOUT",
        strategy_score=70.0, entry=100.0, causal_invalidation=100.0 - stop_width,
        atr=0.0, targets=(target,), spread_bps=1.0, depth_impact_bps=0.0,
        path=path,
    )


def config(**changes):
    values = dict(
        minimum_net_rr=0.4, minimum_net_edge_bps=1.0,
        minimum_strategy_score=65.0, atr_buffer_multiplier=0.25,
        maximum_stop_bps=80.0,
    )
    values.update(changes)
    return SearchConfig(**values)


def test_positive_lower_rr_candidate_can_pass_with_all_costs_included():
    result = metrics([candidate()], config(), hours=1.0)

    assert result["opportunities"] == 1
    assert result["outcomes"] == {"TARGET": 1}
    assert result["net_expectancy_per_trade_bps"] > 0


def test_cost_heavy_candidate_rejects_even_with_lower_rr():
    row = candidate(target=100.20)
    result = metrics([row], config(), hours=1.0)

    assert result["opportunities"] == 0


def test_wide_stop_candidate_rejects_without_changing_risk_bounds():
    row = candidate(stop_width=1.0, target=102.0)
    result = metrics([row], config(maximum_stop_bps=80.0), hours=1.0)

    assert result["opportunities"] == 0


def test_same_candle_stop_and_target_uses_conservative_stop_ordering():
    row = candidate(path=((1_000, 101.1, 99.0, 100.5),))
    result = metrics([row], config(), hours=1.0)

    assert result["outcomes"] == {"STOP": 1}
    assert result["net_expectancy_per_trade_bps"] < 0
