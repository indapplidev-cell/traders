from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)
from app.engine_risk.execution_budget import SharedAccountExecutionBudget
from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_limits import ResearchRiskLimits
from app.engine_risk.risk_policy import RiskPolicy
from tests.engine_risk_01_helpers import strategy_decision


BOUNDARY = 1_700_000_000_000


def candidate(**overrides):
    values = dict(
        trade_profile_id="trade-5m-v1", symbol="SUIUSDT", boundary_ms=BOUNDARY,
        direction="BULLISH", entry=100.0, causal_invalidation=99.70, atr=0.10,
        targets=(CausalTarget(102.0, "LOCAL_5M", BOUNDARY),),
    )
    values.update(overrides)
    return ShadowGeometryCandidate(**values)


def costs(**overrides):
    values = dict(
        spread_bps=1.0, depth_impact_bps=2.0,
        spread_source="BINANCE_PUBLIC_BOOK_TICKER",
        depth_impact_source="BINANCE_PUBLIC_MARKET_DATA_DEPTH",
        spread_authoritative=True, depth_authoritative=True,
    )
    values.update(overrides)
    return ShadowCostInputs(**values)


def config(**overrides):
    values = dict(
        atr_buffer_multiplier=0.25, stop_envelope_bps=50.0,
        minimum_target_diagnostic_bps=45.0,
    )
    values.update(overrides)
    return ShadowGeometryConfig(**values)


@pytest.mark.parametrize("multiplier,expected_stop", [
    (0.25, 99.675), (0.50, 99.65), (0.75, 99.625), (1.00, 99.60),
])
def test_atr_cohorts_are_deterministic_and_preserve_causal_invalidation(multiplier, expected_stop):
    row = evaluate_scalping_shadow(candidate(), costs(), config(atr_buffer_multiplier=multiplier))
    assert row.final_stop == pytest.approx(expected_stop)
    assert row.final_stop <= row.causal_invalidation < row.entry
    assert row.atr_buffer_multiplier == multiplier


def test_stop_is_rejected_not_clipped_inside_causal_invalidation():
    row = evaluate_scalping_shadow(
        candidate(causal_invalidation=99.30, atr=0.20), costs(), config(stop_envelope_bps=50.0)
    )
    assert row.rejection_reason == R.PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE
    assert row.final_stop == pytest.approx(99.25)
    assert row.final_stop < row.causal_invalidation
    assert row.stop_distance_bps == pytest.approx(75.0)
    assert row.entry_fee_bps == 10.0 and row.exit_fee_bps == 10.0
    assert row.entry_slippage_bps == 2.0 and row.exit_slippage_bps == 2.0
    assert row.safety_margin_bps == 3.0
    assert row.fee_source == "CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE"
    assert row.spread_bps == 1.0 and row.depth_impact_bps == 2.0


def test_target_hierarchy_is_causal_local_then_structural_then_higher_tf():
    targets = (
        CausalTarget(101.0, "HIGHER_TF", BOUNDARY - 10),
        CausalTarget(101.5, "STRUCTURAL", BOUNDARY - 20),
        CausalTarget(101.8, "LOCAL_5M", BOUNDARY - 30),
        CausalTarget(100.5, "LOCAL_5M", BOUNDARY + 1),
    )
    row = evaluate_scalping_shadow(candidate(targets=targets), costs(), config())
    assert row.target_source_type == "LOCAL_5M"
    assert row.causal_target == 101.8


def test_future_only_target_does_not_leak_and_missing_target_stays_explicit():
    future = (CausalTarget(102.0, "LOCAL_5M", BOUNDARY + 1),)
    row = evaluate_scalping_shadow(candidate(targets=future), costs(), config())
    assert row.rejection_reason == R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL
    assert row.target_available is False
    assert row.causal_target is None


@pytest.mark.parametrize("minimum", [45.0, 60.0, 80.0])
def test_minimum_target_cohorts_are_diagnostic_and_never_synthesize_target(minimum):
    target = (CausalTarget(100.50, "LOCAL_5M", BOUNDARY),)
    row = evaluate_scalping_shadow(candidate(targets=target), costs(), config(minimum_target_diagnostic_bps=minimum))
    assert row.causal_target == 100.50
    assert row.target_distance_bps == pytest.approx(50.0)
    assert row.minimum_target_diagnostic_pass is (minimum <= 50.0)


def test_missing_spread_fails_closed_and_preserves_known_geometry_and_costs():
    row = evaluate_scalping_shadow(candidate(), costs(spread_bps=None, spread_authoritative=False), config())
    assert row.rejection_reason == R.PAPER_NO_PLAN_MISSING_AUTHORITATIVE_SPREAD
    assert row.economic_gate_enabled is True
    assert row.economic_gate_pass is False
    assert row.final_stop is not None and row.causal_target is not None
    assert row.entry_fee_bps == 10.0 and row.spread_bps is None


def test_positive_gross_edge_but_negative_net_edge_rejects_with_raw_diagnostics():
    close = (CausalTarget(100.20, "LOCAL_5M", BOUNDARY),)
    row = evaluate_scalping_shadow(candidate(targets=close), costs(spread_bps=5.0, depth_impact_bps=5.0), config())
    assert row.gross_reward_bps == pytest.approx(20.0)
    assert row.expected_net_edge_bps < 0
    assert row.rejection_reason == R.PAPER_REJECT_NEGATIVE_NET_EDGE


def test_gross_rr_pass_net_rr_fail_and_cohorts_cannot_bypass_cost_gate():
    target = (CausalTarget(100.70, "LOCAL_5M", BOUNDARY),)
    row = evaluate_scalping_shadow(candidate(targets=target), costs(), config())
    assert row.gross_rr >= 1.5
    assert row.net_rr < 1.5
    assert row.rejection_reason == R.PAPER_REJECT_LOW_NET_RR
    assert row.rr_cohorts_gross["1.20"] is True
    assert row.rr_cohorts_net["1.20"] is False
    assert row.execution_eligible is False


def test_depth_impact_too_high_fails_before_rr_approval():
    row = evaluate_scalping_shadow(candidate(), costs(depth_impact_bps=21.0), config())
    assert row.rejection_reason == R.PAPER_REJECT_DEPTH_IMPACT_TOO_HIGH
    assert row.net_rr is None


def test_net_edge_rr_and_break_even_are_computed_not_hardcoded():
    row = evaluate_scalping_shadow(candidate(), costs(), config())
    assert row.valid_plan and row.final_shadow_approval
    assert row.gross_rr == pytest.approx(200.0 / 32.5)
    assert row.expected_net_edge_bps == pytest.approx(170.0)
    assert row.effective_risk_bps == pytest.approx(62.5)
    assert row.net_rr == pytest.approx(170.0 / 62.5)
    assert row.break_even_win_rate == pytest.approx(62.5 / 232.5)
    assert row.execution_eligible is False


@pytest.mark.parametrize("reason", ["NO_PLAN", "MISSING_TARGET", "STOP_TOO_WIDE", "NEGATIVE_NET_EDGE", "LOW_RR"])
def test_invalid_plan_never_touches_execution_budget(reason):
    budget = SharedAccountExecutionBudget(max_approved_plans=1, max_risk_bps=100)
    before = budget.state
    # Geometry rejection paths never receive this execution authority object.
    if reason == "NO_PLAN":
        evaluate_scalping_shadow(candidate(causal_invalidation=None), costs(), config())
    elif reason == "MISSING_TARGET":
        evaluate_scalping_shadow(candidate(targets=()), costs(), config())
    elif reason == "STOP_TOO_WIDE":
        evaluate_scalping_shadow(candidate(causal_invalidation=99.0), costs(), config())
    elif reason == "NEGATIVE_NET_EDGE":
        evaluate_scalping_shadow(candidate(targets=(CausalTarget(100.1, "LOCAL_5M", BOUNDARY),)), costs(), config())
    else:
        evaluate_scalping_shadow(candidate(targets=(CausalTarget(100.7, "LOCAL_5M", BOUNDARY),)), costs(), config())
    assert budget.state == before


def test_valid_final_approval_consumes_once_and_failed_finalization_releases():
    budget = SharedAccountExecutionBudget(max_approved_plans=2, max_risk_bps=100)
    row = evaluate_scalping_shadow(candidate(), costs(), config())
    assert row.valid_plan
    assert budget.reserve(row.candidate_id, row.effective_risk_bps)
    assert budget.reserve(row.candidate_id, row.effective_risk_bps)
    assert budget.state.reserved_count == 1
    assert budget.commit(row.candidate_id)
    assert budget.commit(row.candidate_id)
    assert budget.state.committed_count == 1

    second = row.candidate_id + ":retry"
    assert budget.reserve(second, 20)
    assert budget.release(second)
    assert budget.state.reserved_count == 0


def test_research_counters_are_profile_separate_while_execution_budget_is_shared():
    limits = ResearchRiskLimits()
    restrictive = RiskConfig(
        max_research_preapprovals_per_symbol_per_day=1,
        max_research_preapprovals_total_per_day=1,
        max_research_preapprovals_per_direction_per_day=1,
    )
    decision = strategy_decision(decision_id="strategy:15m")
    first = RiskPolicy(restrictive, limits, SimpleNamespace(
        profile_id="trade-15m-v1", parameter_set_id="15", risk_shadow_policy_id="risk",
        minimum_planned_rr=1.5,
    )).evaluate(decision)
    second = RiskPolicy(restrictive, limits, SimpleNamespace(
        profile_id="trade-5m-v1", parameter_set_id="5", risk_shadow_policy_id="risk",
        minimum_planned_rr=1.5,
    )).evaluate(strategy_decision(decision_id="strategy:5m"))
    assert first.risk_pre_approved and second.risk_pre_approved
    assert limits.profile_attempts("trade-15m-v1", decision.closed_until_ms) == 1
    assert limits.profile_attempts("trade-5m-v1", decision.closed_until_ms) == 1

    shared = SharedAccountExecutionBudget(max_approved_plans=1, max_risk_bps=100)
    assert shared.reserve("trade-15m-v1:plan", 50)
    assert not shared.reserve("trade-5m-v1:plan", 10)


def test_15m_risk_policy_semantics_are_equivalent_after_profile_keying():
    source = strategy_decision(decision_id="strategy:15m:equivalence")
    baseline = RiskPolicy().evaluate(source)
    explicit = RiskPolicy(runtime_parameters=SimpleNamespace(
        profile_id="trade-15m-v1", parameter_set_id="15", risk_shadow_policy_id="risk",
        minimum_planned_rr=1.5,
    )).evaluate(source)
    assert explicit.risk_status == baseline.risk_status
    assert explicit.risk_level == baseline.risk_level
    assert explicit.risk_score == baseline.risk_score
    assert explicit.risk_pre_approved == baseline.risk_pre_approved
    assert explicit.requires_execution_review == baseline.requires_execution_review
    assert explicit.rejection_reasons == baseline.rejection_reasons


class Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Transport:
    def get(self, url, *, params=None):
        if url.endswith("bookTicker"):
            return Response({"bidPrice": "99.9", "bidQty": "2", "askPrice": "100.1", "askQty": "2"})
        return Response({"bids": [["99.9", "1"], ["99.8", "1"]], "asks": [["100.1", "1"], ["100.2", "1"]]})


def test_existing_public_client_boundary_provides_spread_and_depth_without_orders():
    client = BinancePublicRestClient(transport=Transport(), max_retries=0)
    ticker = client.fetch_book_ticker("BTCUSDT")
    depth = client.estimate_round_trip_depth_impact("BTCUSDT", Decimal("1.5"), limit=100)
    assert ticker.spread_bps == pytest.approx(20.0)
    assert depth.buy_vwap == Decimal("100.1333333333333333333333333")
    assert depth.sell_vwap == Decimal("99.86666666666666666666666667")
    assert depth.depth_impact_bps > 0


class CostSource:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def load(self, symbol, entry, *, safety_margin_bps):
        self.calls.append((symbol, entry, safety_margin_bps))
        return self.value


def production_parameters():
    return SimpleNamespace(minimum_planned_rr=1.5, cost_safety_margin_bps=3.0)


def admitted_5m_risk(**context_changes):
    context = {
        "confirmation_close": 100.0,
        "causal_support_level": 99.70,
        "causal_resistance_level": 102.0,
        "causal_invalidation_level": 99.70,
        "causal_target_level": 102.0,
        "nearest_opposite_level": 102.0,
        "atr_value": 0.10,
    }
    context.update(context_changes)
    return RiskPolicy(runtime_parameters=SimpleNamespace(
        profile_id="trade-5m-v1", parameter_set_id="5m", risk_shadow_policy_id="risk",
        minimum_planned_rr=1.5,
    )).evaluate(strategy_decision(
        decision_id="strategy:5m:production", timeframe="5m", context=context,
    ))


def test_production_5m_runner_enforces_cost_gate_and_preserves_diagnostics():
    source = CostSource(costs())
    plan = ScalpingPaperRunner(
        runtime_parameters=production_parameters(), cost_source=source
    ).process_risk_decision(admitted_5m_risk())
    diagnostic = plan.paper_context["scalping_geometry_diagnostics"]

    assert plan.paper_status == "PAPER_PLAN_READY"
    assert plan.planned_rr == diagnostic["gross_rr"]
    assert diagnostic["net_rr"] > 1.5
    assert diagnostic["break_even_win_rate"] is not None
    assert diagnostic["rr_cohorts_gross"] == {"1.00": True, "1.20": True, "1.50": True}
    assert diagnostic["rr_cohorts_net"] == {"1.00": True, "1.20": True, "1.50": True}
    assert plan.paper_context["economic_gate_enabled"] is True
    assert len(source.calls) == 1


def test_production_5m_runner_fails_closed_when_public_cost_data_is_missing():
    source = CostSource(costs(spread_bps=None, spread_authoritative=False))
    plan = ScalpingPaperRunner(
        runtime_parameters=production_parameters(), cost_source=source
    ).process_risk_decision(admitted_5m_risk())
    diagnostic = plan.paper_context["scalping_geometry_diagnostics"]

    assert plan.paper_status == "NO_PLAN"
    assert diagnostic["rejection_reason"] == R.PAPER_NO_PLAN_MISSING_AUTHORITATIVE_SPREAD
    assert diagnostic["entry"] == 100.0
    assert diagnostic["final_stop"] is not None
    assert diagnostic["causal_target"] == 102.0
    assert diagnostic["spread_bps"] is None


def test_production_5m_runner_does_not_query_costs_before_geometry_is_valid():
    source = CostSource(costs())
    plan = ScalpingPaperRunner(
        runtime_parameters=production_parameters(), cost_source=source
    ).process_risk_decision(admitted_5m_risk(causal_support_level=99.0, causal_invalidation_level=99.0))
    diagnostic = plan.paper_context["scalping_geometry_diagnostics"]

    assert plan.paper_status == "NO_PLAN"
    assert diagnostic["rejection_reason"] == R.PAPER_NO_PLAN_CAUSAL_STOP_TOO_WIDE_FOR_PROFILE
    assert diagnostic["final_stop"] < diagnostic["causal_invalidation"]
    assert diagnostic["entry_fee_bps"] == 10.0
    assert diagnostic["exit_fee_bps"] == 10.0
    assert diagnostic["entry_slippage_bps"] == 2.0
    assert diagnostic["exit_slippage_bps"] == 2.0
    assert diagnostic["safety_margin_bps"] == 3.0
    assert diagnostic["spread_bps"] is None
    assert diagnostic["depth_impact_bps"] is None
    assert source.calls == []
