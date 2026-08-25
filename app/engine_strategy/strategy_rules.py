"""Pure rules for setup-to-strategy routing without downstream actions."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine_strategy.strategy_config import StrategyConfig
from app.engine_strategy.strategy_context import StrategyContext
from app.engine_strategy.strategy_reason_codes import StrategyReasonCode as R
from app.engine_strategy.strategy_status import StrategyQuality, StrategyStatus
from app.engine_strategy.strategy_type import SETUP_TO_STRATEGY_TYPE, StrategyType


@dataclass(frozen=True, slots=True)
class RuleResult:
    status: str
    strategy_type: str = StrategyType.NO_STRATEGY.value
    quality: str = StrategyQuality.UNKNOWN.value
    score: float | None = None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    wait_reasons: list[str] = field(default_factory=list)


def _result(status: str, *, strategy_type: str = StrategyType.NO_STRATEGY.value,
            quality: str, score: float | None = None, reason: str,
            warnings: tuple[str, ...] = ()) -> RuleResult:
    rejected = [reason] if status == StrategyStatus.REJECT.value else []
    waiting = [reason] if status == StrategyStatus.WAIT.value else []
    return RuleResult(status, strategy_type, quality, score, [reason], list(warnings), rejected, waiting)


def diagnostic_strategy_score(context: StrategyContext) -> float | None:
    if context.setup_quality in {"UNKNOWN", "INVALID"}:
        return None if context.setup_quality == "UNKNOWN" else 0.0
    score = context.quality_score
    if score is None:
        score = {"GOOD": 85.0, "ACCEPTABLE": 70.0, "WEAK": 50.0, "POOR": 30.0}[context.setup_quality]
    score = float(score)
    if context.analysis_confidence is not None:
        # A small contemporaneous confidence adjustment cannot promote the setup tier.
        score += (max(0.0, min(1.0, context.analysis_confidence)) - 0.5) * 4.0
    caps = {"GOOD": (80.0, 100.0), "ACCEPTABLE": (65.0, 79.999),
            "WEAK": (45.0, 64.999), "POOR": (0.0, 44.999)}
    low, high = caps[context.setup_quality]
    return round(max(low, min(high, score)), 3)


def strategy_score_diagnostics(
    context: StrategyContext, config: StrategyConfig,
) -> dict[str, object]:
    """Explain the existing score without changing the strategy decision."""
    threshold_by_quality = {"GOOD": 80.0, "ACCEPTABLE": 65.0, "WEAK": 45.0}
    threshold = threshold_by_quality[config.minimum_allowed_quality]
    positive = (context.structural_score, context.confirmation_score, context.context_score)
    raw_score = (
        round(sum(float(value) for value in positive), 3)
        if any(value is not None for value in positive)
        else (float(context.quality_score) if context.quality_score is not None else None)
    )
    penalty_total = round(sum(float(value or 0.0) for value in (
        context.conflict_penalty, context.invalidation_penalty
    )), 3)
    final_score = diagnostic_strategy_score(context)
    return {
        "strategy_quality_threshold": threshold,
        "component_scores": {
            "structure": context.structural_score,
            "candle_confirmation": context.confirmation_score,
            "context_alignment": context.context_score,
        },
        "strategy_raw_score": raw_score,
        "strategy_penalty_total": penalty_total,
        "strategy_final_score": final_score,
        "strategy_margin_to_threshold": (
            None if final_score is None else round(final_score - threshold, 3)
        ),
    }


def evaluate_strategy_rules(context: StrategyContext, config: StrategyConfig) -> RuleResult:
    status = context.setup_status
    if status == "NO_SETUP":
        return _result(StrategyStatus.NO_DECISION.value, quality=StrategyQuality.UNKNOWN.value,
                       reason=R.STRATEGY_NO_DECISION_NO_SETUP.value)
    if status == "SETUP_INVALID":
        return _result(StrategyStatus.REJECT.value, quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_SETUP_INVALID.value)
    if status == "WAIT_FOR_CONFIRMATION":
        return _result(StrategyStatus.WAIT.value, quality=StrategyQuality.WAITING.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_WAIT_FOR_CONFIRMATION.value)
    if status == "ERROR":
        return _result(StrategyStatus.ERROR.value, quality=StrategyQuality.ERROR.value,
                       reason=R.STRATEGY_ERROR_PROCESSING_FAILED.value)

    strategy_type = SETUP_TO_STRATEGY_TYPE.get(context.setup_type, StrategyType.NO_STRATEGY.value)
    severe_warning = any("SEVERE" in value.upper() or "HARD_CONFLICT" in value.upper()
                         for value in context.quality_warnings)
    if ((config.reject_on_future_bars and context.source_future_bars_used)
            or (config.reject_if_source_is_trade_signal and context.source_is_trade_signal)
            or context.has_hard_invalidation):
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_HARD_INVALIDATION.value,
                       warnings=context.quality_warnings)
    if ((config.reject_on_invalidation_reasons and context.invalidation_reasons)
            or context.has_conflict or severe_warning):
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_CONFLICTING_CONTEXT.value,
                       warnings=context.quality_warnings)
    if context.confirmation_state == "AWAITING_CONFIRMATION":
        return _result(StrategyStatus.WAIT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.WAITING.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_WAIT_FOR_CONFIRMATION.value)
    if context.confirmation_state in {"INVALIDATED_BY_CONTEXT", "REJECTED_BY_ANALYSIS"}:
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_CONFLICTING_CONTEXT.value)
    if context.confirmation_state == "NOT_APPLICABLE":
        return _result(StrategyStatus.NO_DECISION.value, quality=StrategyQuality.UNKNOWN.value,
                       reason=R.STRATEGY_REJECT_NO_SETUP.value)
    if config.require_confirmed_by_analysis and context.confirmation_state != "CONFIRMED_BY_ANALYSIS":
        return _result(StrategyStatus.WAIT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.WAITING.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_WAIT_FOR_CONFIRMATION.value)
    if config.require_directional_hint and context.direction_hint not in {"BULLISH", "BEARISH"}:
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_NEUTRAL_DIRECTION.value)
    if context.setup_type not in config.allowed_setup_types or strategy_type == StrategyType.NO_STRATEGY.value:
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       score=diagnostic_strategy_score(context),
                       reason=R.STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE.value)
    score = diagnostic_strategy_score(context)
    if context.setup_quality == "WEAK":
        if config.allow_weak_candidates and config.allow_weak_to_wait:
            return _result(StrategyStatus.WAIT.value, strategy_type=strategy_type,
                           quality=StrategyQuality.WEAK.value, score=score,
                           reason=R.STRATEGY_WAIT_WEAK_BUT_STRUCTURED.value)
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value, score=score,
                       reason=R.STRATEGY_REJECT_WEAK_QUALITY.value)
    if context.setup_quality in {"POOR", "INVALID"}:
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value, score=score,
                       reason=R.STRATEGY_REJECT_POOR_OR_INVALID_QUALITY.value)
    if context.setup_quality == "UNKNOWN":
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value,
                       reason=R.STRATEGY_REJECT_UNKNOWN_QUALITY.value)
    if not config.quality_meets_minimum(context.setup_quality):
        return _result(StrategyStatus.REJECT.value, strategy_type=strategy_type,
                       quality=StrategyQuality.REJECTED.value, score=score,
                       reason=R.STRATEGY_REJECT_POOR_OR_INVALID_QUALITY.value)
    reason = (R.STRATEGY_ALLOW_GOOD_SETUP.value if context.setup_quality == "GOOD"
              else R.STRATEGY_ALLOW_ACCEPTABLE_SETUP.value)
    return _result(StrategyStatus.ALLOW_RESEARCH_TRADE_PLAN.value,
                   strategy_type=strategy_type, quality=context.setup_quality,
                   score=score, reason=reason, warnings=context.quality_warnings)
