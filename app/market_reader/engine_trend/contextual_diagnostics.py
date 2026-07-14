"""Offline explainability for ENGINE_TREND results.

This module is deliberately not imported by the engine facade, composer, setup
contracts, or trading runtime.  It describes an already-produced regime; it
never selects or changes one.  Proximity values below are diagnostic display
settings, not trading thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from re import fullmatch
from typing import Any, Mapping, Sequence


DIAGNOSTIC_NEAR_ZONE_PCT = 0.50
DIAGNOSTIC_NEAR_ZONE_ATR = 1.00


class DiagnosticTag(str, Enum):
    LOCAL_RANGE_UNCONFIRMED = "LOCAL_RANGE_UNCONFIRMED"
    CONFIRMED_RANGE_CONTEXT = "CONFIRMED_RANGE_CONTEXT"
    NEAR_RESISTANCE = "NEAR_RESISTANCE"
    NEAR_SUPPORT = "NEAR_SUPPORT"
    BREAKOUT_NOT_CONFIRMED = "BREAKOUT_NOT_CONFIRMED"
    BREAKDOWN_NOT_CONFIRMED = "BREAKDOWN_NOT_CONFIRMED"
    NEAR_UPPER_RANGE_BOUNDARY = "NEAR_UPPER_RANGE_BOUNDARY"
    NEAR_LOWER_RANGE_BOUNDARY = "NEAR_LOWER_RANGE_BOUNDARY"
    INSIDE_RANGE = "INSIDE_RANGE"
    INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER = (
        "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER"
    )
    LOW_TREND_STRENGTH = "LOW_TREND_STRENGTH"
    MTF_CONFLICT = "MTF_CONFLICT"
    HIGHER_TF_BEARISH_RISK = "HIGHER_TF_BEARISH_RISK"
    HIGHER_TF_BULLISH_RISK = "HIGHER_TF_BULLISH_RISK"
    BEARISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS = (
        "BEARISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS"
    )
    BULLISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS = (
        "BULLISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS"
    )
    UNRESOLVED_HYPOTHESIS_CONFLICT = "UNRESOLVED_HYPOTHESIS_CONFLICT"
    RANGE_TREND_CONFLICT = "RANGE_TREND_CONFLICT"
    NO_CAUSAL_HYPOTHESIS = "NO_CAUSAL_HYPOTHESIS"
    WAIT_FOR_CONFIRMATION = "WAIT_FOR_CONFIRMATION"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class DiagnosticZone:
    zone_type: str
    zone_low: float
    zone_high: float
    source: str
    touch_count: int | None = None

    def __post_init__(self) -> None:
        if self.zone_type not in {"SUPPORT", "RESISTANCE"}:
            raise ValueError("zone_type must be SUPPORT or RESISTANCE")
        if self.zone_low > self.zone_high:
            raise ValueError("zone_low must be <= zone_high")
        if not self.source:
            raise ValueError("zone source must not be empty")


@dataclass(frozen=True)
class ContextualDiagnosticInput:
    symbol: str
    timeframe: str
    as_of: str
    source_regime: str
    source_confidence: float
    last_close: float | None
    day_high: float | None = None
    day_low: float | None = None
    atr: float | None = None
    structure: str | None = None
    zones: tuple[DiagnosticZone, ...] = ()
    range_confirmed: bool = False
    range_lower: float | None = None
    range_upper: float | None = None
    breakout_status: str = "NO_BREAKOUT"
    breakout_direction: str = "NONE"
    confirmed_hypotheses: tuple[str, ...] = ()
    indicator_direction: str = "NEUTRAL"
    indicator_strength: str = "NONE"
    indicator_reason: str = ""
    bullish_votes: int = 0
    bearish_votes: int = 0
    adx: float | None = None
    timeframe_regimes: Mapping[str, str] = field(default_factory=dict)
    conflict_codes: tuple[str, ...] = ()
    bullish_confirmation_needed: tuple[str, ...] = ()
    bearish_confirmation_needed: tuple[str, ...] = ()
    observable_fields: Mapping[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source_regime not in {"UP", "DOWN", "FLAT", "UNKNOWN"}:
            raise ValueError("unsupported source_regime")
        if not 0.0 <= self.source_confidence <= 1.0:
            raise ValueError("source_confidence must be within [0, 1]")
        if self.last_close is not None and self.last_close <= 0:
            raise ValueError("last_close must be positive")


def _distance_to_zone(price: float, zone: DiagnosticZone) -> float:
    if zone.zone_low <= price <= zone.zone_high:
        return 0.0
    return min(abs(price - zone.zone_low), abs(price - zone.zone_high))


def _zone_payload(
    price: float, atr: float | None, zone: DiagnosticZone | None
) -> dict[str, Any] | None:
    if zone is None:
        return None
    distance = _distance_to_zone(price, zone)
    payload: dict[str, Any] = {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "distance_pct": round(distance / price * 100.0, 6),
        "distance_atr": round(distance / atr, 6) if atr and atr > 0 else None,
        "source": zone.source,
    }
    if zone.touch_count is not None:
        payload["touch_count"] = zone.touch_count
    return payload


def _is_near(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    by_pct = float(payload["distance_pct"]) <= DIAGNOSTIC_NEAR_ZONE_PCT
    distance_atr = payload.get("distance_atr")
    return by_pct or (distance_atr is not None and float(distance_atr) <= DIAGNOSTIC_NEAR_ZONE_ATR)


def _nearest(
    data: ContextualDiagnosticInput, zone_type: str
) -> tuple[DiagnosticZone | None, dict[str, Any] | None]:
    candidates = [item for item in data.zones if item.zone_type == zone_type]
    if data.last_close is None:
        return None, None
    zone = min(candidates, key=lambda item: _distance_to_zone(data.last_close, item), default=None)
    return zone, _zone_payload(data.last_close, data.atr, zone)


def _has_confirmed_direction(data: ContextualDiagnosticInput, direction: str) -> bool:
    tokens = ("UP", "BULL") if direction == "BULLISH" else ("DOWN", "BEAR")
    return any(any(token in item.upper() for token in tokens) for item in data.confirmed_hypotheses)


def _timeframe_seconds(value: str) -> int | None:
    match = fullmatch(r"([1-9]\d*)([mhdw])", value.strip().lower())
    if match is None:
        return None
    multiplier = {"m": 60, "h": 3600, "d": 86400, "w": 604800}[match.group(2)]
    return int(match.group(1)) * multiplier


def _summary(data: ContextualDiagnosticInput, tags: Sequence[str]) -> str:
    tag_set = set(tags)
    if DiagnosticTag.RANGE_TREND_CONFLICT.value in tag_set:
        return (
            "Подтверждённый диапазон конфликтует с направленной гипотезой. "
            "До разрешения конфликта действие отсутствует."
        )
    if DiagnosticTag.MTF_CONFLICT.value in tag_set:
        risk = (
            "bearish"
            if DiagnosticTag.HIGHER_TF_BEARISH_RISK.value in tag_set
            else "bullish"
            if DiagnosticTag.HIGHER_TF_BULLISH_RISK.value in tag_set
            else "направленный"
        )
        if DiagnosticTag.NEAR_RESISTANCE.value in tag_set:
            return (
                f"Локальная консолидация под сопротивлением при {risk}-risk старшего ТФ. "
                "Long требует закрытого пробоя/ретеста; short — rejection и breakdown поддержки."
            )
        return (
            f"Рабочий ТФ не подтвердил вход, а старший ТФ несёт {risk}-risk. "
            "Это MTF conflict: требуется causal confirmation на рабочем ТФ."
        )
    if DiagnosticTag.NEAR_RESISTANCE.value in tag_set:
        return (
            "Локальная консолидация под сопротивлением. Long требует закрытого пробоя/ретеста, "
            "short — rejection и подтверждённого breakdown."
        )
    if DiagnosticTag.NEAR_SUPPORT.value in tag_set:
        return (
            "Цена у поддержки, но breakdown не подтверждён. Направленное действие отсутствует "
            "до causal trigger и follow-through."
        )
    if DiagnosticTag.INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER.value in tag_set:
        return (
            "Технический перевес есть, но он confirmatory-only: без breakout/retest, "
            "reversal или continuation confirmation действие отсутствует."
        )
    if data.source_regime == "FLAT":
        return "Подтверждён контекст диапазона; диагностический слой не создаёт торговый setup."
    return "Causal hypothesis и подтверждённый entry trigger отсутствуют; требуется подтверждение."


def diagnose_context(data: ContextualDiagnosticInput) -> dict[str, Any]:
    """Explain an immutable source result and always remain non-actionable."""

    def observable(field_name: str) -> bool:
        return data.observable_fields.get(field_name, True)

    price_observable = observable("price_position") and data.last_close is not None
    zones_observable = observable("zones")
    zone_proximity_observable = zones_observable and price_observable
    range_observable = observable("range")
    breakout_observable = observable("breakout")
    indicator_observable = observable("indicators")
    mtf_observable = observable("multi_timeframe")
    hypotheses_observable = observable("hypotheses")

    support_zones = [item for item in data.zones if item.zone_type == "SUPPORT"]
    resistance_zones = [item for item in data.zones if item.zone_type == "RESISTANCE"]
    support_zone = max(support_zones, key=lambda item: item.touch_count or 0, default=None)
    resistance_zone = max(resistance_zones, key=lambda item: item.touch_count or 0, default=None)
    _, nearest_support = _nearest(data, "SUPPORT") if zone_proximity_observable else (None, None)
    _, nearest_resistance = _nearest(data, "RESISTANCE") if zone_proximity_observable else (None, None)
    near_support = _is_near(nearest_support)
    near_resistance = _is_near(nearest_resistance)
    tags: list[str] = []

    def add(tag: DiagnosticTag) -> None:
        if tag.value not in tags:
            tags.append(tag.value)

    structure = (data.structure or "").upper()
    if range_observable and data.range_confirmed:
        add(DiagnosticTag.CONFIRMED_RANGE_CONTEXT)
        if price_observable and data.range_lower is not None and data.range_upper is not None:
            if data.range_lower <= data.last_close <= data.range_upper:
                add(DiagnosticTag.INSIDE_RANGE)
    elif range_observable and zones_observable and (
        ("SIDEWAYS" in structure or "MIXED" in structure)
        and support_zone
        and resistance_zone
        and support_zone.touch_count is not None
        and support_zone.touch_count >= 2
        and resistance_zone.touch_count is not None
        and resistance_zone.touch_count >= 2
    ):
        add(DiagnosticTag.LOCAL_RANGE_UNCONFIRMED)

    if price_observable and range_observable and data.range_lower is not None and data.range_upper is not None:
        range_width = max(data.range_upper - data.range_lower, 1e-12)
        boundary_fraction = min(
            abs(data.last_close - data.range_lower),
            abs(data.range_upper - data.last_close),
        ) / range_width
        if boundary_fraction <= 0.15:
            if abs(data.last_close - data.range_upper) <= abs(data.last_close - data.range_lower):
                add(DiagnosticTag.NEAR_UPPER_RANGE_BOUNDARY)
            else:
                add(DiagnosticTag.NEAR_LOWER_RANGE_BOUNDARY)

    if near_resistance:
        add(DiagnosticTag.NEAR_RESISTANCE)
    if near_support:
        add(DiagnosticTag.NEAR_SUPPORT)

    upward_confirmed = breakout_observable and data.breakout_status in {"CONFIRMED", "RETEST_HELD"} and data.breakout_direction == "UPWARD"
    downward_confirmed = breakout_observable and data.breakout_status in {"CONFIRMED", "RETEST_HELD"} and data.breakout_direction == "DOWNWARD"
    if breakout_observable and hypotheses_observable and near_resistance and not upward_confirmed and not _has_confirmed_direction(data, "BULLISH"):
        add(DiagnosticTag.BREAKOUT_NOT_CONFIRMED)
    if breakout_observable and hypotheses_observable and near_support and not downward_confirmed and not _has_confirmed_direction(data, "BEARISH"):
        add(DiagnosticTag.BREAKDOWN_NOT_CONFIRMED)

    indicator_direction = data.indicator_direction.upper()
    if indicator_observable and hypotheses_observable and indicator_direction in {"BULLISH", "BEARISH"} and not _has_confirmed_direction(
        data, indicator_direction
    ):
        add(DiagnosticTag.INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER)
    if indicator_observable and data.adx is not None and data.adx < 15.0 and ("SIDEWAYS" in structure or "MIXED" in structure):
        add(DiagnosticTag.LOW_TREND_STRENGTH)

    regimes = {key: value.upper() for key, value in data.timeframe_regimes.items()}
    other_regimes = [value for key, value in regimes.items() if key != data.timeframe]
    directional_other = {value for value in other_regimes if value in {"UP", "DOWN"}}
    if mtf_observable and directional_other and (data.source_regime == "UNKNOWN" or len(directional_other) > 1):
        add(DiagnosticTag.MTF_CONFLICT)
    decision_seconds = _timeframe_seconds(data.timeframe)
    higher_directional = {
        value
        for key, value in regimes.items()
        if key != data.timeframe
        and value in {"UP", "DOWN"}
        and decision_seconds is not None
        and (_timeframe_seconds(key) or 0) > decision_seconds
    }
    if mtf_observable and "DOWN" in higher_directional:
        add(DiagnosticTag.HIGHER_TF_BEARISH_RISK)
    if mtf_observable and "UP" in higher_directional:
        add(DiagnosticTag.HIGHER_TF_BULLISH_RISK)

    conflict_text = " ".join(data.conflict_codes).upper()
    if hypotheses_observable and "CONFLICT" in conflict_text:
        add(DiagnosticTag.UNRESOLVED_HYPOTHESIS_CONFLICT)
    if hypotheses_observable and "RANGE" in conflict_text and ("TREND" in conflict_text or "CONTINUATION" in conflict_text):
        add(DiagnosticTag.RANGE_TREND_CONFLICT)
    if hypotheses_observable and data.source_regime == "UNKNOWN" and not data.confirmed_hypotheses:
        if "BEARISH" in structure:
            add(DiagnosticTag.BEARISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS)
        elif "BULLISH" in structure:
            add(DiagnosticTag.BULLISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS)
        add(DiagnosticTag.NO_CAUSAL_HYPOTHESIS)

    if data.source_regime == "UNKNOWN":
        add(DiagnosticTag.WAIT_FOR_CONFIRMATION)
        add(DiagnosticTag.NO_ACTION)

    day_position = None
    if price_observable and data.day_high is not None and data.day_low is not None and data.day_high > data.day_low:
        day_position = (data.last_close - data.day_low) / (data.day_high - data.day_low)
    no_trade_reasons = [item.lower() for item in tags if item not in {"WAIT_FOR_CONFIRMATION", "NO_ACTION"}]
    bullish_needed = list(data.bullish_confirmation_needed) or [
        "closed breakout or confirmed bullish reversal",
        "retest/hold and follow-through",
    ]
    bearish_needed = list(data.bearish_confirmation_needed) or [
        "confirmed rejection or closed breakdown",
        "retest/hold and follow-through",
    ]
    payload: dict[str, Any] = {
        "symbol": data.symbol,
        "timeframe": data.timeframe,
        "as_of": data.as_of,
        "source_regime": data.source_regime,
        "source_confidence": data.source_confidence,
        "action": "NO_ACTION",
        "contextual_state": "WAIT_FOR_CONFIRMATION" if data.source_regime == "UNKNOWN" else "CONTEXT_ONLY",
        "observability": {
            field_name: "observable" if state else "not_observable"
            for field_name, state in {
                "price_position": price_observable,
                "zones": zones_observable,
                "zone_proximity": zone_proximity_observable,
                "range": range_observable,
                "breakout": breakout_observable,
                "indicators": indicator_observable,
                "multi_timeframe": mtf_observable,
                "hypotheses": hypotheses_observable,
            }.items()
        },
        "diagnostic_tags": tags,
        "price_position": {
            "last_close": data.last_close,
            "day_high": data.day_high,
            "day_low": data.day_low,
            "position_in_day_range": round(day_position, 6) if day_position is not None else None,
        },
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "technical_pressure": {
            "direction": indicator_direction,
            "strength": data.indicator_strength,
            "reason": data.indicator_reason,
            "bullish_votes": data.bullish_votes,
            "bearish_votes": data.bearish_votes,
            "adx": data.adx,
        },
        "multi_timeframe": {
            **regimes,
            "summary": (
                "local neutral state with higher timeframe directional risk"
                if DiagnosticTag.MTF_CONFLICT.value in tags
                else "no unresolved directional MTF conflict detected"
            ),
        },
        "confirmation_needed": {"bullish": bullish_needed, "bearish": bearish_needed},
        "no_trade_reasons": no_trade_reasons,
        "human_summary": _summary(data, tags),
        "safety": {
            "source_regime_preserved": True,
            "setup_created": False,
            "trade_signal_created": False,
            "diagnostics_only": True,
        },
    }
    return payload


def zone_from_engine_output(zone: Any, *, source: str = "engine_zone") -> DiagnosticZone:
    """Small duck-typed adapter for an existing SupportResistanceZone."""

    current_type = getattr(zone, "current_zone_type", None) or getattr(zone, "zone_type")
    return DiagnosticZone(
        zone_type=getattr(current_type, "value", str(current_type)),
        zone_low=float(getattr(zone, "lower_price")),
        zone_high=float(getattr(zone, "upper_price")),
        source=source,
        touch_count=int(getattr(zone, "touch_count")),
    )
