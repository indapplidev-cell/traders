import pytest

from app.engine_strategy.strategy_filter import StrategyFilter


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


def test_conflicting_context_reject_keeps_score_and_penalty_decomposition(candidate_factory):
    candidate = candidate_factory(context={"has_conflict": True})
    decision = StrategyFilter().evaluate(candidate)
    assert decision.rejection_reasons == ["STRATEGY_REJECT_CONFLICTING_CONTEXT"]
    assert decision.strategy_score is not None
    assert decision.strategy_final_score == decision.strategy_score
    assert decision.strategy_raw_score is not None
    assert decision.strategy_penalty_total is not None
