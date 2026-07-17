"""Pure semantic classification rules for potential market situations."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine_setup.setup_context import SetupContext
from app.engine_setup.setup_diagnostics import (
    SetupDiagnostics,
    SetupSemanticBucket,
    status_for_semantic_bucket,
)
from app.engine_setup.setup_invalidation import (
    InvalidationReason,
    blocks_existing_setup,
    collect_invalidation_reasons,
)
from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_status import ConfirmationState, DirectionHint, SetupQuality
from app.engine_setup.setup_type import SetupType


@dataclass(frozen=True, slots=True)
class SetupRuleResult:
    status: str
    setup_type: str
    direction_hint: str
    confirmation_state: str
    setup_quality: str
    reason_codes: list[str]
    invalidation_reasons: list[str]
    diagnostics: SetupDiagnostics

    def __post_init__(self) -> None:
        # Status is a projection of semantic meaning, never an independent rule output.
        object.__setattr__(self, "status", status_for_semantic_bucket(
            self.diagnostics.semantic_bucket))


_FALSE_BREAKOUT = {
    "FAILED_BREAKOUT_RANGE_REENTRY",
    "RETURNED_INSIDE_CONFIRMED_RANGE",
    "DIRECTIONAL_BREAKOUT_INVALIDATED",
}
_EXHAUSTION = {
    "EXTENDED_MOVE_EXHAUSTION_RISK",
    "CLIMAX_VOLUME_WITHOUT_FOLLOW_THROUGH",
    "WICK_REJECTION_AFTER_EXTENSION",
}
_BREAKOUT_CONFIRMATION = {
    "BREAKOUT_HELD_WITH_FOLLOW_THROUGH",
    "BREAKOUT_FOLLOW_THROUGH_CONFIRMED",
    "DIRECTIONAL_BREAKOUT_CONFIRMED",
}
_CONTINUATION_TRIGGER = {
    "CONTROLLED_PULLBACK_CONTINUATION",
    "CONTROLLED_PULLBACK_CONFIRMED",
    "PULLBACK_STRUCTURE_HELD",
}
def evaluate_setup_rules(context: SetupContext) -> SetupRuleResult:
    tokens = set(context.reason_codes)
    phase = context.impulse_phase or ""
    flat = _flatten(context.analysis_context)
    invalidations = collect_invalidation_reasons(context)
    directional = context.regime in {"UP", "DOWN"}
    choppy = _is_choppy(tokens, flat)
    range_present = _has_range(tokens, flat, context.regime)

    late = InvalidationReason.LATE_CONFIRMATION_RISK.value in invalidations
    false_breakout = bool(tokens.intersection(_FALSE_BREAKOUT))
    exhaustion_phase = phase in {"IMPULSE_EXHAUSTION", "IMPULSE_EXHAUSTION_RISK"}
    exhaustion_evidence = exhaustion_phase or bool(tokens.intersection(_EXHAUSTION))
    exhaustion_structure = exhaustion_phase or (
        exhaustion_evidence and _has_rejection_or_level(tokens, flat)
    )
    continuation_trigger = directional and (
        bool(tokens.intersection(_CONTINUATION_TRIGGER))
        or phase in {"CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION"}
    )
    breakout_trigger = directional and (
        phase == "IMPULSE_EXTENSION"
        or any("BREAKOUT_REQUIRES_CONFIRMATION" in token for token in tokens)
    )
    breakout_confirmed = bool(tokens.intersection(_BREAKOUT_CONFIRMATION)) or _breakout_held(flat)

    if late and context.entry_quality in {"POOR", "INVALID"}:
        return _invalid(
            SetupType.LATE_ENTRY_REJECTED, context, invalidations,
            [SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
            direction=_direction_from_regime(context.regime),
            structural=True, level=_has_rejection_or_level(tokens, flat), late=True,
        )

    if false_breakout:
        direction = _false_breakout_direction(context, flat)
        if context.entry_quality == "INVALID":
            return _invalid(
                SetupType.FALSE_BREAKOUT_REVERSAL, context, invalidations,
                [SetupReasonCode.FALSE_BREAKOUT_EVIDENCE,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=direction, structural=True, level=True,
            )
        if _reversal_confirmed(tokens, flat) and _acceptable(context):
            return _candidate(
                SetupType.FALSE_BREAKOUT_REVERSAL, context,
                [SetupReasonCode.FALSE_BREAKOUT_EVIDENCE], invalidations,
                direction=direction, level=True,
            )
        return _wait(
            SetupType.FALSE_BREAKOUT_REVERSAL, context,
            [SetupReasonCode.FALSE_BREAKOUT_EVIDENCE,
             SetupReasonCode.WAITING_FOR_REVERSAL_CONFIRMATION], invalidations,
            direction=direction, level=True,
        )

    if exhaustion_structure:
        if context.entry_quality == "INVALID":
            return _invalid(
                SetupType.MOMENTUM_EXHAUSTION, context, invalidations,
                [SetupReasonCode.MOMENTUM_EXHAUSTION_EVIDENCE,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=_direction_from_regime(context.regime), structural=True,
                level=_has_rejection_or_level(tokens, flat),
            )
        return _wait(
            SetupType.MOMENTUM_EXHAUSTION, context,
            [SetupReasonCode.MOMENTUM_EXHAUSTION_EVIDENCE,
             SetupReasonCode.WAITING_FOR_REVERSAL_CONFIRMATION], invalidations,
            direction=_direction_from_regime(context.regime),
            level=_has_rejection_or_level(tokens, flat),
        )

    if phase == "POST_SPIKE_PULLBACK" and directional:
        return _invalid(
            SetupType.PULLBACK_CONTINUATION, context, invalidations,
            [SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
            direction=_direction_from_regime(context.regime), structural=True,
            level=_has_rejection_or_level(tokens, flat),
        )

    if _is_breakout_retest(tokens, flat):
        if _blocked(invalidations):
            return _invalid(
                SetupType.BREAKOUT_RETEST, context, invalidations,
                [SetupReasonCode.BREAKOUT_RETEST_EVIDENCE,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=_direction_from_regime(context.regime), structural=True, level=True,
            )
        return _candidate(
            SetupType.BREAKOUT_RETEST, context,
            [SetupReasonCode.BREAKOUT_RETEST_EVIDENCE], invalidations,
            direction=_direction_from_regime(context.regime), level=True,
        )

    if continuation_trigger:
        if context.entry_quality in {"POOR", "INVALID"}:
            return _no_setup(
                context,
                [SetupReasonCode.NO_STRUCTURAL_SETUP,
                 SetupReasonCode.WEAK_CONTEXT_FILTERED_TO_NO_SETUP],
                invalidations, directional=True,
                level=_has_rejection_or_level(tokens, flat), choppy=choppy,
            )
        if _blocked(invalidations):
            return _invalid(
                SetupType.PULLBACK_CONTINUATION, context, invalidations,
                [SetupReasonCode.ANALYSIS_SUPPORTS_PULLBACK_CONTINUATION,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=_direction_from_regime(context.regime), structural=True,
                level=_has_rejection_or_level(tokens, flat),
            )
        if breakout_confirmed or _confirmed(flat, tokens):
            return _candidate(
                SetupType.PULLBACK_CONTINUATION, context,
                [SetupReasonCode.ANALYSIS_SUPPORTS_PULLBACK_CONTINUATION], invalidations,
                direction=_direction_from_regime(context.regime),
                level=_has_rejection_or_level(tokens, flat),
            )
        return _wait(
            SetupType.PULLBACK_CONTINUATION, context,
            [SetupReasonCode.ANALYSIS_SUPPORTS_PULLBACK_CONTINUATION,
             SetupReasonCode.WAITING_FOR_BREAKOUT_HOLD], invalidations,
            direction=_direction_from_regime(context.regime),
            level=_has_rejection_or_level(tokens, flat),
        )

    if breakout_trigger:
        if _blocked(invalidations):
            return _invalid(
                SetupType.BREAKOUT_CONTINUATION, context, invalidations,
                [SetupReasonCode.ANALYSIS_CONFIRMS_BREAKOUT_CONTINUATION,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=_direction_from_regime(context.regime), structural=True,
                level=_has_rejection_or_level(tokens, flat),
            )
        if breakout_confirmed:
            return _candidate(
                SetupType.BREAKOUT_CONTINUATION, context,
                [SetupReasonCode.ANALYSIS_CONFIRMS_BREAKOUT_CONTINUATION], invalidations,
                direction=_direction_from_regime(context.regime),
                level=_has_rejection_or_level(tokens, flat),
            )
        return _wait(
            SetupType.TREND_CONTINUATION, context,
            [SetupReasonCode.WAITING_FOR_BREAKOUT_HOLD], invalidations,
            direction=_direction_from_regime(context.regime),
            level=_has_rejection_or_level(tokens, flat),
        )

    if context.regime in {"FLAT", "UNKNOWN"} and _range_rejection(flat, tokens):
        direction = _range_direction(flat)
        if context.entry_quality == "INVALID":
            return _invalid(
                SetupType.RANGE_REJECTION, context, invalidations,
                [SetupReasonCode.RANGE_REJECTION_EVIDENCE,
                 SetupReasonCode.INVALIDATED_EXISTING_SETUP_IDEA],
                direction=direction, structural=True, level=True,
            )
        if _confirmed(flat, tokens) and _acceptable(context):
            return _candidate(
                SetupType.RANGE_REJECTION, context,
                [SetupReasonCode.RANGE_REJECTION_EVIDENCE], invalidations,
                direction=direction, level=True,
            )
        return _wait(
            SetupType.RANGE_REJECTION, context,
            [SetupReasonCode.RANGE_REJECTION_EVIDENCE,
             SetupReasonCode.WAITING_FOR_REJECTION_FOLLOW_THROUGH], invalidations,
            direction=direction, level=True,
        )

    if _reversal_evidence(tokens, flat):
        return _wait(
            SetupType.REVERSAL_START, context,
            [SetupReasonCode.REVERSAL_REQUIRES_CONFIRMATION,
             SetupReasonCode.WAITING_FOR_REVERSAL_CONFIRMATION], invalidations,
            direction=_reversal_direction(flat), level=_has_rejection_or_level(tokens, flat),
        )

    reasons = [SetupReasonCode.NO_STRUCTURAL_SETUP]
    if range_present and not _has_edge_interaction(flat, tokens):
        reasons.append(SetupReasonCode.RANGE_PRESENT_BUT_NO_EDGE_TOUCH)
        reasons.append(SetupReasonCode.NO_LEVEL_INTERACTION)
    elif exhaustion_evidence and not _has_rejection_or_level(tokens, flat):
        reasons.append(SetupReasonCode.NO_LEVEL_INTERACTION)
    elif directional:
        reasons.append(SetupReasonCode.DIRECTIONAL_CONTEXT_WITHOUT_SETUP_TRIGGER)
        reasons.append(SetupReasonCode.NO_CONFIRMATION_REQUIREMENT)
    if choppy:
        reasons.append(SetupReasonCode.CHOP_WITHOUT_SETUP)
    if context.entry_quality in {"WEAK", "POOR", "INVALID"}:
        reasons.append(SetupReasonCode.WEAK_CONTEXT_FILTERED_TO_NO_SETUP)
    if context.action == "NO_ACTION":
        reasons.append(SetupReasonCode.ANALYSIS_NO_ACTION_WITHOUT_SETUP_CONTEXT)
    return _no_setup(context, reasons, invalidations, directional=directional,
                     level=_has_rejection_or_level(tokens, flat), choppy=choppy)


def _diagnostics(*, bucket: SetupSemanticBucket, structural: bool, directional: bool,
                 level: bool, confirmation: bool, invalidated: bool, choppy: bool,
                 late: bool, reasons: list[SetupReasonCode]) -> SetupDiagnostics:
    return SetupDiagnostics(
        has_structural_trigger=structural,
        has_directional_context=directional,
        has_level_context=level,
        has_confirmation_requirement=confirmation,
        has_invalidation_context=invalidated,
        is_choppy_noise=choppy,
        is_late_entry=late,
        is_actionable_setup_candidate=bucket is SetupSemanticBucket.CANDIDATE_STRUCTURE,
        semantic_bucket=bucket.value,
        diagnostic_reasons=[reason.value for reason in reasons],
    )


def _candidate(setup_type: SetupType, context: SetupContext, reasons: list[SetupReasonCode],
               invalidations: list[str], *, direction: str, level: bool) -> SetupRuleResult:
    return SetupRuleResult(
        status="", setup_type=setup_type.value, direction_hint=direction,
        confirmation_state=ConfirmationState.CONFIRMED_BY_ANALYSIS.value,
        setup_quality=_quality(context, wait=False),
        reason_codes=[reason.value for reason in reasons],
        invalidation_reasons=invalidations,
        diagnostics=_diagnostics(
            bucket=SetupSemanticBucket.CANDIDATE_STRUCTURE, structural=True,
            directional=context.regime in {"UP", "DOWN"}, level=level,
            confirmation=False, invalidated=False, choppy=False, late=False,
            reasons=reasons),
    )


def _wait(setup_type: SetupType, context: SetupContext, reasons: list[SetupReasonCode],
          invalidations: list[str], *, direction: str, level: bool) -> SetupRuleResult:
    return SetupRuleResult(
        status="", setup_type=setup_type.value, direction_hint=direction,
        confirmation_state=ConfirmationState.AWAITING_CONFIRMATION.value,
        setup_quality=_quality(context, wait=True),
        reason_codes=[reason.value for reason in reasons],
        invalidation_reasons=invalidations,
        diagnostics=_diagnostics(
            bucket=SetupSemanticBucket.PRE_SETUP_WAITING_CONFIRMATION, structural=True,
            directional=context.regime in {"UP", "DOWN"}, level=level,
            confirmation=True, invalidated=False, choppy=False, late=False,
            reasons=reasons),
    )


def _invalid(setup_type: SetupType, context: SetupContext, invalidations: list[str],
             reasons: list[SetupReasonCode], *, direction: str, structural: bool,
             level: bool, late: bool = False) -> SetupRuleResult:
    active = list(invalidations)
    if not active:
        active.append(InvalidationReason.NO_STRUCTURAL_CONFIRMATION.value)
    return SetupRuleResult(
        status="", setup_type=setup_type.value, direction_hint=direction,
        confirmation_state=ConfirmationState.INVALIDATED_BY_CONTEXT.value,
        setup_quality=SetupQuality.INVALID.value,
        reason_codes=[reason.value for reason in reasons], invalidation_reasons=active,
        diagnostics=_diagnostics(
            bucket=SetupSemanticBucket.INVALIDATED_STRUCTURE, structural=structural,
            directional=context.regime in {"UP", "DOWN"}, level=level,
            confirmation=False, invalidated=True, choppy=False, late=late,
            reasons=reasons),
    )


def _no_setup(context: SetupContext, reasons: list[SetupReasonCode], invalidations: list[str],
              *, directional: bool, level: bool, choppy: bool) -> SetupRuleResult:
    return SetupRuleResult(
        status="", setup_type=SetupType.NO_SETUP.value,
        direction_hint=DirectionHint.NONE.value,
        confirmation_state=ConfirmationState.NOT_APPLICABLE.value,
        setup_quality=_quality(context, wait=True),
        reason_codes=[reason.value for reason in reasons],
        invalidation_reasons=invalidations,
        diagnostics=_diagnostics(
            bucket=SetupSemanticBucket.NO_STRUCTURAL_SETUP, structural=False,
            directional=directional, level=level, confirmation=False,
            invalidated=bool(invalidations), choppy=choppy, late=False, reasons=reasons),
    )


def _quality(context: SetupContext, *, wait: bool) -> str:
    quality = context.entry_quality or SetupQuality.UNKNOWN.value
    if quality not in {item.value for item in SetupQuality}:
        quality = SetupQuality.UNKNOWN.value
    if wait and quality in {SetupQuality.GOOD.value, SetupQuality.ACCEPTABLE.value}:
        return SetupQuality.WEAK.value
    return quality


def _acceptable(context: SetupContext) -> bool:
    return context.entry_quality in {"GOOD", "ACCEPTABLE"}


def _blocked(invalidations: list[str]) -> bool:
    return blocks_existing_setup(invalidations)


def _direction_from_regime(regime: str | None) -> str:
    if regime == "UP":
        return DirectionHint.BULLISH.value
    if regime == "DOWN":
        return DirectionHint.BEARISH.value
    return DirectionHint.NEUTRAL.value


def _flatten(value: object) -> str:
    parts: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            parts.extend((str(key).upper(), _flatten(nested)))
    elif isinstance(value, (list, tuple, set)):
        parts.extend(_flatten(item) for item in value)
    else:
        parts.append(str(value).upper())
    return " ".join(parts)


def _confirmed(flat: str, tokens: set[str]) -> bool:
    return any(word in flat for word in ("CONFIRMED", "FOLLOW_THROUGH")) or bool(
        tokens.intersection(_BREAKOUT_CONFIRMATION))


def _breakout_held(flat: str) -> bool:
    return "BREAKOUT" in flat and any(word in flat for word in ("HELD", "FOLLOW_THROUGH", "CONFIRMED"))


def _is_breakout_retest(tokens: set[str], flat: str) -> bool:
    positive = {"SUCCESSFUL_BREAKOUT_RETEST", "BREAKOUT_RETEST_HELD",
                "BREAKOUT_RETEST_CONFIRMED", "SUCCESSFUL_RETEST"}
    return bool(tokens.intersection(positive)) or any(phrase in flat for phrase in (
        "RETEST_STATUS HELD", "RETEST_STATUS CONFIRMED", "RETEST_RESULT SUCCESSFUL",
        "BREAKOUT_RETEST TRUE"))


def _has_range(tokens: set[str], flat: str, regime: str | None) -> bool:
    return regime == "FLAT" or "MARKET_STRUCTURE_RANGE" in tokens or any(
        token in tokens for token in ("SCHWAGER_TRADING_RANGE_DETECTED", "MARKET_HYPOTHESIS_CONFIRMED_RANGE_CONFIRMED")) or "RANGE_CONTEXT" in flat


def _has_edge_interaction(flat: str, tokens: set[str]) -> bool:
    explicit_tokens = {
        "BOUNDARY_REJECTION_WITHOUT_BREAKOUT", "RANGE_BOUNDARY_REJECTION",
        "SUPPORT_REJECTION", "RESISTANCE_REJECTION",
    }
    phrases = (
        "PRICE_LOCATION SUPPORT", "PRICE_LOCATION RESISTANCE",
        "PRICE_LOCATION LOWER_BOUNDARY", "PRICE_LOCATION UPPER_BOUNDARY",
        "AT_RANGE_BOUNDARY TRUE", "EDGE_TOUCH TRUE", "BOUNDARY_TOUCH TRUE",
    )
    return bool(tokens.intersection(explicit_tokens)) or any(phrase in flat for phrase in phrases)


def _has_rejection_or_level(tokens: set[str], flat: str) -> bool:
    return _has_edge_interaction(flat, tokens) or any(
        marker in tokens for marker in (
            "IMPULSE_HIGH_REJECTION", "IMPULSE_LOW_REJECTION",
            "WICK_REJECTION_AFTER_EXTENSION", "FAILED_BREAKOUT_RANGE_REENTRY",
            "RETURNED_INSIDE_CONFIRMED_RANGE",
        )) or any(phrase in flat for phrase in (
            "LEVEL_INTERACTION TRUE", "REJECTION_EVIDENCE TRUE",
            "PRICE_LOCATION SUPPORT", "PRICE_LOCATION RESISTANCE",
        ))


def _range_rejection(flat: str, tokens: set[str]) -> bool:
    has_range = _has_range(tokens, flat, "FLAT" if "MARKET_STRUCTURE RANGE" in flat else None)
    rejection = "REJECTION_EVIDENCE TRUE" in flat or bool(tokens.intersection({
        "BOUNDARY_REJECTION_WITHOUT_BREAKOUT", "RANGE_BOUNDARY_REJECTION",
        "SUPPORT_REJECTION", "RESISTANCE_REJECTION",
    }))
    return has_range and _has_edge_interaction(flat, tokens) and rejection


def _range_direction(flat: str) -> str:
    if "PRICE_LOCATION SUPPORT" in flat or "PRICE_LOCATION LOWER_BOUNDARY" in flat:
        return DirectionHint.BULLISH.value
    if "PRICE_LOCATION RESISTANCE" in flat or "PRICE_LOCATION UPPER_BOUNDARY" in flat:
        return DirectionHint.BEARISH.value
    return DirectionHint.NEUTRAL.value


def _false_breakout_direction(context: SetupContext, flat: str) -> str:
    if "FAILED_BREAKOUT_DIRECTION UP" in flat or "FAILED_BREAKOUT_DIRECTION:UP" in flat:
        return DirectionHint.BEARISH.value
    if "FAILED_BREAKOUT_DIRECTION DOWN" in flat or "FAILED_BREAKOUT_DIRECTION:DOWN" in flat:
        return DirectionHint.BULLISH.value
    direction = _direction_from_regime(context.regime)
    if direction == DirectionHint.BULLISH.value:
        return DirectionHint.BEARISH.value
    if direction == DirectionHint.BEARISH.value:
        return DirectionHint.BULLISH.value
    return DirectionHint.NEUTRAL.value


def _reversal_evidence(tokens: set[str], flat: str) -> bool:
    return bool(tokens.intersection({"REVERSAL_EVIDENCE", "REVERSAL_TRIGGER"})) or "REVERSAL_EVIDENCE TRUE" in flat


def _reversal_confirmed(tokens: set[str], flat: str) -> bool:
    return bool(tokens.intersection({"REVERSAL_CONFIRMED", "REVERSAL_FOLLOW_THROUGH"})) or "REVERSAL_CONFIRMED TRUE" in flat


def _reversal_direction(flat: str) -> str:
    if "BULLISH" in flat:
        return DirectionHint.BULLISH.value
    if "BEARISH" in flat:
        return DirectionHint.BEARISH.value
    return DirectionHint.NEUTRAL.value


def _is_choppy(tokens: set[str], flat: str) -> bool:
    return any("CHOP" in token for token in tokens) or "HIGH_OVERLAP" in flat or "CHOPPY" in flat
