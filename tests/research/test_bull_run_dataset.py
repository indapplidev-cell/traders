from traders_ml.parameter_sweep.bull_run_dataset import (
    _atr14,
    _entry_components,
    historical_costs,
)


def test_historical_costs_require_every_causal_component():
    geometry = {
        "entry_fee_bps": 7.5, "exit_fee_bps": 7.5,
        "entry_slippage_bps": 2, "exit_slippage_bps": 2,
        "spread_bps": 1, "adverse_fill_reserve_bps": 3,
        "effective_total_cost_bps": 23,
    }
    assert historical_costs({"geometry": geometry}) == {
        key: value for key, value in geometry.items() if key != "effective_total_cost_bps"
    } | {"round_trip_cost_bps": 23}
    missing = dict(geometry)
    missing["spread_bps"] = None
    assert historical_costs({"geometry": missing}) is None


def test_entry_components_reverse_the_lossless_baseline_decomposition():
    contributions = {
        "structure": 20, "context": 12, "momentum": 12, "volume": 12,
        "entry_quality": 8, "liquidity": 8, "confirmation": 8,
    }
    strategy = {"context": {"scalping_score_decomposition": {"components": contributions}}}
    assert _entry_components(strategy) == {name: 80 for name in contributions}
    assert _entry_components({}) is None


def test_atr_uses_only_current_and_prior_candles():
    rows = [
        {"open_time_ms": index * 300_000, "high": 101 + index, "low": 99,
         "close": 100 + index}
        for index in range(15)
    ]
    before = _atr14(rows)
    changed = [dict(row) for row in rows]
    changed[-1]["high"] = 1000
    after = _atr14(changed)
    assert before[13 * 300_000] == after[13 * 300_000]
    assert before[14 * 300_000] != after[14 * 300_000]
