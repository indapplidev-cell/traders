import pytest
from types import SimpleNamespace

from app.engine_strategy.strategy_filter import StrategyFilter
from app.engine_strategy.strategy_config import StrategyConfig
from app.engine_setup.setup_quality_diagnostics import SetupQualityDiagnostics
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters


def test_weak_quality_reject_has_quantitative_threshold_margin(candidate_factory):
    decision = StrategyFilter().evaluate(candidate_factory(
        setup_quality="WEAK", quality_score=60.0,
    ))
    assert decision.rejection_reasons == ["STRATEGY_REJECT_WEAK_QUALITY"]
    assert decision.strategy_quality_threshold == 65.0
    assert decision.strategy_final_score == decision.strategy_score
    assert decision.strategy_margin_to_threshold == pytest.approx(
        decision.strategy_score - 65.0
    )
    assert set(decision.component_scores) == {
        "structure", "candle_confirmation", "context_alignment",
    }
    assert decision.raw_component_values == decision.component_scores
    assert set(decision.normalized_component_scores) == set(decision.component_scores)
    assert set(decision.negative_penalties) == {"conflict", "invalidation"}


def test_conflicting_context_reject_keeps_score_and_penalty_decomposition(candidate_factory):
    candidate = candidate_factory(context={"has_conflict": True})
    decision = StrategyFilter().evaluate(candidate)
    assert decision.rejection_reasons == ["STRATEGY_REJECT_CONFLICTING_CONTEXT"]
    assert decision.strategy_score is not None
    assert decision.strategy_final_score == decision.strategy_score
    assert decision.strategy_raw_score is not None
    assert decision.strategy_penalty_total is not None
    assert decision.conflict_trace
    assert decision.conflict_trace[0]["valid_at_decision_boundary"] is True


def test_bounded_5m_shadow_threshold_cohorts_are_diagnostic_only(candidate_factory):
    decision = StrategyFilter(runtime_parameters=SimpleNamespace(
        profile_id="trade-5m-v1", parameter_set_id="5m", strategy_policy_id="strategy",
        strategy_not_evaluated_handling="LEGACY_WEAK_CAP",
        strategy_shadow_thresholds=(55.0, 60.0, 65.0),
    )).evaluate(candidate_factory(setup_quality="WEAK", quality_score=64.6))
    assert decision.decision_status == "REJECT"
    assert decision.shadow_quality_cohorts == {
        "production_threshold": 65.0,
        "threshold_55": True,
        "threshold_60": True,
        "threshold_65": False,
        "diagnostic_only": True,
    }


def test_scalping_not_evaluated_is_scored_neutrally_and_components_are_lossless(
    candidate_factory,
):
    parameters = resolve_runtime_parameters("trade-5m-v1")
    diagnostics = SetupQualityDiagnostics(
        quality="WEAK", quality_score=64.999,
        structural_score=35, confirmation_score=30, context_score=30,
        conflict_penalty=0, invalidation_penalty=0,
        quality_reasons=["QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY"],
        capped_by_analysis_entry_quality=True,
        source_analysis_entry_quality="NOT_EVALUATED",
    )
    candidate = candidate_factory(
        timeframe="5m", setup_type="SCALP_BREAKOUT",
        setup_quality="WEAK", quality_score=64.999,
        quality_diagnostics=diagnostics,
        context={"scalping": {"entry_evidence_strength": "NOT_EVALUATED"}},
    )
    decision = StrategyFilter(
        StrategyConfig(allowed_setup_types=frozenset(parameters.strategy_allowed_setup_types)),
        parameters,
    ).evaluate(candidate)
    assert decision.decision_status == "ALLOW_RESEARCH_TRADE_PLAN"
    assert decision.context["source_setup_quality"] == "WEAK"
    assert decision.context["source_quality_reasons"] == [
        "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY"
    ]
    assert decision.setup_quality == "GOOD"
    assert decision.strategy_cap_applied is False
    assert decision.context["analysis_entry_evidence_strength"] == "NOT_EVALUATED"
    decomposition = decision.context["scalping_score_decomposition"]
    assert decomposition["target_weights"] == {
        "structure": 25.0, "context": 15.0, "momentum": 15.0,
        "volume": 15.0, "entry_quality": 10.0, "liquidity": 10.0,
        "confirmation": 10.0,
    }
    assert decomposition["mapped_total"] == decomposition["source_total"] == 95.0
    assert decision.shadow_quality_cohorts["threshold_65"] is True


@pytest.mark.parametrize(
    ("strength", "expected_reason"),
    [
        ("UNKNOWN", "STRATEGY_REJECT_UNKNOWN_QUALITY"),
        ("CONFLICTING", "STRATEGY_REJECT_CONFLICTING_CONTEXT"),
        ("INVALID", "STRATEGY_REJECT_HARD_INVALIDATION"),
        ("WEAK", "STRATEGY_REJECT_WEAK_QUALITY"),
    ],
)
def test_scalping_analysis_semantics_are_not_collapsed_to_weak(
    candidate_factory, strength, expected_reason,
):
    parameters = resolve_runtime_parameters("trade-5m-v1")
    candidate = candidate_factory(
        timeframe="5m", setup_type="SCALP_BREAKOUT",
        setup_quality="WEAK", quality_score=60,
        context={"scalping": {"entry_evidence_strength": strength}},
    )
    decision = StrategyFilter(
        StrategyConfig(allowed_setup_types=frozenset(parameters.strategy_allowed_setup_types)),
        parameters,
    ).evaluate(candidate)
    assert decision.rejection_reasons == [expected_reason]
    assert decision.context["analysis_entry_evidence_strength"] == strength


def test_scalping_v2_unknown_no_setup_preserves_final_score_contract(candidate_factory):
    parameters = resolve_runtime_parameters("trade-5m-v2")
    candidate = candidate_factory(
        timeframe="5m",
        status="NO_SETUP",
        setup_type="NO_SETUP",
        setup_quality="UNKNOWN",
        quality_score=None,
        context={"scalping": {"entry_evidence_strength": "UNKNOWN"}},
    )

    decision = StrategyFilter(
        StrategyConfig(allowed_setup_types=frozenset(parameters.strategy_allowed_setup_types)),
        parameters,
    ).evaluate(candidate)

    assert decision.decision_status == "NO_DECISION"
    assert decision.strategy_score == decision.strategy_final_score
    assert "STRATEGY_ERROR_PROCESSING_FAILED" not in decision.decision_reasons
