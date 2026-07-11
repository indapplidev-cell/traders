from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


DEFAULT_CLEAN_TREND_CONFIDENCE_THRESHOLD = 0.60


class SymbolBucket(StrEnum):
    CLEAN_TREND = "CLEAN_TREND"
    STABLE_FLAT = "STABLE_FLAT"
    TRANSITIONING = "TRANSITIONING"
    UNSTABLE = "UNSTABLE"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"
    SKIP_CANDIDATE = "SKIP_CANDIDATE"


class MarketContextState(StrEnum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    MIXED = "MIXED"
    UNSTABLE = "UNSTABLE"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class SymbolBucketDecision:
    symbol: str
    bucket: SymbolBucket
    regime: str
    stability: str
    last_transition: str
    confidence: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    skip_candidate: bool = False
    safe_for_runtime_trading: bool = False
    trade_signal: str = "NOT_EVALUATED"


TREND_REGIMES = {"UP", "DOWN"}
CLEAN_TREND_TRANSITIONS = {
    "NO_CHANGE",
    "FLAT_TO_UP",
    "FLAT_TO_DOWN",
    "UNKNOWN_TO_UP",
    "UNKNOWN_TO_DOWN",
}
SKIP_CANDIDATE_BUCKETS = {
    SymbolBucket.UNKNOWN,
    SymbolBucket.UNSTABLE,
    SymbolBucket.INSUFFICIENT_DATA,
    SymbolBucket.ERROR,
}
UNKNOWNISH_BUCKETS = {
    SymbolBucket.UNKNOWN,
    SymbolBucket.INSUFFICIENT_DATA,
    SymbolBucket.ERROR,
}


def classify_symbol_bucket(row: object) -> SymbolBucketDecision:
    symbol = _read_token(row, "symbol", "UNKNOWN")
    status_value = _read_required_token(row, "status")
    regime_value = _read_required_token(row, "current_regime")
    stability_value = _read_required_token(row, "stability")
    transition_value = _read_required_token(row, "last_transition")
    confidence = _read_float(_read_field(row, "confidence", _read_field(row, "current_confidence", 0.0)), 0.0)
    warnings = _read_warnings(row)

    if None in (status_value, regime_value, stability_value, transition_value):
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.ERROR,
            regime=regime_value or "UNKNOWN",
            stability=stability_value or "UNKNOWN",
            last_transition=transition_value or "UNKNOWN",
            confidence=confidence,
            reason_codes=("L1_ROW_ERROR",),
            warnings=warnings,
        )

    status = status_value
    regime = regime_value
    stability = stability_value
    last_transition = transition_value

    if status == "INSUFFICIENT_DATA":
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.INSUFFICIENT_DATA,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("L1_INSUFFICIENT_DATA",),
            warnings=warnings,
        )

    if status == "ERROR" or status != "OK":
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.ERROR,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("L1_ROW_ERROR",),
            warnings=warnings,
        )

    if regime == "UNKNOWN":
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.UNKNOWN,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("CURRENT_REGIME_UNKNOWN",),
            warnings=warnings,
        )

    if stability == "STABLE" and regime == "FLAT" and last_transition == "NO_CHANGE":
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.STABLE_FLAT,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("STABLE_FLAT_CONTEXT",),
            warnings=warnings,
        )

    if (
        regime in TREND_REGIMES
        and stability in {"STABLE", "CHANGING"}
        and last_transition in CLEAN_TREND_TRANSITIONS
        and confidence >= DEFAULT_CLEAN_TREND_CONFIDENCE_THRESHOLD
    ):
        direction_reason = "CURRENT_UP_CONTEXT" if regime == "UP" else "CURRENT_DOWN_CONTEXT"
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.CLEAN_TREND,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("CURRENT_TREND_CONTEXT", direction_reason, "ACCEPTABLE_CONFIDENCE"),
            warnings=warnings,
        )

    if stability == "UNSTABLE" or _has_too_many_regimes(row):
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.UNSTABLE,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("UNSTABLE_TIMELINE_CONTEXT",),
            warnings=warnings,
        )

    if last_transition != "NO_CHANGE":
        return _decision(
            symbol=symbol,
            bucket=SymbolBucket.TRANSITIONING,
            regime=regime,
            stability=stability,
            last_transition=last_transition,
            confidence=confidence,
            reason_codes=("RECENT_REGIME_TRANSITION",),
            warnings=warnings,
        )

    return _decision(
        symbol=symbol,
        bucket=SymbolBucket.UNKNOWN,
        regime=regime,
        stability=stability,
        last_transition=last_transition,
        confidence=confidence,
        reason_codes=("CONTEXT_RULE_UNMATCHED",),
        warnings=warnings,
    )


def classify_overall_market_context(decisions: tuple[SymbolBucketDecision, ...]) -> MarketContextState:
    if not decisions:
        return MarketContextState.ERROR

    if all(decision.bucket in UNKNOWNISH_BUCKETS for decision in decisions):
        return MarketContextState.UNKNOWN

    unstable_or_transitioning_count = sum(
        1 for decision in decisions if decision.bucket in {SymbolBucket.UNSTABLE, SymbolBucket.TRANSITIONING}
    )
    if unstable_or_transitioning_count > len(decisions) / 2:
        return MarketContextState.UNSTABLE

    evaluable = tuple(decision for decision in decisions if decision.bucket not in UNKNOWNISH_BUCKETS)
    if not evaluable:
        return MarketContextState.UNKNOWN

    stable_flat_count = sum(1 for decision in evaluable if decision.bucket == SymbolBucket.STABLE_FLAT)
    if stable_flat_count > len(evaluable) / 2:
        return MarketContextState.RANGING

    clean_trends = tuple(decision for decision in evaluable if decision.bucket == SymbolBucket.CLEAN_TREND)
    up_trends = sum(1 for decision in clean_trends if decision.regime == "UP")
    down_trends = sum(1 for decision in clean_trends if decision.regime == "DOWN")
    if up_trends and down_trends:
        return MarketContextState.MIXED
    if len(clean_trends) > len(evaluable) / 2:
        return MarketContextState.TRENDING

    return MarketContextState.MIXED


def _decision(
    *,
    symbol: str,
    bucket: SymbolBucket,
    regime: str,
    stability: str,
    last_transition: str,
    confidence: float,
    reason_codes: tuple[str, ...],
    warnings: tuple[str, ...],
) -> SymbolBucketDecision:
    skip_candidate = bucket in SKIP_CANDIDATE_BUCKETS
    if skip_candidate:
        reason_codes = (*reason_codes, "SKIP_CANDIDATE_CONTEXT")
    return SymbolBucketDecision(
        symbol=symbol,
        bucket=bucket,
        regime=regime,
        stability=stability,
        last_transition=last_transition,
        confidence=confidence,
        reason_codes=reason_codes,
        warnings=warnings,
        skip_candidate=skip_candidate,
    )


def _has_too_many_regimes(row: object) -> bool:
    regimes = _read_field(row, "regimes", ())
    if not isinstance(regimes, (list, tuple)):
        return False
    normalized = {_normalize_token(regime, "") for regime in regimes}
    normalized.discard("")
    return len(normalized) >= 3


def _read_warnings(row: object) -> tuple[str, ...]:
    warnings = _read_field(row, "warnings", ())
    if isinstance(warnings, tuple):
        return tuple(str(warning) for warning in warnings)
    if isinstance(warnings, list):
        return tuple(str(warning) for warning in warnings)
    return ()


def _read_required_token(row: object, field_name: str) -> str | None:
    value = _read_field(row, field_name, None)
    if value is None:
        return None
    token = _normalize_token(value, "")
    return token or None


def _read_token(row: object, field_name: str, default: str) -> str:
    return _normalize_token(_read_field(row, field_name, default), default)


def _read_field(row: object, field_name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(field_name, default)
    return getattr(row, field_name, default)


def _read_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _normalize_token(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip().upper()
    return text or default
