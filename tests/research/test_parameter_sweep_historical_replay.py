from __future__ import annotations

from copy import deepcopy

from traders_ml.parameter_sweep.historical_replay import (
    baseline_parity, build_parameter_registry, chronological_portfolio_replay,
    gate_candidate, replay_capabilities, resolve_price_path,
)


def _candidate(*, direction="BULLISH", high=110.0, low=99.0, close=105.0):
    return {
        "candidate_id": "c1", "causal_identity": "BTC:1000:BULLISH",
        "causal_opportunity": "o1", "symbol": "BTCUSDT", "boundary_ms": 1000,
        "opened_at_ms": 1000, "direction": direction, "setup_type": "TEST",
        "historically_rejected": True, "historical_rejection_reason": "RR_FAIL",
        "entry_price": 100.0, "stop_price": 98.0 if direction == "BULLISH" else 102.0,
        "target_price": 104.0 if direction == "BULLISH" else 96.0,
        "stop_distance_bps": 200.0, "target_distance_bps": 400.0,
        "effective_total_cost_bps": 10.0, "cost_provenance": "HISTORICAL",
        "probability_sample_size": 20, "p_win_raw": .6, "expected_ev_r": .1,
        "net_rr": 1.5, "risk_score": 90.0, "strategy_score": 80.0,
        "causal_reset_conditions": 1,
        "market_path_1m": [{"close_time_ms": 61_000, "open": 100.0,
                            "high": high, "low": low, "close": close}],
    }


def _config(**changes):
    value = {"stop_max_bps": 250.0, "target_min_bps": 300.0,
             "minimum_planned_rr": .4, "bucket_min_sample": 20,
             "min_positive_ev_r": 0.0, "causal_reset_min_conditions": 1,
             "soft_timeout_seconds": 60, "hard_timeout_seconds": 120,
             "min_target_progress_at_soft_timeout": .2, "max_extensions": 0,
             "extension_seconds": 0, "risk_per_trade_bps": 10.0,
             "max_open_positions": 2, "max_new_commands_per_cycle": 1,
             "total_open_risk_limit_bps": 50.0}
    value.update(changes)
    return value


def test_long_short_and_same_bar_stop_target_resolution_is_conservative():
    long = resolve_price_path(_candidate(high=105, low=97), _config())
    short = resolve_price_path(_candidate(direction="BEARISH", high=103, low=95), _config())
    assert long["exit_reason"] == short["exit_reason"] == "STOP_SAME_BAR_CONSERVATIVE"
    assert long["exit_price"] == 98.0 and short["exit_price"] == 102.0


def test_time_stop_reconstructs_without_shadow_rows_and_carries_cost_provenance():
    row = _candidate(high=101, low=99, close=100.1)
    outcome = resolve_price_path(row, _config())
    assert outcome["exit_reason"] == "TIME_STOP"
    assert row["cost_provenance"] == "HISTORICAL"


def test_rejected_opportunity_can_pass_alternative_geometry_config():
    row = _candidate()
    assert gate_candidate(row, _config(stop_max_bps=150))[0] is False
    assert gate_candidate(row, _config(stop_max_bps=250))[0] is True


def test_chronological_portfolio_selector_risk_balance_and_symbol_capacity():
    first = _candidate(high=105, low=99)
    second = deepcopy(first); second.update(candidate_id="c2", causal_identity="BTC:1000:BEARISH", direction="BEARISH", risk_score=10)
    result = chronological_portfolio_replay([first, second], _config())
    assert result["trade_count"] == 1
    assert result["funnel"]["REJECT_SELECTOR"] == 1
    assert result["ending_balance"] != 1000.0
    assert result["available_balance"] == result["ending_balance"]


def test_per_family_capability_does_not_globally_fail_optional_missing_family():
    summary = {"MARKET_1M_ROWS": 1, "MARKET_5M_ROWS": 1}
    rows = [_candidate()]
    rows[0]["p_win_raw"] = None
    caps = replay_capabilities(summary, rows)
    assert caps["STOP_TARGET_PATH"]["STATUS"] == "READY"
    assert caps["PORTFOLIO"]["STATUS"] == "READY"
    assert gate_candidate(rows[0], _config())[0] is True


def test_parameter_registry_is_derived_from_runtime_owners_and_search_values():
    registry = build_parameter_registry({"risk_per_trade_bps": [5.0, 10.0], "stop_max_bps": [50.0, 65.0]})
    assert {item["PARAMETER_FAMILY"] for item in registry} == {"RISK", "STOP"}
    assert next(x for x in registry if x["PARAMETER_NAME"] == "risk_per_trade_bps")["BASELINE_VALUE"] == 10.0


def test_baseline_parity_classifies_known_recovery_separately():
    persisted = [{"position_id": "p", "symbol": "ETHUSDT", "side": "LONG",
                  "opened_at": __import__("datetime").datetime.fromtimestamp(1, tz=__import__("datetime").timezone.utc),
                  "reason_code": "OPERATOR_RECOVERY_CLOSE"}]
    parity = baseline_parity({"trades": []}, persisted)
    assert parity["BASELINE_EXPECTED_MISMATCHES"] == 1
    assert parity["BASELINE_UNEXPLAINED_MISMATCHES"] == 0


def test_chronological_holdout_inputs_remain_isolated_between_runs():
    row = _candidate()
    before = deepcopy(row)
    chronological_portfolio_replay([row], _config())
    assert row == before
