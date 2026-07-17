"""Context reasons that block or weaken a potential setup."""

from enum import StrEnum

from app.engine_setup.setup_context import SetupContext


class InvalidationReason(StrEnum):
    ANALYSIS_NOT_ANALYZED = "ANALYSIS_NOT_ANALYZED"
    ANALYSIS_ERROR = "ANALYSIS_ERROR"
    NOT_ENOUGH_DATA = "NOT_ENOUGH_DATA"
    FUTURE_BARS_REJECTED = "FUTURE_BARS_REJECTED"
    ENTRY_QUALITY_INVALID = "ENTRY_QUALITY_INVALID"
    ENTRY_QUALITY_POOR = "ENTRY_QUALITY_POOR"
    LATE_CONFIRMATION_RISK = "LATE_CONFIRMATION_RISK"
    POST_SPIKE_PULLBACK_RISK = "POST_SPIKE_PULLBACK_RISK"
    RANGE_REENTRY_RISK = "RANGE_REENTRY_RISK"
    DISTRIBUTION_RISK = "DISTRIBUTION_RISK"
    IMPULSE_EXHAUSTION_RISK = "IMPULSE_EXHAUSTION_RISK"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_STRUCTURAL_CONFIRMATION = "NO_STRUCTURAL_CONFIRMATION"
    CONFLICTING_PHASE_CONTEXT = "CONFLICTING_PHASE_CONTEXT"


CRITICAL_INVALIDATION_REASONS = frozenset({
    InvalidationReason.FUTURE_BARS_REJECTED.value,
    InvalidationReason.ANALYSIS_ERROR.value,
    InvalidationReason.NOT_ENOUGH_DATA.value,
    InvalidationReason.ENTRY_QUALITY_INVALID.value,
    InvalidationReason.LATE_CONFIRMATION_RISK.value,
    InvalidationReason.POST_SPIKE_PULLBACK_RISK.value,
    InvalidationReason.RANGE_REENTRY_RISK.value,
    InvalidationReason.DISTRIBUTION_RISK.value,
})

# These reasons may invalidate an already detected setup structure. Their mere
# presence does not manufacture a setup idea and therefore is not a fallback
# reason for SETUP_INVALID.
EXISTING_SETUP_BLOCKERS = frozenset({
    InvalidationReason.ENTRY_QUALITY_INVALID.value,
    InvalidationReason.ENTRY_QUALITY_POOR.value,
    InvalidationReason.POST_SPIKE_PULLBACK_RISK.value,
    InvalidationReason.RANGE_REENTRY_RISK.value,
    InvalidationReason.DISTRIBUTION_RISK.value,
})


def collect_invalidation_reasons(context: SetupContext) -> list[str]:
    tokens = set(context.reason_codes)
    phase = context.impulse_phase or ""
    scalar_values = _flatten_scalar_values(context.analysis_context)
    reasons: list[str] = []

    def add(reason: InvalidationReason, present: bool) -> None:
        if present and reason.value not in reasons:
            reasons.append(reason.value)

    add(InvalidationReason.ENTRY_QUALITY_INVALID, context.entry_quality == "INVALID")
    add(InvalidationReason.ENTRY_QUALITY_POOR, context.entry_quality == "POOR")
    add(InvalidationReason.LATE_CONFIRMATION_RISK,
        "LATE_CONFIRMATION_RISK" in phase or "LATE_DIRECTIONAL_CONFIRMATION" in tokens
        or "LATE_CONFIRMATION_RISK" in tokens
        or _context_flag(context.analysis_context, "LATE_CONFIRMATION_RISK")
        or "LATE_CONFIRMATION_RISK" in scalar_values)
    add(InvalidationReason.POST_SPIKE_PULLBACK_RISK,
        "POST_SPIKE_PULLBACK" in phase or "POST_SPIKE_PULLBACK" in tokens
        or _context_flag(context.analysis_context, "POST_SPIKE_PULLBACK")
        or "POST_SPIKE_PULLBACK" in scalar_values)
    add(InvalidationReason.RANGE_REENTRY_RISK,
        any(value in tokens for value in ("RANGE_REENTRY", "RANGE_REENTRY_ACTIVE"))
        or "RANGE_REENTRY" in phase
        or _context_flag(context.analysis_context, "RANGE_REENTRY")
        or "RANGE_REENTRY" in scalar_values)
    add(InvalidationReason.DISTRIBUTION_RISK,
        any("DISTRIBUTION" in value for value in tokens)
        or _context_flag(context.analysis_context, "DISTRIBUTION")
        or "DISTRIBUTION" in scalar_values)
    add(InvalidationReason.IMPULSE_EXHAUSTION_RISK,
        "IMPULSE_EXHAUSTION" in phase or any(value in tokens for value in (
            "EXTENDED_MOVE_EXHAUSTION_RISK", "CLIMAX_VOLUME_WITHOUT_FOLLOW_THROUGH",
            "WICK_REJECTION_AFTER_EXTENSION",
        )))
    add(InvalidationReason.LOW_CONFIDENCE,
        context.confidence is not None and float(context.confidence) < 0.35)
    add(InvalidationReason.CONFLICTING_PHASE_CONTEXT,
        any("PHASE_CONFLICT" in value for value in tokens))
    return reasons


def has_critical_invalidation(reasons: list[str]) -> bool:
    return bool(CRITICAL_INVALIDATION_REASONS.intersection(reasons))


def blocks_existing_setup(reasons: list[str]) -> bool:
    return bool(EXISTING_SETUP_BLOCKERS.intersection(reasons))


def _flatten_scalar_values(value: object) -> str:
    parts: list[str] = []
    if isinstance(value, dict):
        for nested in value.values():
            parts.append(_flatten_scalar_values(nested))
    elif isinstance(value, (list, tuple, set)):
        parts.extend(_flatten_scalar_values(item) for item in value)
    else:
        parts.append(str(value).upper())
    return " ".join(parts)


def _context_flag(value: object, name: str) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).upper()
            if name in normalized and _is_active(nested):
                return True
            if _context_flag(nested, name):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_context_flag(item, name) for item in value)
    return False


def _is_active(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.upper() not in {"", "NONE", "FALSE", "NO", "NO_BREAKOUT", "NOT_CONFIRMED"}
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, dict):
        return any(_is_active(nested) for nested in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_is_active(item) for item in value)
    return bool(value)
