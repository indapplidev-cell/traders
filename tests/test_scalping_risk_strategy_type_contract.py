from dataclasses import replace

import pytest

from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_paper.scalping_shadow import ShadowCostInputs
from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_limits import ResearchRiskLimits
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_risk.strategy_type_contract import (
    SCALPING_RISK_STRATEGY_TYPES,
    TRADE_15M_RISK_STRATEGY_TYPES,
    risk_supports_strategy_type,
)
from app.engine_strategy.strategy_type import StrategyType
from tests.engine_risk_01_helpers import strategy_decision


def policy(profile_id: str, limits: ResearchRiskLimits | None = None) -> RiskPolicy:
    parameters = resolve_runtime_parameters(profile_id)
    return RiskPolicy(
        RiskConfig(
            policy_version=parameters.risk_shadow_policy_id,
            minimum_strategy_quality=parameters.risk_minimum_strategy_quality,
            minimum_strategy_score=parameters.risk_minimum_strategy_score,
        ),
        limits=limits,
        runtime_parameters=parameters,
    )


def admitted(strategy_type: str, *, setup_type: str = "SCALP_BREAKOUT"):
    return strategy_decision(
        timeframe="5m", setup_type=setup_type, strategy_type=strategy_type,
        strategy_score=82.0, strategy_quality="ACCEPTABLE",
    )


@pytest.mark.parametrize("strategy_type", sorted(SCALPING_RISK_STRATEGY_TYPES))
def test_every_known_scalping_type_passes_compatibility(strategy_type):
    decision = policy("trade-5m-v1").evaluate_shadow(admitted(strategy_type))
    assert decision.risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert "RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE" not in decision.rejection_reasons


def test_unknown_but_well_formed_strategy_enum_fails_closed():
    decision = policy("trade-5m-v1").evaluate_shadow(
        admitted("PULLBACK_CONTINUATION_RESEARCH")
    )
    assert decision.risk_status == "REJECT"
    assert decision.rejection_reasons == ["RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE"]


@pytest.mark.parametrize("strategy_type", ["SCALP_FUTURE_RESEARCH", "", None, 7])
def test_synthetic_unknown_or_invalid_machine_code_fails_contract(strategy_type):
    assert not risk_supports_strategy_type(
        "trade-5m-v1", "SCALPING", strategy_type
    )


def test_profile_and_trade_mode_are_both_authoritative():
    scalping_type = StrategyType.SCALP_BREAKOUT_RESEARCH.value
    legacy_type = StrategyType.BREAKOUT_CONTINUATION_RESEARCH.value
    assert risk_supports_strategy_type("trade-5m-v1", "SCALPING", scalping_type)
    assert not risk_supports_strategy_type("trade-5m-v1", "SCALPING", legacy_type)
    assert not risk_supports_strategy_type("trade-15m-v1", "TRADE_15M", scalping_type)
    assert not risk_supports_strategy_type("trade-5m-v1", "TRADE_15M", scalping_type)


def test_wrong_profile_type_combinations_are_rejected():
    scalping_on_15m = policy("trade-15m-v1").evaluate_shadow(
        strategy_decision(strategy_type="SCALP_BREAKOUT_RESEARCH")
    )
    legacy_on_5m = policy("trade-5m-v1").evaluate_shadow(
        admitted("BREAKOUT_CONTINUATION_RESEARCH")
    )
    assert scalping_on_15m.rejection_reasons == ["RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE"]
    assert legacy_on_5m.rejection_reasons == ["RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE"]


@pytest.mark.parametrize("strategy_type", sorted(TRADE_15M_RISK_STRATEGY_TYPES))
def test_15m_supported_types_keep_their_existing_semantics(strategy_type):
    implicit = RiskPolicy().evaluate_shadow(strategy_decision(strategy_type=strategy_type))
    explicit = policy("trade-15m-v1").evaluate_shadow(
        strategy_decision(strategy_type=strategy_type)
    )
    assert implicit.risk_status == explicit.risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert implicit.risk_level == explicit.risk_level
    assert implicit.risk_score == explicit.risk_score
    assert implicit.rejection_reasons == explicit.rejection_reasons == []


def test_preview_is_side_effect_free_and_authoritative_reservation_still_applies():
    limits = ResearchRiskLimits()
    source = admitted("SCALP_BREAKOUT_RESEARCH")
    risk = policy("trade-5m-v1", limits)
    preview = risk.evaluate_shadow(source)
    assert preview.risk_pre_approved
    assert limits.profile_attempts("trade-5m-v1", source.closed_until_ms) == 0
    authoritative = risk.evaluate(source)
    assert authoritative.risk_pre_approved
    assert limits.profile_attempts("trade-5m-v1", source.closed_until_ms) == 1


def test_numeric_and_quota_rejection_paths_remain_after_compatibility():
    low_score = policy("trade-5m-v1").evaluate_shadow(replace(
        admitted("SCALP_BREAKOUT_RESEARCH"), strategy_score=1.0
    ))
    assert low_score.rejection_reasons == ["RISK_REJECT_LOW_STRATEGY_SCORE"]

    restrictive = RiskConfig(
        max_research_preapprovals_per_symbol_per_day=1,
        max_research_preapprovals_total_per_day=1,
        max_research_preapprovals_per_direction_per_day=1,
    )
    parameters = resolve_runtime_parameters("trade-5m-v1")
    limits = ResearchRiskLimits()
    risk = RiskPolicy(restrictive, limits, parameters)
    assert risk.evaluate(admitted("SCALP_BREAKOUT_RESEARCH")).risk_pre_approved
    second = replace(admitted("SCALP_BREAKOUT_RESEARCH"), decision_id="strategy:second")
    rejected = risk.evaluate(second)
    assert rejected.rejection_reasons == ["RISK_REJECT_RESEARCH_LIMIT_EXCEEDED"]


def test_v2_production_compatibility_does_not_turn_research_frequency_into_risk():
    parameters = resolve_runtime_parameters("trade-5m-v2")
    limits = ResearchRiskLimits()
    risk = RiskPolicy(
        RiskConfig(
            policy_version=parameters.risk_shadow_policy_id,
            minimum_strategy_quality=parameters.risk_minimum_strategy_quality,
            minimum_strategy_score=parameters.risk_minimum_strategy_score,
            max_research_preapprovals_per_symbol_per_day=1,
            max_research_preapprovals_total_per_day=1,
            max_research_preapprovals_per_direction_per_day=1,
            enforce_research_preapproval_limits=False,
        ),
        limits,
        parameters,
    )

    for index in range(12):
        source = replace(
            admitted("SCALP_BREAKOUT_RESEARCH"),
            decision_id=f"strategy:v2:production:{index}",
        )
        decision = risk.evaluate(source)
        assert decision.risk_status == "RISK_PRE_APPROVED_RESEARCH"
        assert decision.rejection_reasons == []
        assert decision.risk_context["research_preapproval_limits_enforced"] is False

    assert limits.profile_attempts("trade-5m-v2", source.closed_until_ms) == 0


class DeterministicCostSource:
    def load(self, symbol, entry, *, safety_margin_bps):
        return ShadowCostInputs(
            spread_bps=1.0, depth_impact_bps=2.0,
            spread_source="ISOLATED_FIXTURE",
            depth_impact_source="ISOLATED_FIXTURE",
            spread_authoritative=True, depth_authoritative=True,
        )


def test_all_known_scalping_types_reach_geometry_cost_rr_then_authoritative_risk():
    parameters = resolve_runtime_parameters("trade-5m-v1")
    limits = ResearchRiskLimits()
    risk = policy("trade-5m-v1", limits)
    paper = ScalpingPaperRunner(
        runtime_parameters=parameters, cost_source=DeterministicCostSource()
    )
    setup_by_strategy = {
        value: value.removesuffix("_RESEARCH") for value in SCALPING_RISK_STRATEGY_TYPES
    }

    for index, strategy_type in enumerate(sorted(SCALPING_RISK_STRATEGY_TYPES)):
        source = replace(
            admitted(strategy_type, setup_type=setup_by_strategy[strategy_type]),
            decision_id=f"strategy:scalping-contract:{index}",
            context={
                "confirmation_close": 100.0,
                "causal_support_level": 99.70,
                "causal_invalidation_level": 99.70,
                "causal_target_level": 102.0,
                "causal_target_candidates": [{
                    "price": 102.0, "source_type": "LOCAL_5M",
                    "timeframe": "5m", "known_at_ms": 1_700_000_000_000,
                    "validated": True, "still_relevant": True,
                }],
                "atr_value": 0.10,
                "opportunity_id": f"opportunity:contract:{index}",
            },
        )
        preview = risk.evaluate_shadow(source)
        assert preview.risk_pre_approved
        assert limits.profile_attempts("trade-5m-v1", source.closed_until_ms) == index
        plan = paper.process_risk_decision(preview)
        diagnostic = plan.paper_context["scalping_geometry_diagnostics"]
        assert diagnostic["valid_plan"] is True
        assert diagnostic["economic_gate_pass"] is True
        assert diagnostic["rr_cohorts_net"]["1.50"] is True
        authoritative = risk.evaluate(source)
        assert authoritative.risk_pre_approved
        assert limits.profile_attempts("trade-5m-v1", source.closed_until_ms) == index + 1
