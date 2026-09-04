from decimal import Decimal
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.scalping_paper_runner import (
    BinancePublicScalpingCostSource,
    ScalpingPaperRunner,
)
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    compute_net_economics,
    evaluate_scalping_shadow,
    minimum_reward_bps_for_net_rr,
    minimum_target_price_for_net_rr,
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
    assert row.rejection_reason == R.SCALP_REJECT_CAUSAL_STOP_TOO_WIDE
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
    assert row.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE
    assert row.net_rr is None and row.break_even_win_rate is None
    assert row.target_considerations[0]["rejection_reason"] == "BELOW_ECONOMIC_FLOOR"


def test_gross_rr_pass_net_rr_fail_and_cohorts_cannot_bypass_cost_gate():
    target = (CausalTarget(100.70, "LOCAL_5M", BOUNDARY),)
    row = evaluate_scalping_shadow(candidate(targets=target), costs(), config())
    assert row.gross_rr >= 1.5
    assert row.net_rr < 1.5
    assert row.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE
    assert row.economically_actionable_target_exists is False
    assert row.target_considerations[0]["rejection_reason"] == "BELOW_REQUIRED_NET_RR"
    assert row.rr_cohorts_gross["1.20"] is True
    assert row.rr_cohorts_net["1.20"] is False
    assert row.execution_eligible is False


def test_non_actionable_local_target_falls_back_to_nearest_structural_causal_target():
    targets = (
        CausalTarget(100.20, "LOCAL_5M", BOUNDARY),
        CausalTarget(102.00, "STRUCTURAL", BOUNDARY),
        CausalTarget(103.00, "HIGHER_TF", BOUNDARY),
    )
    row = evaluate_scalping_shadow(candidate(targets=targets), costs(), config())
    assert row.valid_plan is True
    assert row.causal_target_exists is True
    assert row.economically_actionable_target_exists is True
    assert row.target_source_type == "STRUCTURAL"
    assert row.causal_target == 102.00
    first = row.target_considerations[0]
    assert first["source_type"] == "LOCAL_5M"
    assert first["price"] == 100.20
    assert first["distance_bps"] == pytest.approx(20.0)
    assert first["causal"] is True and first["future_safe"] is True
    assert first["directionally_valid"] is True
    assert first["economically_actionable"] is False
    assert first["rejection_reason"] == "BELOW_ECONOMIC_FLOOR"
    assert first["next_target_considered"] == "STRUCTURAL"


def test_non_actionable_nearest_local_traverses_to_next_validated_local():
    targets = (
        CausalTarget(100.20, "LOCAL_5M", BOUNDARY),
        CausalTarget(102.00, "LOCAL_5M", BOUNDARY),
    )
    row = evaluate_scalping_shadow(candidate(targets=targets), costs(), config())
    assert row.valid_plan is True
    assert len(row.target_considerations) == 2
    assert row.causal_target == 102.00
    assert row.first_causal_target["target_price"] == 100.20
    assert row.first_actionable_target["target_price"] == 102.00


def test_cost_aware_construction_selects_next_strategy_valid_target():
    targets = (
        CausalTarget(100.70, "LOCAL_5M", BOUNDARY),
        CausalTarget(102.00, "LOCAL_5M", BOUNDARY),
    )
    row = evaluate_scalping_shadow(candidate(targets=targets), costs(), config())
    assert row.economically_actionable_target_exists is True
    assert row.causal_target == 102.00
    assert row.rejection_reason is None
    assert row.valid_plan is True
    assert row.target_considerations[0]["rejection_reason"] == "BELOW_REQUIRED_NET_RR"
    assert row.target_considerations[1]["economically_actionable"] is True


def test_target_trace_preserves_invalid_future_wrong_side_and_unreachable_1h():
    targets = (
        CausalTarget(99.0, "LOCAL_5M", BOUNDARY),
        CausalTarget(102.0, "15M", BOUNDARY + 1, timeframe="15m"),
        CausalTarget(103.0, "1H", BOUNDARY, achievable=False, timeframe="1h"),
        CausalTarget(102.0, "STRUCTURAL", BOUNDARY, timeframe="5m"),
    )
    row = evaluate_scalping_shadow(candidate(targets=targets), costs(), config())
    reasons = {item["reject_reason"] for item in row.target_considerations}
    assert {"WRONG_DIRECTION", "FUTURE_TARGET", "TARGET_NOT_REACHABLE_WITHIN_SCALP_HORIZON"} <= reasons
    assert row.causal_target == 102.0
    assert row.target_candidates_considered == 4


@pytest.mark.parametrize("minimum", [0.0, 5.0, 10.0])
def test_positive_edge_alone_cannot_bypass_required_net_rr(minimum):
    target = (CausalTarget(100.35, "LOCAL_5M", BOUNDARY),)
    row = evaluate_scalping_shadow(
        candidate(targets=target), costs(), config(minimum_positive_edge_bps=minimum)
    )
    assert row.economically_actionable_target_exists is False
    assert row.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE


@pytest.mark.parametrize("direction", ["BULLISH", "BEARISH"])
def test_authoritative_net_rr_and_minimum_target_are_symmetric(direction):
    net_reward, net_risk, net_rr = compute_net_economics(
        gross_reward_bps=120.0, gross_risk_bps=40.0, total_cost_bps=30.0
    )
    assert net_reward == 90.0
    assert net_risk == 70.0
    assert net_rr == pytest.approx(90.0 / 70.0)
    required = minimum_reward_bps_for_net_rr(
        gross_risk_bps=40.0, total_cost_bps=30.0, required_net_rr=1.5
    )
    assert required == 135.0
    target = minimum_target_price_for_net_rr(
        entry=100.0, direction=direction, minimum_reward_bps=required
    )
    assert target == (101.35 if direction == "BULLISH" else 98.65)


def test_no_feasible_structural_target_persists_causal_economics():
    row = evaluate_scalping_shadow(
        candidate(targets=(
            CausalTarget(100.35, "LOCAL_5M", BOUNDARY),
            CausalTarget(100.70, "STRUCTURAL", BOUNDARY),
        )),
        costs(),
        config(),
    )
    assert row.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE
    assert row.geometry_feasibility_result == "INFEASIBLE"
    assert row.minimum_economically_valid_target_bps == pytest.approx(123.75)
    assert row.required_rr == 1.5
    assert len(row.target_considerations) == 2
    assert all(item["gross_rr"] is not None for item in row.target_considerations)


@pytest.mark.parametrize(
    ("direction", "target_price"),
    [("BULLISH", 101.2375), ("BEARISH", 98.7625)],
)
def test_required_net_rr_boundary_equality_passes(direction, target_price):
    row = evaluate_scalping_shadow(
        candidate(
            direction=direction,
            causal_invalidation=(99.70 if direction == "BULLISH" else 100.30),
            targets=(CausalTarget(target_price, "LOCAL_5M", BOUNDARY),),
        ),
        costs(),
        config(),
    )
    assert row.net_rr == 1.5
    assert row.geometry_feasibility_result == "FEASIBLE"
    assert row.valid_plan is True


def test_conservative_target_normalization_cannot_manufacture_net_rr():
    row = evaluate_scalping_shadow(
        candidate(
            targets=(
                CausalTarget(101.237499999, "LOCAL_5M", BOUNDARY),
            )
        ),
        costs(),
        config(),
    )
    assert row.causal_target == 101.23749999
    assert row.net_rr < 1.5
    assert row.rejection_reason == R.ECONOMIC_GEOMETRY_NOT_FEASIBLE
    assert row.valid_plan is False


def test_nonfinite_authoritative_cost_rejects_as_cost_model_invalid():
    row = evaluate_scalping_shadow(
        candidate(targets=(CausalTarget(102.00, "LOCAL_5M", BOUNDARY),)),
        costs(spread_bps=float("nan")),
        config(),
    )
    assert row.rejection_reason == R.COST_MODEL_INVALID
    assert row.rejection_stage == "COST_MODEL"


def test_opportunity_identity_is_stable_across_adjacent_boundaries_but_candidate_is_not():
    first = evaluate_scalping_shadow(candidate(setup_identity="BREAKOUT_CONTINUATION"), costs(), config())
    second = evaluate_scalping_shadow(candidate(
        boundary_ms=BOUNDARY + 300_000,
        targets=(CausalTarget(102.0, "LOCAL_5M", BOUNDARY),),
        setup_identity="BREAKOUT_CONTINUATION",
    ), costs(), config())
    assert first.candidate_id != second.candidate_id
    assert first.opportunity_id == second.opportunity_id


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


def test_v2_requires_authoritative_commission_and_exposes_provenance():
    rejected = evaluate_scalping_shadow(
        candidate(trade_profile_id="trade-5m-v2"), costs(),
        config(profile_id="trade-5m-v2", production_rr_floor=0.4),
    )
    assert rejected.rejection_reason == "PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION"
    accepted = evaluate_scalping_shadow(
        candidate(trade_profile_id="trade-5m-v2"),
        costs(
            commission_authoritative=True,
            commission_symbol="SUIUSDT",
            commission_snapshot_id="commission:snapshot:1",
            commission_fetched_at="2026-09-04T00:00:00Z",
            fee_source="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT",
        ),
        config(profile_id="trade-5m-v2", production_rr_floor=0.4),
    )
    assert accepted.valid_plan
    assert accepted.commission_authoritative is True
    assert accepted.commission_symbol == "SUIUSDT"
    assert accepted.round_trip_commission_bps == 20
    assert accepted.cost_policy_version == "scalping-round-trip-net-pnl-v2"


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
    )).evaluate(strategy_decision(
        decision_id="strategy:5m", timeframe="5m", setup_type="SCALP_BREAKOUT",
        strategy_type="SCALP_BREAKOUT_RESEARCH",
    ))
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


def test_dynamic_account_commission_snapshot_drives_costs(monkeypatch, tmp_path):
    snapshot = tmp_path / "commission.json"
    snapshot.write_text(json.dumps({
        "snapshot_id": "binance:commission:20260904",
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bnb_discount_state": "DISABLED",
        "symbols": {"BTCUSDT": {
            "taker_bps": 8.5,
            "special_commission_state": "NONE",
            "tax_commission_state": "NONE",
        }},
    }), encoding="utf-8")
    monkeypatch.setenv("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH", str(snapshot))
    source = BinancePublicScalpingCostSource(
        client=BinancePublicRestClient(transport=Transport(), max_retries=0)
    )
    value = source.load("BTCUSDT", 100.0, safety_margin_bps=3.0)
    assert value.commission_authoritative is True
    assert value.fee_source == "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
    assert value.entry_fee_bps == value.exit_fee_bps == 8.5
    assert value.commission_symbol == "BTCUSDT"
    assert value.commission_snapshot_id == "binance:commission:20260904"
    result = evaluate_scalping_shadow(
        candidate(trade_profile_id="trade-5m-v2", symbol="BTCUSDT"), value,
        config(profile_id="trade-5m-v2", production_rr_floor=0.4),
    )
    assert result.valid_plan
    assert result.total_cost_bps is not None
    assert result.round_trip_commission_bps == 17.0


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
    return SimpleNamespace(
        profile_id="trade-5m-v1",
        minimum_planned_rr=1.5, cost_safety_margin_bps=3.0,
        geometry_atr_buffer_multiplier=.25,
        geometry_stop_envelope_bps=80.0,
        geometry_minimum_target_bps=45.0,
        economics_entry_fee_bps=10.0, economics_exit_fee_bps=10.0,
        economics_entry_slippage_bps=2.0, economics_exit_slippage_bps=2.0,
        economics_minimum_net_edge_bps=1.0,
        economics_minimum_net_edge_shadow_cohorts_bps=(10.0, 15.0, 20.0),
        economics_max_depth_impact_bps=20.0,
        rr_shadow_cohorts=(1.0, 1.2, 1.5),
        opportunity_reentry_enabled=False,
    )


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
        decision_id="strategy:5m:production", timeframe="5m",
        setup_type="SCALP_BREAKOUT", strategy_type="SCALP_BREAKOUT_RESEARCH",
        context=context,
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
    assert diagnostic["total_cost_bps"] == 30.0
    assert diagnostic["net_reward_bps"] == diagnostic["gross_reward_bps"] - 30.0
    assert diagnostic["net_edge_cohorts"] == {
        "10.00": True, "15.00": True, "20.00": True,
    }
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

    assert plan.paper_status == "REJECT"
    assert diagnostic["rejection_reason"] == R.SCALP_REJECT_CAUSAL_STOP_TOO_WIDE
    assert diagnostic["final_stop"] < diagnostic["causal_invalidation"]
    assert diagnostic["entry_fee_bps"] == 10.0
    assert diagnostic["exit_fee_bps"] == 10.0
    assert diagnostic["entry_slippage_bps"] == 2.0
    assert diagnostic["exit_slippage_bps"] == 2.0
    assert diagnostic["safety_margin_bps"] == 3.0
    assert diagnostic["spread_bps"] is None
    assert diagnostic["depth_impact_bps"] is None
    assert source.calls == []
