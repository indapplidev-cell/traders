"""Altunina trend, impulse, correction, and pullback evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendCandle,
    EngineTrendEvidence,
)


STRUCTURE_TOLERANCE_RATIO = 0.001


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
class ImpulseCorrectionSummary:
    bullish_impulse_total: float
    bearish_impulse_total: float
    bullish_correction_total: float
    bearish_correction_total: float
    dominant_impulse_direction: PriceLegDirection
    max_pullback_depth: float
    average_pullback_depth: float
    correction_count: int

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
        }


@dataclass(frozen=True)
class AltuninaTrendContext:
    candle_count: int
    swing_points: tuple[SwingPoint, ...]
    price_legs: tuple[PriceLeg, ...]
    structure_direction: AltuninaStructureDirection
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
    "ALTUNINA_PRICE_LEGS_BUILT": ("Price legs were built from adjacent swing points", 0.0),
    "ALTUNINA_STRUCTURE_UNCLEAR": ("Swing structure is unavailable or unclear", 0.0),
    "ALTUNINA_BULLISH_STRUCTURE": ("Higher swing highs and lows form bullish structure", 0.20),
    "ALTUNINA_BEARISH_STRUCTURE": ("Lower swing highs and lows form bearish structure", -0.20),
    "ALTUNINA_SIDEWAYS_STRUCTURE": ("Swing sequences do not establish directional structure", 0.0),
    "ALTUNINA_TREND_NOT_CONFIRMED": ("Directional trend is not structurally confirmed", 0.0),
    "ALTUNINA_TREND_WEAK": ("Structural trend measures are weak", 0.0),
    "ALTUNINA_TREND_STRONG": ("Structural trend measures are strong", 0.10),
    "ALTUNINA_BULLISH_IMPULSE_DOMINANT": ("Upward impulse movement dominates", 0.15),
    "ALTUNINA_BEARISH_IMPULSE_DOMINANT": ("Downward impulse movement dominates", -0.15),
    "ALTUNINA_CORRECTION_WITHOUT_STRUCTURE_BREAK": ("Correction remains within the preceding impulse", 0.0),
    "ALTUNINA_DEEP_PULLBACK": ("Pullback is deep relative to the preceding impulse", 0.0),
    "ALTUNINA_SHALLOW_PULLBACK": ("Pullback is shallow relative to the preceding impulse", 0.03),
    "ALTUNINA_PULLBACK_BREAKS_STRUCTURE": ("Pullback exceeds the preceding impulse", 0.0),
    "ALTUNINA_TREND_PROGRESS_CONFIRMED": ("Close-to-close directional progress is confirmed", 0.08),
    "ALTUNINA_LOW_DIRECTIONAL_PROGRESS": ("Directional progress across the period is low", 0.0),
    "ALTUNINA_STRUCTURE_CONFLICT": ("Leg balance conflicts with classified swing structure", 0.0),
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _evidence(code: str, direction_sign: int = 1, **metadata: Any) -> EngineTrendEvidence:
    description, contribution = _EVIDENCE[code]
    if code in {"ALTUNINA_TREND_STRONG", "ALTUNINA_SHALLOW_PULLBACK", "ALTUNINA_TREND_PROGRESS_CONFIRMED"}:
        contribution *= direction_sign
    return EngineTrendEvidence(BookSource.ALTUNINA, code, description, contribution, metadata)


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
        is_low = all(candle.low < item.low for item in neighbors)
        is_high = all(candle.high > item.high for item in neighbors)
        if is_low:
            points.append(SwingPoint(index, candle.timestamp, candle.low, SwingPointType.LOW))
        if is_high:
            points.append(SwingPoint(index, candle.timestamp, candle.high, SwingPointType.HIGH))
    return tuple(points)


def build_price_legs(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
) -> tuple[PriceLeg, ...]:
    ordered = sorted(swing_points, key=lambda item: (item.index, 0 if item.point_type is SwingPointType.LOW else 1))
    legs: list[PriceLeg] = []
    for start, end in zip(ordered, ordered[1:]):
        signed_change = end.price - start.price
        direction = PriceLegDirection.UP if signed_change > 0 else PriceLegDirection.DOWN if signed_change < 0 else PriceLegDirection.FLAT
        absolute_change = abs(signed_change)
        relative_change = absolute_change / start.price if start.price != 0 else 0.0
        legs.append(PriceLeg(start, end, direction, absolute_change, relative_change, end.index - start.index))
    return tuple(legs)


def _material_change(first: float, last: float) -> int:
    scale = max(abs(first), abs(last), 1.0)
    delta = last - first
    if abs(delta) <= scale * STRUCTURE_TOLERANCE_RATIO:
        return 0
    return 1 if delta > 0 else -1


def classify_structure_direction(
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint],
) -> AltuninaStructureDirection:
    highs = [item.price for item in swing_points if item.point_type is SwingPointType.HIGH]
    lows = [item.price for item in swing_points if item.point_type is SwingPointType.LOW]
    if len(highs) < 2 or len(lows) < 2:
        return AltuninaStructureDirection.UNCLEAR_STRUCTURE
    high_change = _material_change(highs[0], highs[-1])
    low_change = _material_change(lows[0], lows[-1])
    if high_change == low_change == 1:
        return AltuninaStructureDirection.BULLISH_STRUCTURE
    if high_change == low_change == -1:
        return AltuninaStructureDirection.BEARISH_STRUCTURE
    return AltuninaStructureDirection.SIDEWAYS_STRUCTURE


def analyze_impulse_correction(
    price_legs: tuple[PriceLeg, ...] | list[PriceLeg],
    structure_direction: AltuninaStructureDirection,
) -> ImpulseCorrectionSummary:
    bullish_impulse = bearish_impulse = bullish_correction = bearish_correction = 0.0
    depths: list[float] = []
    previous_impulse = 0.0
    dominant = PriceLegDirection.FLAT
    if structure_direction is AltuninaStructureDirection.BULLISH_STRUCTURE:
        dominant = PriceLegDirection.UP
        for leg in price_legs:
            if leg.direction is PriceLegDirection.UP:
                bullish_impulse += leg.absolute_change
                previous_impulse = leg.absolute_change
            elif leg.direction is PriceLegDirection.DOWN:
                bullish_correction += leg.absolute_change
                depths.append(_clamp(leg.absolute_change / previous_impulse if previous_impulse else 0.0, 0.0, 10.0))
    elif structure_direction is AltuninaStructureDirection.BEARISH_STRUCTURE:
        dominant = PriceLegDirection.DOWN
        for leg in price_legs:
            if leg.direction is PriceLegDirection.DOWN:
                bearish_impulse += leg.absolute_change
                previous_impulse = leg.absolute_change
            elif leg.direction is PriceLegDirection.UP:
                bearish_correction += leg.absolute_change
                depths.append(_clamp(leg.absolute_change / previous_impulse if previous_impulse else 0.0, 0.0, 10.0))
    return ImpulseCorrectionSummary(
        bullish_impulse, bearish_impulse, bullish_correction, bearish_correction,
        dominant, max(depths, default=0.0), sum(depths) / len(depths) if depths else 0.0, len(depths),
    )


def analyze_altunina_trend_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> AltuninaTrendContext:
    swings = detect_swing_points(candles)
    legs = build_price_legs(swings)
    structure = classify_structure_direction(swings)
    impulse = analyze_impulse_correction(legs, structure)
    directional = structure in {AltuninaStructureDirection.BULLISH_STRUCTURE, AltuninaStructureDirection.BEARISH_STRUCTURE}
    sign = 1 if structure is AltuninaStructureDirection.BULLISH_STRUCTURE else -1
    impulse_total = impulse.bullish_impulse_total + impulse.bearish_impulse_total
    total_movement = sum(item.absolute_change for item in legs)
    strength = _clamp(impulse_total / total_movement if total_movement else 0.0)
    dominant_leg_count = sum(item.direction is impulse.dominant_impulse_direction for item in legs) if directional else 0
    consistency = _clamp(dominant_leg_count / len(legs) if legs else 0.0)
    period_range = max((item.high for item in candles), default=0.0) - min((item.low for item in candles), default=0.0)
    raw_progress = ((candles[-1].close - candles[0].close) * sign) if candles and directional else 0.0
    progress = _clamp(raw_progress / period_range if period_range else 0.0)

    items: list[EngineTrendEvidence] = []
    if len(swings) < 4:
        items.append(_evidence("ALTUNINA_INSUFFICIENT_SWING_POINTS", swing_count=len(swings)))
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
        dominant_code = "ALTUNINA_BULLISH_IMPULSE_DOMINANT" if sign > 0 else "ALTUNINA_BEARISH_IMPULSE_DOMINANT"
        if impulse_total > 0:
            items.append(_evidence(dominant_code, impulse_total=impulse_total))
        strong = strength >= 0.60 and consistency >= 0.50
        items.append(_evidence("ALTUNINA_TREND_STRONG" if strong else "ALTUNINA_TREND_WEAK", sign, strength=strength, consistency=consistency))
        if progress >= 0.20:
            items.append(_evidence("ALTUNINA_TREND_PROGRESS_CONFIRMED", sign, progress=progress))
        else:
            items.append(_evidence("ALTUNINA_LOW_DIRECTIONAL_PROGRESS", progress=progress))
        if impulse.correction_count:
            depth = impulse.max_pullback_depth
            if depth > 1.0:
                items.append(_evidence("ALTUNINA_PULLBACK_BREAKS_STRUCTURE", depth=depth))
            else:
                items.append(_evidence("ALTUNINA_CORRECTION_WITHOUT_STRUCTURE_BREAK", depth=depth))
                pullback_code = "ALTUNINA_SHALLOW_PULLBACK" if depth <= 0.50 else "ALTUNINA_DEEP_PULLBACK"
                items.append(_evidence(pullback_code, sign, depth=depth))
        opposite_total = sum(item.absolute_change for item in legs if item.direction not in {impulse.dominant_impulse_direction, PriceLegDirection.FLAT})
        if opposite_total > impulse_total:
            items.append(_evidence("ALTUNINA_STRUCTURE_CONFLICT", opposite_total=opposite_total, impulse_total=impulse_total))

    evidence = tuple(items)
    summary: dict[str, float | int | str] = {
        "swing_count": len(swings), "leg_count": len(legs), "structure_direction": structure.value,
        "total_movement": total_movement, "directional_progress": progress,
    }
    return AltuninaTrendContext(
        len(candles), swings, legs, structure, strength, consistency, progress,
        impulse, evidence, tuple(dict.fromkeys(item.code for item in evidence)), summary,
    )
