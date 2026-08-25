"""Builds a safe StrategyDecision from one SetupCandidate."""

from __future__ import annotations

import time

from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_strategy.strategy_config import StrategyConfig
from app.engine_strategy.strategy_context import StrategyContext
from app.engine_strategy.lineage_identity import BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION
from app.engine_strategy.strategy_decision import (
    StrategyDecision,
    canonical_strategy_decision_identity,
    strategy_decision_id,
)
from app.engine_strategy.strategy_reason_codes import StrategyReasonCode
from app.engine_strategy.strategy_rules import (
    evaluate_strategy_rules,
    strategy_score_diagnostics,
    strategy_shadow_threshold_cohorts,
)
from app.engine_strategy.strategy_status import StrategyStatus


class StrategyFilter:
    def __init__(self, config: StrategyConfig | None = None,
                 runtime_parameters: object | None = None) -> None:
        self.config = config or StrategyConfig()
        self.runtime_parameters = runtime_parameters

    def evaluate(self, setup_candidate: SetupCandidate) -> StrategyDecision:
        if not isinstance(setup_candidate, SetupCandidate):
            raise TypeError("setup_candidate must be a SetupCandidate")
        context = StrategyContext.from_setup_candidate(setup_candidate)
        result = evaluate_strategy_rules(context, self.config)
        score_diagnostics = strategy_score_diagnostics(context, self.config)
        allow = result.status == StrategyStatus.ALLOW_RESEARCH_TRADE_PLAN.value
        reasons = list(result.reasons)
        reasons.extend([
            StrategyReasonCode.STRATEGY_NO_FUTURE_BARS_USED.value,
            StrategyReasonCode.STRATEGY_NOT_EXECUTABLE.value,
        ])
        if allow:
            reasons.append(StrategyReasonCode.STRATEGY_REQUIRES_RISK_REVIEW.value)
        return StrategyDecision(
            decision_id=strategy_decision_id(
                setup_candidate.symbol, setup_candidate.timeframe,
                setup_candidate.closed_until_ms, setup_candidate.setup_id),
            created_at_ms=time.time_ns() // 1_000_000,
            source_setup_id=setup_candidate.setup_id,
            source_analysis_snapshot_id=setup_candidate.source_analysis_snapshot_id,
            symbol=setup_candidate.symbol, timeframe=setup_candidate.timeframe,
            closed_until_ms=setup_candidate.closed_until_ms,
            decision_status=result.status, strategy_type=result.strategy_type,
            direction_hint=setup_candidate.direction_hint,
            setup_status=setup_candidate.status, setup_type=setup_candidate.setup_type,
            setup_quality=setup_candidate.setup_quality,
            setup_quality_score=setup_candidate.quality_score,
            strategy_score=result.score, strategy_quality=result.quality,
            strategy_quality_threshold=score_diagnostics["strategy_quality_threshold"],
            component_scores=score_diagnostics["component_scores"],
            strategy_raw_score=score_diagnostics["strategy_raw_score"],
            strategy_penalty_total=score_diagnostics["strategy_penalty_total"],
            strategy_final_score=score_diagnostics["strategy_final_score"],
            strategy_margin_to_threshold=score_diagnostics["strategy_margin_to_threshold"],
            shadow_quality_cohorts=(
                strategy_shadow_threshold_cohorts(result.score)
                if getattr(self.runtime_parameters, "profile_id", None) == "trade-5m-v1"
                else {}
            ),
            decision_reasons=reasons, decision_warnings=result.warnings,
            rejection_reasons=result.rejection_reasons, wait_reasons=result.wait_reasons,
            required_next_layer="engine_risk" if allow else None,
            requires_risk_review=allow,
            context={
                **context.to_dict(),
                **({
                    "runtime_parameter_set_id": getattr(
                        self.runtime_parameters, "parameter_set_id"
                    ),
                    "strategy_policy_id": getattr(
                        self.runtime_parameters, "strategy_policy_id"
                    ),
                } if self.runtime_parameters is not None else {}),
                "strategy_type": result.strategy_type,
                "direction_hint": setup_candidate.direction_hint,
                "canonical_strategy_decision_identity": canonical_strategy_decision_identity(
                    setup_candidate.symbol,
                    setup_candidate.timeframe,
                    setup_candidate.closed_until_ms,
                    setup_candidate.setup_id,
                ),
                "bounded_identity_algorithm_version":
                    BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION,
            },
        )
