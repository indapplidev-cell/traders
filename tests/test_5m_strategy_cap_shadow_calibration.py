from __future__ import annotations

from types import SimpleNamespace

from app.engine_observation.strategy_cap_calibration import (
    calibrate,
    classify_not_evaluated_reason,
)
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)


def row(*, quality="NOT_EVALUATED", phase="NO_IMPULSE", reason="STRATEGY_REJECT_WEAK_QUALITY",
        boundary=1_800_000_000_000, raw=92.5):
    return {
        "run_id": f"run-{boundary}", "result_id": boundary, "boundary": boundary,
        "symbol": "BTCUSDT", "profile": "trade-5m-v1", "parameter_set_id": "p5",
        "analysis": {"regime": "UP", "entry_quality": quality, "impulse_phase": phase,
                     "impulse_direction": "UP", "impulse_context": {"data_sufficient": True}},
        "setup": {
            "setup_status": "SETUP_CANDIDATE", "setup_type": "BREAKOUT_CONTINUATION",
            "direction_hint": "BULLISH", "setup_quality": "WEAK", "source_entry_quality": quality,
            "quality_score": 64.999, "quality_diagnostics": {
                "source_analysis_entry_quality": quality, "conflict_penalty": 0,
                "invalidation_penalty": 0, "capped_by_analysis_entry_quality": True,
            }, "quality_reasons": ["QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY"],
        },
        "strategy": {
            "decision_status": "REJECT", "direction_hint": "BULLISH", "strategy_score": 64.999,
            "strategy_raw_score": raw, "component_scores": {
                "structure": 32.5, "candle_confirmation": 30, "context_alignment": raw - 62.5,
            }, "context": {"direction_hint": "BULLISH", "setup_type": "BREAKOUT_CONTINUATION",
                           "confirmation_close": 100, "causal_invalidation_level": 99.5,
                           "atr_value": .1, "causal_target_level": 102},
            "rejection_reasons": [reason],
        },
        "risk": {"risk_status": "REJECT"}, "paper": {"paper_status": "NO_PLAN", "paper_context": {}},
    }


def test_not_evaluated_no_impulse_is_non_applicability_not_true_weak():
    assert classify_not_evaluated_reason(row()) == "NOT_EVALUATED_NO_APPLICABLE_ENTRY_PATTERN"
    assert classify_not_evaluated_reason(row(quality="WEAK")) is None


def test_shadow_matrix_is_factor_isolated_and_production_equivalent():
    report = calibrate([row()])
    cohorts = report["cohorts"]
    assert cohorts["C0_PRODUCTION"]["strategy_pass"] == 0
    assert cohorts["C1_NO_WEAK_CAP_ONLY"]["strategy_pass"] == 0
    assert cohorts["C2_NOT_EVALUATED_BYPASS"]["strategy_pass"] == 1
    assert cohorts["C3_UNKNOWN_CAP_65"]["strategy_pass"] == 1
    assert cohorts["C4_NOT_EVALUATED_RAW_GE_92.5"]["strategy_pass"] == 1
    assert cohorts["C4_NOT_EVALUATED_RAW_GE_95"]["strategy_pass"] == 0
    assert report["side_effects"] == {
        "risk_reservations": 0, "paper_entities": 0,
        "trading_mutations": 0, "binance_order_api_calls": 0,
    }
    c2 = next(item for item in report["records"] if item["shadow_policy_id"] == "C2_NOT_EVALUATED_BYPASS")
    assert c2["production_terminal_reason"] == "STRATEGY_REJECT_WEAK_QUALITY"
    assert c2["weak_quality_gate"] is False
    assert c2["spread_bps"] is None and c2["total_cost_bps"] is None
    assert c2["paper_not_reached_reason"] == "UPSTREAM_ECONOMICS_NOT_REPLAYABLE_OR_REJECTED"


def test_true_evaluated_weak_is_not_bypassed():
    report = calibrate([row(quality="WEAK", phase="IMPULSE_DETECTED")])
    assert report["cohorts"]["C2_NOT_EVALUATED_BYPASS"]["strategy_pass"] == 0


def test_conflict_gate_remains_terminal_for_every_shadow_policy():
    report = calibrate([row(reason="STRATEGY_REJECT_CONFLICTING_CONTEXT")])
    assert all(value["strategy_pass"] == 0 for value in report["cohorts"].values())


def candidate():
    return ShadowGeometryCandidate(
        "trade-5m-v1", "BTCUSDT", 1_800_000_000_000, "BULLISH", 100, 99.5, .1,
        (CausalTarget(102, "LOCAL_5M", 1_800_000_000_000),),
    )


def config():
    return ShadowGeometryConfig(.25, 80, 45)


def causal_costs(timestamp, cutoff):
    return ShadowCostInputs(
        spread_bps=1, depth_impact_bps=1, spread_authoritative=True, depth_authoritative=True,
        bid=99.99, ask=100.01, buy_vwap=100.02, sell_vwap=99.98,
        economic_input_timestamp_ms=timestamp, decision_cutoff_timestamp_ms=cutoff,
        economic_input_source="TEST_BOUNDARY_SNAPSHOT", require_causal_timestamp=True,
    )


def test_exact_boundary_economics_are_accepted():
    result = evaluate_scalping_shadow(candidate(), causal_costs(1000, 1000), config())
    assert result.economic_gate_pass is True
    assert result.economic_input_age_ms == 0


def test_later_quote_and_stale_quote_fail_closed():
    future = evaluate_scalping_shadow(candidate(), causal_costs(1001, 1000), config())
    stale = evaluate_scalping_shadow(candidate(), causal_costs(1000, 7001), config())
    assert future.rejection_reason == "PAPER_NO_PLAN_STALE_OR_FUTURE_ECONOMIC_INPUT"
    assert stale.rejection_reason == "PAPER_NO_PLAN_STALE_OR_FUTURE_ECONOMIC_INPUT"


def test_repeated_observations_share_one_causal_opportunity():
    report = calibrate([row(), row(boundary=1_800_000_300_000)])
    cohort = report["cohorts"]["C2_NOT_EVALUATED_BYPASS"]
    assert cohort["strategy_pass"] == 2
    assert cohort["unique_opportunities"] == 1
    assert cohort["repeat_observations"] == 1


def test_prospective_capture_is_5m_only_pre_strategy_and_side_effect_free():
    class Source:
        calls = 0

        def load(self, symbol, entry, *, safety_margin_bps):
            self.calls += 1
            return causal_costs(1000, 1001)

    source = Source()
    runner = object.__new__(PipelineRunner)
    runner.config = SimpleNamespace(trade_profile_id="trade-5m-v1")
    runner.runtime_parameters = SimpleNamespace(cost_safety_margin_bps=3)
    runner.strategy_cap_cost_source = source
    setup = SimpleNamespace(
        status="SETUP_CANDIDATE", symbol="BTCUSDT", closed_until_ms=900,
        setup_id="setup-1", context={"confirmation_close": 100},
    )
    snapshot = runner._capture_strategy_cap_economics(setup)
    assert snapshot["capture_status"] == "CAPTURED_BEFORE_STRATEGY_DECISION"
    assert snapshot["causally_usable"] is True
    assert source.calls == 1
    runner.config = SimpleNamespace(trade_profile_id="trade-15m-v1")
    assert runner._capture_strategy_cap_economics(setup) is None
    assert source.calls == 1
