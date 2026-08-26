"""Pure rules for setup-to-strategy routing without downstream actions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.engine_strategy.strategy_config import StrategyConfig
from app.engine_strategy.strategy_context import StrategyContext
from app.engine_strategy.strategy_reason_codes import StrategyReasonCode as R
from app.engine_strategy.strategy_status import StrategyQuality, StrategyStatus
from app.engine_strategy.strategy_type import SETUP_TO_STRATEGY_TYPE, StrategyType
from app.engine_setup.setup_quality_diagnostics import quality_from_score


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
    penalty_values = {
        "conflict": context.conflict_penalty,
        "invalidation": context.invalidation_penalty,
    }
    penalty_total = round(sum(float(value or 0.0) for value in penalty_values.values()), 3)
    final_score = diagnostic_strategy_score(context)
    confidence_adjustment = (
        None if context.analysis_confidence is None
        else round((max(0.0, min(1.0, context.analysis_confidence)) - 0.5) * 4.0, 3)
    )
    setup_pre_cap_score = (
        None if raw_score is None else round(max(0.0, min(100.0, raw_score - penalty_total)), 3)
    )
    immediate_pre_cap_score = (
        None if context.quality_score is None else round(
            float(context.quality_score) + float(confidence_adjustment or 0.0), 3
        )
    )
    tier_caps = {
        "GOOD": 100.0, "ACCEPTABLE": 79.999, "WEAK": 64.999,
        "POOR": 44.999, "INVALID": 0.0, "UNKNOWN": 0.0,
    }
    caps: list[dict[str, object]] = []
    if "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY" in context.quality_reasons:
        caps.append({
            "cap_type": "ANALYSIS_ENTRY_QUALITY_TIER_CAP",
            "cap_reason": "QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY",
            "input_score": setup_pre_cap_score,
            "cap_value": tier_caps[context.setup_quality],
            "output_score": context.quality_score,
            "applied": True,
        })
    if (
        immediate_pre_cap_score is not None and final_score is not None
        and immediate_pre_cap_score != final_score
    ):
        caps.append({
            "cap_type": "SETUP_QUALITY_TIER_CLAMP",
            "cap_reason": f"SETUP_QUALITY_{context.setup_quality}_UPPER_BOUND",
            "input_score": immediate_pre_cap_score,
            "cap_value": tier_caps[context.setup_quality],
            "output_score": final_score,
            "applied": True,
        })
    primary_cap = caps[0] if caps else {}
    maximums = {"structure": 35.0, "candle_confirmation": 30.0, "context_alignment": 35.0}
    components = {
        "structure": context.structural_score,
        "candle_confirmation": context.confirmation_score,
        "context_alignment": context.context_score,
    }
    normalized = {
        name: (None if value is None else round(float(value) / maximums[name] * 100.0, 3))
        for name, value in components.items()
    }
    return {
        "strategy_quality_threshold": threshold,
        "component_scores": components,
        "raw_component_values": components,
        "normalized_component_scores": normalized,
        "positive_contributions": {
            **components,
            "analysis_confidence_adjustment": confidence_adjustment,
        },
        "negative_penalties": {
            **penalty_values,
        },
        "strategy_raw_score": raw_score,
        "strategy_penalty_total": penalty_total,
        "strategy_penalties": [
            {"penalty_type": name.upper(), "value": float(value), "applied": bool(value)}
            for name, value in penalty_values.items() if value is not None
        ],
        "strategy_setup_pre_cap_score": setup_pre_cap_score,
        "strategy_pre_cap_score": immediate_pre_cap_score,
        "strategy_cap_applied": bool(caps),
        "strategy_cap_type": primary_cap.get("cap_type"),
        "strategy_cap_reason": primary_cap.get("cap_reason"),
        "strategy_cap_value": primary_cap.get("cap_value"),
        "strategy_post_cap_score": final_score,
        "strategy_caps": caps,
        "strategy_confidence_adjustment": confidence_adjustment,
        "strategy_final_score": final_score,
        "strategy_margin_to_threshold": (
            None if final_score is None else round(final_score - threshold, 3)
        ),
    }


_TERMINAL_GATE_BY_REASON = {
    R.STRATEGY_NO_DECISION_NO_SETUP.value: "SOURCE_SETUP_STATUS",
    R.STRATEGY_REJECT_SETUP_INVALID.value: "SOURCE_SETUP_STATUS",
    R.STRATEGY_WAIT_FOR_CONFIRMATION.value: "CONFIRMATION_GATE",
    R.STRATEGY_ERROR_PROCESSING_FAILED.value: "SOURCE_SETUP_STATUS",
    R.STRATEGY_REJECT_HARD_INVALIDATION.value: "HARD_INVALIDATION_GATE",
    R.STRATEGY_REJECT_CONFLICTING_CONTEXT.value: "CONFLICT_CONTEXT_GATE",
    R.STRATEGY_REJECT_NO_SETUP.value: "CONFIRMATION_GATE",
    R.STRATEGY_REJECT_NEUTRAL_DIRECTION.value: "DIRECTION_GATE",
    R.STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE.value: "SETUP_TYPE_GATE",
    R.STRATEGY_REJECT_WEAK_QUALITY.value: "WEAK_QUALITY_GATE",
    R.STRATEGY_WAIT_WEAK_BUT_STRUCTURED.value: "WEAK_QUALITY_GATE",
    R.STRATEGY_REJECT_POOR_OR_INVALID_QUALITY.value: "MINIMUM_QUALITY_GATE",
    R.STRATEGY_REJECT_UNKNOWN_QUALITY.value: "MINIMUM_QUALITY_GATE",
    R.STRATEGY_ALLOW_GOOD_SETUP.value: "ADMISSION",
    R.STRATEGY_ALLOW_ACCEPTABLE_SETUP.value: "ADMISSION",
}


def strategy_gate_diagnostics(result: RuleResult) -> dict[str, object]:
    """Expose the actual terminal rule separately from score transforms."""
    reason = result.reasons[0] if result.reasons else None
    terminal = _TERMINAL_GATE_BY_REASON.get(reason, "UNKNOWN_TERMINAL_GATE")
    rejected = result.status == StrategyStatus.REJECT.value
    return {
        "strategy_gate_results": [{
            "gate": terminal,
            "outcome": "FAIL" if rejected else result.status,
            "terminal": True,
            "reason": reason,
        }],
        "strategy_failed_gate": terminal if rejected else None,
        "strategy_failed_gate_reason": reason if rejected else None,
    }


def strategy_shadow_threshold_cohorts(final_score: float | None) -> dict[str, bool | float]:
    """Bounded diagnostic-only 5m cohorts; never consulted by decision rules."""
    if final_score is None:
        return {}
    return {
        "production_threshold": 65.0,
        "delta_minus_0_10": final_score >= 64.90,
        "delta_minus_0_25": final_score >= 64.75,
        "delta_minus_0_50": final_score >= 64.50,
        "delta_minus_1_00": final_score >= 64.00,
        "diagnostic_only": True,
    }


def strategy_shadow_variants(
    context: StrategyContext, config: StrategyConfig,
) -> dict[str, object]:
    """One-factor, diagnostic-only Strategy replay with no execution authority."""
    baseline = evaluate_strategy_rules(context, config)
    diagnostics = strategy_score_diagnostics(context, config)
    uncapped_score = diagnostics["strategy_setup_pre_cap_score"]
    uncapped_quality = quality_from_score(
        uncapped_score, hard_invalidation=context.has_hard_invalidation
    )
    no_cap_context = replace(
        context, setup_quality=uncapped_quality, quality_score=uncapped_score,
    )
    no_cap = evaluate_strategy_rules(no_cap_context, config)

    specific_context = context
    terminal_reason = baseline.reasons[0] if baseline.reasons else None
    if terminal_reason == R.STRATEGY_REJECT_CONFLICTING_CONTEXT.value:
        specific_context = replace(
            context, has_conflict=False, quality_warnings=(), invalidation_reasons=(),
        )
    no_specific_gate = evaluate_strategy_rules(specific_context, config)
    if terminal_reason == R.STRATEGY_REJECT_WEAK_QUALITY.value:
        # Skipping only the special weak branch still reaches the independent
        # minimum-quality rule; report that terminal result without promotion.
        no_specific_gate = _result(
            StrategyStatus.REJECT.value,
            strategy_type=SETUP_TO_STRATEGY_TYPE.get(
                context.setup_type, StrategyType.NO_STRATEGY.value
            ),
            quality=StrategyQuality.REJECTED.value,
            score=diagnostic_strategy_score(context),
            reason=R.STRATEGY_REJECT_POOR_OR_INVALID_QUALITY.value,
        )
    return {
        "SHADOW_BASELINE": baseline,
        "SHADOW_NO_CAP": no_cap,
        "SHADOW_NO_SPECIFIC_GATE": no_specific_gate,
        "SHADOW_RAW_SCORE_ONLY_DIAGNOSTIC": {
            "score": uncapped_score,
            "threshold": diagnostics["strategy_quality_threshold"],
            "would_pass_numeric_threshold": (
                uncapped_score is not None
                and uncapped_score >= diagnostics["strategy_quality_threshold"]
            ),
            "diagnostic_only": True,
        },
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
