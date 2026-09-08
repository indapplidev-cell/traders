from scripts.forensic_scalping_rr_dynamic_anchor import (
    EXPECTED_SYMBOLS, build_report, freeze_cohort, reject_streak, rr_subreason,
    select_latest_completed_cycle,
)
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy
from app.engine_paper.scalping_shadow import compute_net_economics


def row(boundary, symbol, *, result=None, candidate=None):
    diagnostic = None if result is None else {
        "candidate_id": candidate or f"candidate:{boundary}:{symbol}",
        "opportunity_id": f"opportunity:{symbol}", "entry": 100, "final_stop": 99,
        "causal_target": 102, "stop_distance_bps": 100, "target_distance_bps": 200,
        "gross_rr": 2, "net_rr": 1.0, "required_rr": .6,
        "effective_total_cost_bps": 20, "entry_fee_bps": 7.5, "exit_fee_bps": 7.5,
        "spread_bps": 1, "entry_slippage_bps": 1, "exit_slippage_bps": 1,
        "depth_impact_bps": 0, "safety_margin_bps": 0, "adverse_fill_reserve_bps": 2,
        "expectancy_gate_reason": ("DYNAMIC_NET_RR_CONSERVATIVE_EV_PASS" if result == "PASS" else "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"),
        "valid_plan": result == "PASS", "probability_sample_size": 0,
    }
    return {"cycle_boundary": boundary, "symbol": symbol, "run_id": f"run:{boundary}:{symbol}",
            "status": "SUCCESS", "finished_at": str(boundary), "strategy": {"strategy_type": "x"},
            "paper": {"parameter_set_id": "scalping-v2-set-2", "resolved_config_hash": "hash",
                      "paper_direction": "BULLISH", "paper_context": {"production_rr_floor": .6,
                      "scalping_geometry_diagnostics": diagnostic} if diagnostic else {}}}


def cycle(boundary, rr=None):
    return [row(boundary, symbol, result=rr if index == 0 else None) for index, symbol in enumerate(sorted(EXPECTED_SYMBOLS))]


def test_dynamic_anchor_uses_latest_complete_cycle():
    rows = cycle(1_788_885_900_000) + cycle(1_788_886_200_000)[:-1]
    assert select_latest_completed_cycle(rows)[0] == 1_788_885_900_000


def test_frozen_cohort_does_not_change_when_new_rolling_rows_arrive():
    anchor = 1_788_900_000_000
    rows = cycle(anchor - 300_000, "REJECT") + cycle(anchor, "REJECT")
    frozen, _ = freeze_cohort(rows, anchor)
    changed, _ = freeze_cohort(rows + cycle(anchor + 300_000, "PASS"), anchor)
    assert [item["candidate_id"] for item in frozen] == [item["candidate_id"] for item in changed]


def test_last_pass_and_reject_streak_are_detected_without_fixed_count():
    anchor = 1_788_900_000_000
    rows = cycle(anchor - 600_000, "PASS") + cycle(anchor - 300_000, "REJECT") + cycle(anchor, "REJECT")
    cohort, _ = freeze_cohort(rows, anchor)
    streak, last_pass = reject_streak(cohort)
    assert len(streak) == 2
    assert last_pass["rr_result"] == "PASS"


def test_report_labels_insufficient_statistics_and_no_legacy_fallback():
    anchor = 1_788_900_000_000
    cohort, report = build_report(cycle(anchor, "REJECT"), "0031", "revision")
    assert report["reject_reason_distribution"] == {"INSUFFICIENT_PROBABILITY": 1}
    assert cohort[0]["classification"] == "INSUFFICIENT_STATISTICS"
    assert report["formula_audit"]["fallback_rr_value"] is None


def test_units_costs_long_short_and_equality_boundaries():
    assert compute_net_economics(gross_reward_bps=80, gross_risk_bps=40, total_cost_bps=20) == (60, 60, 1)
    for direction in ("BULLISH", "BEARISH"):
        item = row(1_788_900_000_000, "BTCUSDT", result="PASS")
        item["paper"]["paper_direction"] = direction
        assert item["paper"]["paper_context"]["production_rr_floor"] == .6
    decision = evaluate_expectancy(net_win_bps=120, net_loss_bps=40,
        bucket=EmpiricalSetupBucket("BREAKOUT", "BULLISH", 100, 60))
    assert decision.candidate_net_rr == 3
    assert decision.admitted
    assert rr_subreason({"net_rr": .6, "dynamic_required_net_rr": .6}, .6) == "OTHER"
