"""Setup detector consuming exactly one completed analysis snapshot."""

from __future__ import annotations

import time
from dataclasses import replace

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot, AnalysisSnapshotStatus
from app.engine_setup.setup_candidate import SetupCandidate, setup_candidate_id
from app.engine_setup.causal_planning_context import setup_causal_context
from app.engine_setup.setup_context import SetupContext
from app.engine_setup.setup_diagnostics import SetupDiagnostics, SetupSemanticBucket
from app.engine_setup.setup_invalidation import InvalidationReason
from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_rules import SetupRuleResult, evaluate_setup_rules
from app.engine_setup.setup_status import ConfirmationState, DirectionHint, SetupQuality, SetupStatus
from app.engine_setup.setup_type import SetupType
from app.engine_setup.setup_quality_diagnostics import diagnose_setup_quality


class SetupDetector:
    def __init__(self, runtime_parameters: object | None = None) -> None:
        self.runtime_parameters = runtime_parameters

    def detect(self, analysis_snapshot: AnalysisSnapshot) -> SetupCandidate:
        if not isinstance(analysis_snapshot, AnalysisSnapshot):
            raise TypeError("analysis_snapshot must be an AnalysisSnapshot")
        context = SetupContext.from_analysis_snapshot(analysis_snapshot)
        result = self._evaluate_snapshot(analysis_snapshot, context)
        return self._build(analysis_snapshot, context, result)

    def _evaluate_snapshot(self, snapshot: AnalysisSnapshot, context: SetupContext) -> SetupRuleResult:
        if bool(getattr(snapshot, "future_bars_used", False)):
            return _precondition_invalid(InvalidationReason.FUTURE_BARS_REJECTED)
        if snapshot.status == AnalysisSnapshotStatus.ERROR.value:
            return _precondition_invalid(InvalidationReason.ANALYSIS_ERROR)
        if snapshot.status != AnalysisSnapshotStatus.ANALYZED.value:
            return _no_setup(InvalidationReason.ANALYSIS_NOT_ANALYZED)
        if not snapshot.enough_data:
            return _no_setup(InvalidationReason.NOT_ENOUGH_DATA)
        if snapshot.degraded:
            return _precondition_invalid(InvalidationReason.ANALYSIS_NOT_ANALYZED)
        return evaluate_setup_rules(context)

    def _build(self, snapshot: AnalysisSnapshot, context: SetupContext,
               result: SetupRuleResult) -> SetupCandidate:
        missing = []
        for present, name in (
            (result.diagnostics.has_structural_trigger, "STRUCTURAL_TRIGGER"),
            (result.diagnostics.has_directional_context, "DIRECTIONAL_CONTEXT"),
            (result.diagnostics.has_level_context, "LIQUIDITY_OR_LEVEL_CONTEXT"),
        ):
            if not present:
                missing.append(name)

        def nested_value(value: object, key: str) -> object | None:
            if isinstance(value, dict):
                if key in value:
                    return value[key]
                for nested in value.values():
                    found = nested_value(nested, key)
                    if found is not None:
                        return found
            return None

        breakout = nested_value(context.analysis_context, "breakout_volume_ratio")
        atr = nested_value(context.analysis_context, "atr_value")
        result = SetupRuleResult(
            status=result.status,
            setup_type=result.setup_type,
            direction_hint=result.direction_hint,
            confirmation_state=result.confirmation_state,
            setup_quality=result.setup_quality,
            reason_codes=result.reason_codes,
            invalidation_reasons=result.invalidation_reasons,
            diagnostics=replace(
                result.diagnostics,
                distance_to_setup_condition=len(missing),
                missing_setup_conditions=missing,
                breakout_strength=(
                    float(breakout) if isinstance(breakout, (int, float)) else None
                ),
                pullback_quality=(
                    context.impulse_phase
                    if context.impulse_phase and "PULLBACK" in context.impulse_phase
                    else "NO_CAUSAL_PULLBACK_EVIDENCE"
                ),
                liquidity_presence=result.diagnostics.has_level_context,
                volatility_suitability=(
                    "OBSERVED_NOT_THRESHOLD_CLASSIFIED"
                    if isinstance(atr, (int, float)) and float(atr) > 0
                    else "UNKNOWN"
                ),
            ),
        )
        identity = setup_candidate_id(snapshot.symbol, snapshot.timeframe, snapshot.closed_until_ms,
                                      result.setup_type, result.status)
        quality = diagnose_setup_quality(
            status=result.status, setup_type=result.setup_type, direction_hint=result.direction_hint,
            confirmation_state=result.confirmation_state, diagnostics=result.diagnostics,
            reason_codes=result.reason_codes, invalidation_reasons=result.invalidation_reasons,
            source_analysis_entry_quality=context.entry_quality, source_confidence=context.confidence,
            source_regime=context.regime, source_impulse_phase=context.impulse_phase,
        )
        candidate_context = setup_causal_context(
            dict(context.analysis_context), direction=result.direction_hint,
            setup_type=result.setup_type,
        )
        if self.runtime_parameters is not None:
            candidate_context.update({
                "runtime_parameter_set_id": getattr(
                    self.runtime_parameters, "parameter_set_id"
                ),
                "setup_policy_id": getattr(self.runtime_parameters, "setup_policy_id"),
                "confirmation_window_candles": getattr(
                    self.runtime_parameters, "confirmation_window_candles"
                ),
                "minimum_planned_rr": getattr(
                    self.runtime_parameters, "minimum_planned_rr"
                ),
                "stop_policy_id": getattr(self.runtime_parameters, "stop_policy_id"),
                "target_policy_id": getattr(self.runtime_parameters, "target_policy_id"),
            })
        return SetupCandidate(
            setup_id=identity,
            symbol=snapshot.symbol.upper(),
            timeframe=snapshot.timeframe,
            closed_until_ms=snapshot.closed_until_ms,
            created_at_ms=time.time_ns() // 1_000_000,
            source_analysis_snapshot_id=snapshot.snapshot_id,
            source_regime=context.regime,
            source_confidence=context.confidence,
            source_action=context.action,
            source_impulse_phase=context.impulse_phase,
            source_entry_quality=context.entry_quality,
            status=result.status,
            setup_type=result.setup_type,
            direction_hint=result.direction_hint,
            confirmation_state=result.confirmation_state,
            setup_quality=quality.quality,
            quality_score=quality.quality_score,
            quality_diagnostics=quality,
            quality_reasons=quality.quality_reasons,
            quality_warnings=quality.quality_warnings,
            reason_codes=result.reason_codes,
            invalidation_reasons=result.invalidation_reasons,
            diagnostics=result.diagnostics,
            context=candidate_context,
        )


def _no_setup(reason: InvalidationReason) -> SetupRuleResult:
    reasons = [SetupReasonCode.NO_STRUCTURAL_SETUP.value]
    return SetupRuleResult(
        status="",
        setup_type=SetupType.NO_SETUP.value,
        direction_hint=DirectionHint.NONE.value,
        confirmation_state=ConfirmationState.NOT_APPLICABLE.value,
        setup_quality=SetupQuality.UNKNOWN.value,
        reason_codes=reasons,
        invalidation_reasons=[reason.value],
        diagnostics=SetupDiagnostics(
            has_invalidation_context=True,
            semantic_bucket=SetupSemanticBucket.NO_STRUCTURAL_SETUP.value,
            diagnostic_reasons=reasons,
        ),
    )


def _precondition_invalid(reason: InvalidationReason) -> SetupRuleResult:
    reasons = [SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA.value]
    return SetupRuleResult(
        status="",
        setup_type=SetupType.NO_SETUP.value,
        direction_hint=DirectionHint.NONE.value,
        confirmation_state=ConfirmationState.REJECTED_BY_ANALYSIS.value,
        setup_quality=SetupQuality.INVALID.value,
        reason_codes=reasons,
        invalidation_reasons=[reason.value],
        diagnostics=SetupDiagnostics(
            has_invalidation_context=True,
            semantic_bucket=SetupSemanticBucket.INVALIDATED_STRUCTURE.value,
            diagnostic_reasons=reasons,
        ),
    )
