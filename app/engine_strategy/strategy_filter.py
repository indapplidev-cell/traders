"""Builds a safe StrategyDecision from one SetupCandidate."""

from __future__ import annotations

import time
from dataclasses import replace

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
    scalping_strategy_score_decomposition,
    strategy_gate_diagnostics,
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
        source_setup_quality = context.setup_quality
        source_quality_reasons = context.quality_reasons
        if getattr(self.runtime_parameters, "profile_id", None) == "trade-5m-v1":
            if context.analysis_entry_evidence_strength == "UNKNOWN":
                context = replace(context, setup_quality="UNKNOWN", quality_score=None)
            elif context.analysis_entry_evidence_strength == "CONFLICTING":
                context = replace(context, has_conflict=True)
            elif context.analysis_entry_evidence_strength == "INVALID":
                context = replace(
                    context, setup_quality="INVALID", quality_score=0.0,
                    has_hard_invalidation=True,
                )
        if (
            getattr(self.runtime_parameters, "profile_id", None) == "trade-5m-v1"
            and getattr(self.runtime_parameters, "strategy_not_evaluated_handling", None)
            == "SCORE_FROM_EVALUATED_COMPONENTS"
            and context.analysis_entry_evidence_strength == "NOT_EVALUATED"
        ):
            raw = sum(float(value or 0.0) for value in (
                context.structural_score, context.confirmation_score, context.context_score,
            )) - float(context.conflict_penalty or 0.0) - float(context.invalidation_penalty or 0.0)
            from app.engine_setup.setup_quality_diagnostics import quality_from_score
            context = replace(
                context,
                setup_quality=quality_from_score(raw),
                quality_score=max(0.0, min(100.0, raw)),
                quality_reasons=tuple(
                    reason for reason in context.quality_reasons
                    if reason != "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY"
                ),
            )
        result = evaluate_strategy_rules(context, self.config)
        score_diagnostics = strategy_score_diagnostics(context, self.config)
        gate_diagnostics = strategy_gate_diagnostics(result)
        conflict_trace = []
        for warning in context.quality_warnings:
            conflict_trace.append({
                "conflict_component": warning,
                "conflict_severity": (
                    "HARD" if context.has_hard_invalidation else "CONFLICT"
                ),
                "source_timeframe": setup_candidate.timeframe,
                "source": (
                    "analysis_confidence" if warning == "LOW_CONFIDENCE"
                    else "setup_quality_diagnostics"
                ),
                "valid_at_decision_boundary": not context.source_future_bars_used,
            })
        if context.has_conflict and not conflict_trace:
            conflict_trace.append({
                "conflict_component": "UNSPECIFIED_EXISTING_CONTEXT_CONFLICT",
                "conflict_severity": "CONFLICT",
                "source_timeframe": setup_candidate.timeframe,
                "source": "setup_context",
                "valid_at_decision_boundary": not context.source_future_bars_used,
            })
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
            setup_quality=context.setup_quality,
            setup_quality_score=context.quality_score,
            strategy_score=result.score, strategy_quality=result.quality,
            strategy_quality_threshold=score_diagnostics["strategy_quality_threshold"],
            component_scores=score_diagnostics["component_scores"],
            raw_component_values=score_diagnostics["raw_component_values"],
            normalized_component_scores=score_diagnostics["normalized_component_scores"],
            positive_contributions=score_diagnostics["positive_contributions"],
            negative_penalties=score_diagnostics["negative_penalties"],
            conflict_trace=conflict_trace,
            strategy_raw_score=score_diagnostics["strategy_raw_score"],
            strategy_penalty_total=score_diagnostics["strategy_penalty_total"],
            strategy_penalties=score_diagnostics["strategy_penalties"],
            strategy_pre_cap_score=score_diagnostics["strategy_pre_cap_score"],
            strategy_cap_applied=score_diagnostics["strategy_cap_applied"],
            strategy_cap_type=score_diagnostics["strategy_cap_type"],
            strategy_cap_reason=score_diagnostics["strategy_cap_reason"],
            strategy_cap_value=score_diagnostics["strategy_cap_value"],
            strategy_post_cap_score=score_diagnostics["strategy_post_cap_score"],
            strategy_caps=score_diagnostics["strategy_caps"],
            strategy_gate_results=gate_diagnostics["strategy_gate_results"],
            strategy_failed_gate=gate_diagnostics["strategy_failed_gate"],
            strategy_failed_gate_reason=gate_diagnostics["strategy_failed_gate_reason"],
            strategy_final_score=score_diagnostics["strategy_final_score"],
            strategy_margin_to_threshold=score_diagnostics["strategy_margin_to_threshold"],
            shadow_quality_cohorts=(
                strategy_shadow_threshold_cohorts(
                    result.score,
                    tuple(self.runtime_parameters.strategy_shadow_thresholds),
                )
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
                "source_setup_quality": source_setup_quality,
                "source_quality_reasons": list(source_quality_reasons),
                "scalping_score_decomposition": (
                    scalping_strategy_score_decomposition(context)
                    if getattr(self.runtime_parameters, "profile_id", None) == "trade-5m-v1"
                    else None
                ),
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
