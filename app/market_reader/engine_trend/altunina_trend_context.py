"""Altunina trend, impulse, correction, and pullback evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isclose
from typing import Any

from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendCandle,
    EngineTrendEvidence,
)


STRUCTURE_TOLERANCE_RATIO = 0.001
FIBONACCI_PULLBACK_LEVELS = (0.38, 0.50, 0.62)
ALTUNINA_CORRECTION_LIMIT = 0.62

BOOK_RULE = "ALTUNINA_BOOK_RULE"
DERIVED_HEURISTIC = "ENGINE_TREND_DERIVED_HEURISTIC"


class SwingPointType(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class PriceLegDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class AltuninaStructureDirection(str, Enum):
    BULLISH_STRUCTURE = "BULLISH_STRUCTURE"
    BEARISH_STRUCTURE = "BEARISH_STRUCTURE"
    SIDEWAYS_STRUCTURE = "SIDEWAYS_STRUCTURE"
    UNCLEAR_STRUCTURE = "UNCLEAR_STRUCTURE"


class TrendDurationClass(str, Enum):
    MULTI_YEAR = "MULTI_YEAR"
    MONTHLY_SCALE = "MONTHLY_SCALE"
    SUB_MONTH_SCALE = "SUB_MONTH_SCALE"
    UNKNOWN = "UNKNOWN"


class TrendHierarchyRole(str, Enum):
    PRIMARY = "PRIMARY"
    INTERMEDIATE = "INTERMEDIATE"
    MINOR = "MINOR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    timestamp: str
    price: float
    point_type: SwingPointType

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "price": float(self.price),
            "point_type": self.point_type.value,
        }


@dataclass(frozen=True)
class PriceLeg:
    start: SwingPoint
    end: SwingPoint
    direction: PriceLegDirection
    absolute_change: float
    relative_change: float
    candle_span: int

    def to_dict(self) -> dict[str, object]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "direction": self.direction.value,
            "absolute_change": float(self.absolute_change),
            "relative_change": float(self.relative_change),
            "candle_span": self.candle_span,
        }


@dataclass(frozen=True)
class TrendLineSummary:
    available: bool
    direction: PriceLegDirection
    start: SwingPoint | None
    end: SwingPoint | None
    slope_per_candle: float
    anchor_count: int
    method_origin: str = DERIVED_HEURISTIC

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "direction": self.direction.value,
            "start": self.start.to_dict() if self.start else None,
            "end": self.end.to_dict() if self.end else None,
            "slope_per_candle": float(self.slope_per_candle),
            "anchor_count": self.anchor_count,
            "method_origin": self.method_origin,
        }


@dataclass(frozen=True)
class TrendDurationSummary:
    duration_days: float | None
    duration_class: TrendDurationClass
    hierarchy_role: TrendHierarchyRole
    method_origin: str = BOOK_RULE

    def to_dict(self) -> dict[str, object]:
        return {
            "duration_days": self.duration_days,
            "duration_class": self.duration_class.value,
            "hierarchy_role": self.hierarchy_role.value,
            "method_origin": self.method_origin,
        }


@dataclass(frozen=True)
class ImpulseCorrectionSummary:
    bullish_impulse_total: float
    bearish_impulse_total: float
    bullish_correction_total: float
    bearish_correction_total: float
    dominant_impulse_direction: PriceLegDirection
    max_pullback_depth: float
    average_pullback_depth: float
    correction_count: int
    correction_limit: float
    correction_limit_breached: bool
    structural_pivot_breached: bool
    nearest_fibonacci_level: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "bullish_impulse_total": float(self.bullish_impulse_total),
            "bearish_impulse_total": float(self.bearish_impulse_total),
            "bullish_correction_total": float(self.bullish_correction_total),
            "bearish_correction_total": float(self.bearish_correction_total),
            "dominant_impulse_direction": self.dominant_impulse_direction.value,
            "max_pullback_depth": float(self.max_pullback_depth),
            "average_pullback_depth": float(self.average_pullback_depth),
            "correction_count": self.correction_count,
            "correction_limit": float(self.correction_limit),
            "correction_limit_breached": self.correction_limit_breached,
            "structural_pivot_breached": self.structural_pivot_breached,
            "nearest_fibonacci_level": self.nearest_fibonacci_level,
        }


@dataclass(frozen=True)
class AltuninaTrendContext:
    candle_count: int
    swing_points: tuple[SwingPoint, ...]
    price_legs: tuple[PriceLeg, ...]
    structure_direction: AltuninaStructureDirection
    trend_line: TrendLineSummary
    trend_duration: TrendDurationSummary
    trend_strength_score: float
    trend_consistency_score: float
    trend_progress_score: float
    impulse_correction: ImpulseCorrectionSummary
    evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    summary: dict[str, float | int | str]

    def to_dict(self) -> dict[str, object]:
        return {
            "candle_count": self.candle_count,
            "swing_points": [item.to_dict() for item in self.swing_points],
            "price_legs": [item.to_dict() for item in self.price_legs],
            "structure_direction": self.structure_direction.value,
            "trend_line": self.trend_line.to_dict(),
            "trend_duration": self.trend_duration.to_dict(),
            "trend_strength_score": float(self.trend_strength_score),
            "trend_consistency_score": float(self.trend_consistency_score),
            "trend_progress_score": float(self.trend_progress_score),
            "impulse_correction": self.impulse_correction.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "reason_codes": list(self.reason_codes),
            "summary": dict(self.summary),
        }


_EVIDENCE: dict[str, tuple[str, float]] = {
    "ALTUNINA_INSUFFICIENT_SWING_POINTS": ("Too few swing points for structural confirmation", 0.0),
    "ALTUNINA_PRICE_LEGS_BUILT": ("Price legs were built from normalized swing points", 0.0),
    "ALTUNINA_STRUCTURE_UNCLEAR": ("Swing structure is unavailable or unclear", 0.0),
    "ALTUNINA_BULLISH_STRUCTURE": ("Every material swing high and low rises", 0.20),
    "ALTUNINA_BEARISH_STRUCTURE": ("Every material swing high and low falls", -0.20),
    "ALTUNINA_SIDEWAYS_STRUCTURE": ("Swing sequences do not establish directional structure", 0.0),
    "ALTUNINA_TREND_NOT_CONFIRMED": ("Directional trend is not structurally confirmed", 0.0),
    "ALTUNINA_TREND_WEAK": ("Derived structural trend measures are weak", 0.0),
    "ALTUNINA_TREND_STRONG": ("Derived structural trend measures are strong", 0.10),
    "ALTUNINA_BULLISH_IMPULSE_DOMINANT": ("Upward impulse movement dominates", 0.15),
    "ALTUNINA_BEARISH_IMPULSE_DOMINANT": ("Downward impulse movement dominates", -0.15),
    "ALTUNINA_CORRECTION_WITHOUT_STRUCTURE_BREAK": ("Correction stays within the book limit and preserves its structural pivot", 0.0),
    "ALTUNINA_DEEP_PULLBACK": ("Pullback is above the one-half retracement level", 0.0),
    "ALTUNINA_SHALLOW_PULLBACK": ("Pullback is at or below the 38 percent retracement level", 0.03),
    "ALTUNINA_PULLBACK_BREAKS_STRUCTURE": ("Pullback exceeds the book limit or breaches its structural pivot", 0.0),
    "ALTUNINA_TREND_PROGRESS_CONFIRMED": ("Derived close-to-close directional progress is confirmed", 0.08),
    "ALTUNINA_LOW_DIRECTIONAL_PROGRESS": ("Derived directional progress across the period is low", 0.0),
    "ALTUNINA_STRUCTURE_CONFLICT": ("Leg balance conflicts with classified swing structure", 0.0),
}


_BOOK_BASED_CODES = {
    "ALTUNINA_TREND_NOT_CONFIRMED",
    "ALTUNINA_CORRECTION_WITHOUT_STRUCTURE_BREAK",
    "ALTUNINA_DEEP_PULLBACK",
    "ALTUNINA_SHALLOW_PULLBACK",
    "ALTUNINA_PULLBACK_BREAKS_STRUCTURE",
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _evidence(code: str, direction_sign: int = 1, **metadata: Any) -> EngineTrendEvidence:
    description, contribution = _EVIDENCE[code]
    if code in {
        "ALTUNINA_TREND_STRONG",
        "ALTUNINA_SHALLOW_PULLBACK",
        "ALTUNINA_TREND_PROGRESS_CONFIRMED",
    }:
        contribution *= direction_sign
    origin = BOOK_RULE if code in _BOOK_BASED_CODES else DERIVED_HEURISTIC
    enriched_metadata = {
        "method_origin": origin,
        "contribution_origin": DERIVED_HEURISTIC,
        **metadata,
    }
    return EngineTrendEvidence(
        BookSource.ALTUNINA,
        code,
        description,
        contribution,
        enriched_metadata,
    )


def detect_swing_points(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    lookback: int = 1,
) -> tuple[SwingPoint, ...]:
    if lookback < 1:
        raise ValueError("lookback must be at least one")
    if len(candles) < lookback * 2 + 1:
        return ()
    points: list[SwingPoint] = []
    for index in range(lookback, len(candles) - lookback):
        candle = candles[index]
        neighbors = candles[index - lookback:index] + candles[index + 1:index + lookback + 1]
        if all(candle.low < item.low for item in neighbors):
            points.append(SwingPoint(index, candle.timestamp, candle.low, SwingPointType.LOW))
        if all(candle.high > item.high for item in neighbors):
            points.append(SwingPoint(index, candle.timestamp, candle.high, SwingPointType.HIGH))
    return tuple(points)


def normalize_swing_points(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
) -> tuple[SwingPoint, ...]:
    """Return alternating pivots, retaining the more extreme consecutive pivot."""

    ordered = sorted(
        swing_points,
        key=lambda item: (
            item.index,
            0 if item.point_type is SwingPointType.LOW else 1,
        ),
    )
    normalized: list[SwingPoint] = []
    for candidate in ordered:
        if normalized and candidate.index == normalized[-1].index:
            if len(normalized) > 1 and candidate.point_type is not normalized[-2].point_type:
                normalized[-1] = candidate
            continue
        if not normalized or candidate.point_type is not normalized[-1].point_type:
            normalized.append(candidate)
            continue
        previous = normalized[-1]
        more_extreme = (
            candidate.price > previous.price
            if candidate.point_type is SwingPointType.HIGH
            else candidate.price < previous.price
        )
        if more_extreme:
            normalized[-1] = candidate
    return tuple(normalized)


def build_price_legs(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
) -> tuple[PriceLeg, ...]:
    ordered = sorted(
        swing_points,
        key=lambda item: (
            item.index,
            0 if item.point_type is SwingPointType.LOW else 1,
        ),
    )
    legs: list[PriceLeg] = []
    for start, end in zip(ordered, ordered[1:]):
        signed_change = end.price - start.price
        direction = (
            PriceLegDirection.UP
            if signed_change > 0
            else PriceLegDirection.DOWN
            if signed_change < 0
            else PriceLegDirection.FLAT
        )
        absolute_change = abs(signed_change)
        relative_change = absolute_change / start.price if start.price != 0 else 0.0
        legs.append(
            PriceLeg(
                start,
                end,
                direction,
                absolute_change,
                relative_change,
                end.index - start.index,
            )
        )
    return tuple(legs)


def _material_change(first: float, last: float) -> int:
    scale = max(abs(first), abs(last), 1.0)
    delta = last - first
    if abs(delta) <= scale * STRUCTURE_TOLERANCE_RATIO:
        return 0
    return 1 if delta > 0 else -1


def _sequence_direction(values: list[float]) -> int:
    changes = [_material_change(first, last) for first, last in zip(values, values[1:])]
    if changes and all(change == 1 for change in changes):
        return 1
    if changes and all(change == -1 for change in changes):
        return -1
    return 0


def classify_structure_direction(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
) -> AltuninaStructureDirection:
    highs = [item.price for item in swing_points if item.point_type is SwingPointType.HIGH]
    lows = [item.price for item in swing_points if item.point_type is SwingPointType.LOW]
    if len(highs) < 2 or len(lows) < 2:
        return AltuninaStructureDirection.UNCLEAR_STRUCTURE
    high_direction = _sequence_direction(highs)
    low_direction = _sequence_direction(lows)
    if high_direction == low_direction == 1:
        return AltuninaStructureDirection.BULLISH_STRUCTURE
    if high_direction == low_direction == -1:
        return AltuninaStructureDirection.BEARISH_STRUCTURE
    return AltuninaStructureDirection.SIDEWAYS_STRUCTURE


def build_trend_line(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
    structure_direction: AltuninaStructureDirection,
) -> TrendLineSummary:
    anchor_type = (
        SwingPointType.LOW
        if structure_direction is AltuninaStructureDirection.BULLISH_STRUCTURE
        else SwingPointType.HIGH
        if structure_direction is AltuninaStructureDirection.BEARISH_STRUCTURE
        else None
    )
    anchors = [item for item in swing_points if item.point_type is anchor_type]
    if len(anchors) < 2:
        return TrendLineSummary(False, PriceLegDirection.FLAT, None, None, 0.0, len(anchors))
    start, end = anchors[0], anchors[-1]
    span = end.index - start.index
    slope = (end.price - start.price) / span if span else 0.0
    direction = (
        PriceLegDirection.UP
        if slope > 0
        else PriceLegDirection.DOWN
        if slope < 0
        else PriceLegDirection.FLAT
    )
    return TrendLineSummary(True, direction, start, end, slope, len(anchors))


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def classify_trend_duration(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> TrendDurationSummary:
    if len(candles) < 2:
        return TrendDurationSummary(None, TrendDurationClass.UNKNOWN, TrendHierarchyRole.UNKNOWN)
    start = _parse_timestamp(candles[0].timestamp)
    end = _parse_timestamp(candles[-1].timestamp)
    if start is None or end is None:
        return TrendDurationSummary(None, TrendDurationClass.UNKNOWN, TrendHierarchyRole.UNKNOWN)
    try:
        elapsed = end - start
    except TypeError:
        return TrendDurationSummary(None, TrendDurationClass.UNKNOWN, TrendHierarchyRole.UNKNOWN)
    if elapsed.total_seconds() < 0:
        return TrendDurationSummary(None, TrendDurationClass.UNKNOWN, TrendHierarchyRole.UNKNOWN)
    days = elapsed.total_seconds() / 86_400
    duration_class = (
        TrendDurationClass.MULTI_YEAR
        if days >= 365
        else TrendDurationClass.MONTHLY_SCALE
        if days >= 31
        else TrendDurationClass.SUB_MONTH_SCALE
    )
    hierarchy_role = (
        TrendHierarchyRole.PRIMARY
        if days >= 365
        else TrendHierarchyRole.INTERMEDIATE
        if 31 <= days <= 183
        else TrendHierarchyRole.MINOR
        if 7 <= days < 31
        else TrendHierarchyRole.UNKNOWN
    )
    return TrendDurationSummary(days, duration_class, hierarchy_role)


def _nearest_fibonacci_level(depth: float, correction_count: int) -> float | None:
    if not correction_count:
        return None
    return min(FIBONACCI_PULLBACK_LEVELS, key=lambda level: abs(depth - level))


def analyze_impulse_correction(
    price_legs: tuple[PriceLeg, ...] | list[PriceLeg],
    structure_direction: AltuninaStructureDirection,
) -> ImpulseCorrectionSummary:
    bullish_impulse = bearish_impulse = bullish_correction = bearish_correction = 0.0
    depths: list[float] = []
    previous_impulse = 0.0
    previous_pivot: float | None = None
    pivot_breached = False
    dominant = PriceLegDirection.FLAT
    if structure_direction is AltuninaStructureDirection.BULLISH_STRUCTURE:
        dominant = PriceLegDirection.UP
        for leg in price_legs:
            if leg.direction is PriceLegDirection.UP:
                bullish_impulse += leg.absolute_change
                previous_impulse = leg.absolute_change
                previous_pivot = leg.start.price
            elif leg.direction is PriceLegDirection.DOWN:
                bullish_correction += leg.absolute_change
                depth = leg.absolute_change / previous_impulse if previous_impulse else 0.0
                depths.append(_clamp(depth, 0.0, 10.0))
                if previous_pivot is not None and leg.end.price <= previous_pivot:
                    pivot_breached = True
    elif structure_direction is AltuninaStructureDirection.BEARISH_STRUCTURE:
        dominant = PriceLegDirection.DOWN
        for leg in price_legs:
            if leg.direction is PriceLegDirection.DOWN:
                bearish_impulse += leg.absolute_change
                previous_impulse = leg.absolute_change
                previous_pivot = leg.start.price
            elif leg.direction is PriceLegDirection.UP:
                bearish_correction += leg.absolute_change
                depth = leg.absolute_change / previous_impulse if previous_impulse else 0.0
                depths.append(_clamp(depth, 0.0, 10.0))
                if previous_pivot is not None and leg.end.price >= previous_pivot:
                    pivot_breached = True
    maximum = max(depths, default=0.0)
    return ImpulseCorrectionSummary(
        bullish_impulse,
        bearish_impulse,
        bullish_correction,
        bearish_correction,
        dominant,
        maximum,
        sum(depths) / len(depths) if depths else 0.0,
        len(depths),
        ALTUNINA_CORRECTION_LIMIT,
        maximum > ALTUNINA_CORRECTION_LIMIT
        and not isclose(maximum, ALTUNINA_CORRECTION_LIMIT, rel_tol=1e-9, abs_tol=1e-12),
        pivot_breached,
        _nearest_fibonacci_level(maximum, len(depths)),
    )


def analyze_altunina_trend_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> AltuninaTrendContext:
    raw_swings = detect_swing_points(candles)
    swings = normalize_swing_points(raw_swings)
    legs = build_price_legs(swings)
    structure = classify_structure_direction(swings)
    trend_line = build_trend_line(swings, structure)
    trend_duration = classify_trend_duration(candles)
    impulse = analyze_impulse_correction(legs, structure)
    directional = structure in {
        AltuninaStructureDirection.BULLISH_STRUCTURE,
        AltuninaStructureDirection.BEARISH_STRUCTURE,
    }
    sign = 1 if structure is AltuninaStructureDirection.BULLISH_STRUCTURE else -1
    impulse_total = impulse.bullish_impulse_total + impulse.bearish_impulse_total
    total_movement = sum(item.absolute_change for item in legs)
    strength = _clamp(impulse_total / total_movement if total_movement else 0.0)
    dominant_leg_count = (
        sum(item.direction is impulse.dominant_impulse_direction for item in legs)
        if directional
        else 0
    )
    consistency = _clamp(dominant_leg_count / len(legs) if legs else 0.0)
    period_range = max((item.high for item in candles), default=0.0) - min(
        (item.low for item in candles), default=0.0
    )
    raw_progress = (
        (candles[-1].close - candles[0].close) * sign
        if candles and directional
        else 0.0
    )
    progress = _clamp(raw_progress / period_range if period_range else 0.0)

    items: list[EngineTrendEvidence] = []
    if len(swings) < 4:
        items.append(
            _evidence(
                "ALTUNINA_INSUFFICIENT_SWING_POINTS",
                raw_swing_count=len(raw_swings),
                normalized_swing_count=len(swings),
            )
        )
    if legs:
        items.append(_evidence("ALTUNINA_PRICE_LEGS_BUILT", leg_count=len(legs)))
    structure_codes = {
        AltuninaStructureDirection.BULLISH_STRUCTURE: "ALTUNINA_BULLISH_STRUCTURE",
        AltuninaStructureDirection.BEARISH_STRUCTURE: "ALTUNINA_BEARISH_STRUCTURE",
        AltuninaStructureDirection.SIDEWAYS_STRUCTURE: "ALTUNINA_SIDEWAYS_STRUCTURE",
        AltuninaStructureDirection.UNCLEAR_STRUCTURE: "ALTUNINA_STRUCTURE_UNCLEAR",
    }
    items.append(_evidence(structure_codes[structure]))
    if not directional:
        items.append(_evidence("ALTUNINA_TREND_NOT_CONFIRMED"))
    else:
        dominant_code = (
            "ALTUNINA_BULLISH_IMPULSE_DOMINANT"
            if sign > 0
            else "ALTUNINA_BEARISH_IMPULSE_DOMINANT"
        )
        if impulse_total > 0:
            items.append(_evidence(dominant_code, impulse_total=impulse_total))
        strong = strength >= 0.60 and consistency >= 0.50
        items.append(
            _evidence(
                "ALTUNINA_TREND_STRONG" if strong else "ALTUNINA_TREND_WEAK",
                sign,
                strength=strength,
                consistency=consistency,
            )
        )
        if progress >= 0.20:
            items.append(
                _evidence("ALTUNINA_TREND_PROGRESS_CONFIRMED", sign, progress=progress)
            )
        else:
            items.append(_evidence("ALTUNINA_LOW_DIRECTIONAL_PROGRESS", progress=progress))
        if impulse.correction_count:
            depth = impulse.max_pullback_depth
            pullback_metadata = {
                "depth": depth,
                "correction_limit": impulse.correction_limit,
                "nearest_fibonacci_level": impulse.nearest_fibonacci_level,
                "structural_pivot_breached": impulse.structural_pivot_breached,
            }
            if impulse.correction_limit_breached or impulse.structural_pivot_breached:
                items.append(
                    _evidence("ALTUNINA_PULLBACK_BREAKS_STRUCTURE", **pullback_metadata)
                )
            else:
                items.append(
                    _evidence(
                        "ALTUNINA_CORRECTION_WITHOUT_STRUCTURE_BREAK",
                        **pullback_metadata,
                    )
                )
                if depth <= FIBONACCI_PULLBACK_LEVELS[0]:
                    items.append(
                        _evidence("ALTUNINA_SHALLOW_PULLBACK", sign, **pullback_metadata)
                    )
                elif depth > FIBONACCI_PULLBACK_LEVELS[1]:
                    items.append(_evidence("ALTUNINA_DEEP_PULLBACK", **pullback_metadata))
        opposite_total = sum(
            item.absolute_change
            for item in legs
            if item.direction
            not in {impulse.dominant_impulse_direction, PriceLegDirection.FLAT}
        )
        if opposite_total > impulse_total:
            items.append(
                _evidence(
                    "ALTUNINA_STRUCTURE_CONFLICT",
                    opposite_total=opposite_total,
                    impulse_total=impulse_total,
                )
            )

    evidence = tuple(items)
    summary: dict[str, float | int | str] = {
        "raw_swing_count": len(raw_swings),
        "swing_count": len(swings),
        "leg_count": len(legs),
        "structure_direction": structure.value,
        "total_movement": total_movement,
        "directional_progress": progress,
        "score_method_origin": DERIVED_HEURISTIC,
        "swing_method_origin": DERIVED_HEURISTIC,
    }
    return AltuninaTrendContext(
        len(candles),
        swings,
        legs,
        structure,
        trend_line,
        trend_duration,
        strength,
        consistency,
        progress,
        impulse,
        evidence,
        tuple(dict.fromkeys(item.code for item in evidence)),
        summary,
    )
