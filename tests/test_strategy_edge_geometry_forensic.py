from __future__ import annotations

from scripts.forensic_strategy_edge_geometry import (
    group_metrics, outcome_path_result, stop_alternatives, target_rows,
    task_b, task_c, task_d,
)
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket
from app.engine_paper.scalping_shadow import (
    CausalTarget, ShadowCostInputs, ShadowGeometryCandidate, ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


def test_target_inventory_recomputes_all_causal_levels_without_lookahead() -> None:
    diagnostic = {"target_considerations": [
        {"target_price": 100.2, "target_source": "LOCAL_5M", "target_timeframe": "5m",
         "causal": True, "future_safe": True, "directionally_valid": True},
        {"target_price": 100.6, "target_source": "STRUCTURAL", "target_timeframe": "5m",
         "causal": True, "future_safe": True, "directionally_valid": True},
        {"target_price": 101.0, "target_source": "1H", "target_timeframe": "1h",
         "causal": True, "future_safe": False, "directionally_valid": True},
    ]}
    rows = target_rows(diagnostic, 100, 20, 10)
    assert [row["price"] for row in rows] == [100.2, 100.6]
    assert abs(rows[0]["net_rr"] - 1 / 3) < 1e-12
    assert abs(rows[1]["net_rr"] - 5 / 3) < 1e-12


def test_causal_outcome_is_conservative_when_stop_and_target_share_candle() -> None:
    outcome = {"entry_status": "ENTERED", "terminal_price": 100,
               "closed_candle_path": [{"high": 106, "low": 94, "close": 102}]}
    result = outcome_path_result(outcome, entry=100, stop=95, target=105, side="LONG", costs=10)
    assert result["outcome"] == "STOP_FIRST"
    assert result["net_r"] == -1


def test_stop_alternatives_are_directional_and_nearest_first() -> None:
    observation = {"setup": {"raw": {"context": {"causal_support_candidates": [
        {"price": 98, "validated": True, "future_safe": True, "still_relevant": True},
        {"price": 99, "validated": True, "future_safe": True, "still_relevant": True},
        {"price": 101, "validated": True, "future_safe": True, "still_relevant": True},
    ]}}}}
    rows = stop_alternatives(observation, side="LONG", entry=100, atr_buffer=.25)
    assert [row["invalidation_level"] for row in rows] == [101, 99, 98]
    assert rows[0]["valid"] is False
    assert rows[1]["valid"] is True


def _row(index: int, *, net_rr: float = .8, required: float = 2.0,
         alternative: float = 3.0, outcome: float = -1.0) -> dict:
    target_outcome = {"net_r": outcome, "target_hit": outcome > 0,
                      "stop_hit": outcome == -1, "timeout": False}
    return {"candidate_id": str(index), "cycle_boundary": index, "symbol": "BTCUSDT",
            "setup_type": "MOMENTUM", "side": "LONG", "regime": "TREND",
            "net_rr": net_rr, "final_required_rr": required, "net_outcome_r": outcome,
            "rr_pass": net_rr >= required, "timeout": False, "trend_alignment": "ALIGNED",
            "momentum_context": "IMPULSE", "target_distance_bps": 30,
            "best_causal_target_distance_bps": 80, "target_efficiency": net_rr / alternative,
            "farther_causal_targets": [{"price": 108}],
            "selector_missed_dynamic_valid_target": alternative >= required,
            "all_causal_targets": [{"price": 103, "net_rr": net_rr, "distance_bps": 30},
                                   {"price": 108, "net_rr": alternative, "distance_bps": 80,
                                    "causal_outcome": target_outcome}],
            "stop_distance_bps": 20, "stop_efficiency": 1.0, "mae_bps": 10,
            "machine_reason": "DYNAMIC_NET_RR_CONSERVATIVE_EV_REJECT", "final_stage": "EXPECTANCY_GATE"}


def test_target_task_detects_late_dynamic_ordering_defect() -> None:
    report = task_c([_row(1)], {"cycle_boundary": 1})
    assert report["final_verdict"] == "TARGET_ORDERING_DEFECT"
    assert report["selector_missed_count"] == 1
    assert report["bounded_replay"]["no_lookahead"] is True


def test_runtime_selector_continues_to_farther_causal_target_for_dynamic_rr() -> None:
    boundary = 2_000
    candidate = ShadowGeometryCandidate(
        trade_profile_id="trade-5m-v2", symbol="BTCUSDT", boundary_ms=boundary,
        direction="BULLISH", entry=100, causal_invalidation=99.5, atr=0,
        targets=(CausalTarget(100.35, "LOCAL_5M", boundary),
                 CausalTarget(101, "STRUCTURAL", boundary)), setup_identity="fixture",
    )
    costs = ShadowCostInputs(
        entry_fee_bps=0, exit_fee_bps=0, entry_slippage_bps=0,
        exit_slippage_bps=0, safety_margin_bps=0, adverse_fill_reserve_bps=0,
        spread_bps=0, depth_impact_bps=0, spread_authoritative=True,
        depth_authoritative=True, commission_authoritative=True,
    )
    result = evaluate_scalping_shadow(candidate, costs, ShadowGeometryConfig(
        atr_buffer_multiplier=.25, stop_envelope_bps=50,
        minimum_target_diagnostic_bps=60, production_rr_floor=.6,
        empirical_bucket=EmpiricalSetupBucket("MOMENTUM", "BULLISH", 100, 60),
        minimum_ev_reserve_r=.05,
    ))
    assert result.first_actionable_target["target_price"] == 100.35
    assert result.causal_target == 101
    assert result.net_rr == 2
    assert result.valid_plan is True


def test_stop_task_does_not_treat_rounding_noise_as_suboptimal() -> None:
    row = _row(1); row["stop_efficiency"] = .99999
    report = task_b([row], {"cycle_boundary": 1})
    assert report["selector_suboptimal"] is False
    assert report["software_defect"] is False


def test_edge_groups_and_variants_are_bounded_and_holdout_aware() -> None:
    rows = [_row(index, outcome=(1 if index % 3 == 0 else -1)) for index in range(20)]
    assert len(group_metrics(rows)) <= 30
    report = task_d(rows, {"cycle_boundary": 20})
    assert report["variants_evaluated"] <= 6
    assert report["promotion_allowed"] is False
    assert all(row["selection_is_causal"] for row in report["variants"])
