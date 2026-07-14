"""Schwager range, level-zone, breakout, and polarity evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendCandle,
    EngineTrendEvidence,
)
from app.market_reader.engine_trend.altunina_trend_context import (
    SwingPoint,
    SwingPointType,
    detect_swing_points,
)


ZONE_CLUSTER_TOLERANCE_RATIO = 0.003
MIN_ZONE_TOUCHES = 2
MIN_RANGE_TOUCHES = 4
MIN_INSIDE_CLOSE_RATIO = 0.60
MIN_RANGE_WIDTH_RATIO = 0.003
MAX_RANGE_WIDTH_RATIO = 0.20
BREAKOUT_BUFFER_RATIO = 0.001
FOLLOW_THROUGH_LOOKAHEAD = 2
FALSE_BREAKOUT_LOOKAHEAD = 3
RETEST_LOOKAHEAD = 5
MIN_RANGE_DURATION = 4
MIN_BOUNDARY_ALTERNATIONS = 2
MIN_CONFIRMATION_CLOSES = 3
BREAKOUT_CONFIRMATION_DISTANCE_RATIO = 0.005
FALSE_BREAKOUT_TIME_LOOKAHEAD = 4
RETEST_DEPARTURE_RATIO = 0.003


class ZoneType(str, Enum):
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"


class BreakoutDirection(str, Enum):
    UPWARD = "UPWARD"
    DOWNWARD = "DOWNWARD"
    NONE = "NONE"


class BreakoutConfirmationStatus(str, Enum):
    NO_BREAKOUT = "NO_BREAKOUT"
    ATTEMPT = "ATTEMPT"
    CONFIRMED = "CONFIRMED"
    NO_FOLLOW_THROUGH = "NO_FOLLOW_THROUGH"
    FALSE_BREAKOUT = "FALSE_BREAKOUT"
    RETEST_HELD = "RETEST_HELD"
    RETEST_FAILED = "RETEST_FAILED"
    RETURNED_TO_RANGE = "RETURNED_TO_RANGE"


class BreakoutConfirmationMethod(str, Enum):
    NONE = "NONE"
    CLOSE_COUNT = "CLOSE_COUNT"
    DISTANCE = "DISTANCE"
    CLOSE_COUNT_AND_DISTANCE = "CLOSE_COUNT_AND_DISTANCE"


class FalseBreakoutConfirmationStatus(str, Enum):
    NONE = "NONE"
    RETURNED_INSIDE = "RETURNED_INSIDE"
    INITIAL_PRICE_CONFIRMATION = "INITIAL_PRICE_CONFIRMATION"
    STRONG_PRICE_CONFIRMATION = "STRONG_PRICE_CONFIRMATION"
    TIME_CONFIRMATION = "TIME_CONFIRMATION"
    INVALIDATED = "INVALIDATED"


class PolarityFlipStatus(str, Enum):
    NONE = "NONE"
    RESISTANCE_TO_SUPPORT = "RESISTANCE_TO_SUPPORT"
    SUPPORT_TO_RESISTANCE = "SUPPORT_TO_RESISTANCE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SupportResistanceZone:
    zone_type: ZoneType
    lower_price: float
    upper_price: float
    mid_price: float
    touch_count: int
    source_indexes: tuple[int, ...]
    zone_width: float
    zone_width_ratio: float
    formed_at_index: int = 0
    first_touch_index: int = 0
    last_touch_index: int = 0
    source_point_types: tuple[SwingPointType, ...] = ()
    original_zone_type: ZoneType | None = None
    current_zone_type: ZoneType | None = None
    role_changed_at_index: int | None = None
    is_significant_single_extreme: bool = False
    positional_zone_type: ZoneType | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "zone_type": self.zone_type.value,
            "lower_price": float(self.lower_price),
            "upper_price": float(self.upper_price),
            "mid_price": float(self.mid_price),
            "touch_count": self.touch_count,
            "source_indexes": list(self.source_indexes),
            "zone_width": float(self.zone_width),
            "zone_width_ratio": float(self.zone_width_ratio),
            "formed_at_index": self.formed_at_index,
            "first_touch_index": self.first_touch_index,
            "last_touch_index": self.last_touch_index,
            "source_point_types": [item.value for item in self.source_point_types],
            "original_zone_type": (self.original_zone_type or self.zone_type).value,
            "current_zone_type": (self.current_zone_type or self.zone_type).value,
            "role_changed_at_index": self.role_changed_at_index,
            "is_significant_single_extreme": self.is_significant_single_extreme,
            "positional_zone_type": (self.positional_zone_type or self.zone_type).value,
        }


@dataclass(frozen=True)
class TradingRange:
    support_zone: SupportResistanceZone | None
    resistance_zone: SupportResistanceZone | None
    is_detected: bool
    lower_boundary: float | None
    upper_boundary: float | None
    midline: float | None
    width: float
    width_ratio: float
    touch_count: int
    inside_close_ratio: float
    formed_at_index: int = 0
    first_touch_index: int = 0
    duration_candles: int = 0
    boundary_alternation_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "support_zone": self.support_zone.to_dict() if self.support_zone else None,
            "resistance_zone": self.resistance_zone.to_dict() if self.resistance_zone else None,
            "is_detected": self.is_detected,
            "lower_boundary": self.lower_boundary,
            "upper_boundary": self.upper_boundary,
            "midline": self.midline,
            "width": float(self.width),
            "width_ratio": float(self.width_ratio),
            "touch_count": self.touch_count,
            "inside_close_ratio": float(self.inside_close_ratio),
            "formed_at_index": self.formed_at_index,
            "first_touch_index": self.first_touch_index,
            "duration_candles": self.duration_candles,
            "boundary_alternation_count": self.boundary_alternation_count,
        }


@dataclass(frozen=True)
class BreakoutContext:
    direction: BreakoutDirection
    status: BreakoutConfirmationStatus
    breakout_index: int | None
    boundary_price: float | None
    breakout_close: float | None
    distance_ratio: float
    returned_to_range: bool
    follow_through_count: int
    evidence: tuple[EngineTrendEvidence, ...]
    analysis_start_index: int = 0
    confirmation_method: BreakoutConfirmationMethod = BreakoutConfirmationMethod.NONE
    confirmation_close_count: int = 0
    extreme_index: int | None = None
    extreme_price: float | None = None
    maximum_distance_ratio: float = 0.0
    return_index: int | None = None
    return_depth_ratio: float = 0.0
    reversal_candle_count: int = 0
    false_breakout_confirmation: FalseBreakoutConfirmationStatus = FalseBreakoutConfirmationStatus.NONE
    false_breakout_invalidated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "direction": self.direction.value,
            "status": self.status.value,
            "breakout_index": self.breakout_index,
            "boundary_price": self.boundary_price,
            "breakout_close": self.breakout_close,
            "distance_ratio": float(self.distance_ratio),
            "returned_to_range": self.returned_to_range,
            "follow_through_count": self.follow_through_count,
            "evidence": [item.to_dict() for item in self.evidence],
            "analysis_start_index": self.analysis_start_index,
            "confirmation_method": self.confirmation_method.value,
            "confirmation_close_count": self.confirmation_close_count,
            "extreme_index": self.extreme_index,
            "extreme_price": self.extreme_price,
            "maximum_distance_ratio": float(self.maximum_distance_ratio),
            "return_index": self.return_index,
            "return_depth_ratio": float(self.return_depth_ratio),
            "reversal_candle_count": self.reversal_candle_count,
            "false_breakout_confirmation": self.false_breakout_confirmation.value,
            "false_breakout_invalidated": self.false_breakout_invalidated,
        }


@dataclass(frozen=True)
class PolarityFlipContext:
    status: PolarityFlipStatus
    source_zone_type: ZoneType | None
    test_index: int | None
    held: bool
    evidence: tuple[EngineTrendEvidence, ...]
    departure_index: int | None = None
    role_changed_at_index: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "source_zone_type": self.source_zone_type.value if self.source_zone_type else None,
            "test_index": self.test_index,
            "held": self.held,
            "evidence": [item.to_dict() for item in self.evidence],
            "departure_index": self.departure_index,
            "role_changed_at_index": self.role_changed_at_index,
        }


@dataclass(frozen=True)
class SchwagerRangeContext:
    candle_count: int
    zones: tuple[SupportResistanceZone, ...]
    trading_range: TradingRange
    breakout_context: BreakoutContext
    polarity_flip_context: PolarityFlipContext
    evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "candle_count": self.candle_count,
            "zones": [item.to_dict() for item in self.zones],
            "trading_range": self.trading_range.to_dict(),
            "breakout_context": self.breakout_context.to_dict(),
            "polarity_flip_context": self.polarity_flip_context.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "reason_codes": list(self.reason_codes),
            "summary": dict(self.summary),
        }


_EVIDENCE: dict[str, tuple[str, float]] = {
    "SCHWAGER_SUPPORT_ZONE_IDENTIFIED": ("Repeated swing lows form a support zone", 0.0),
    "SCHWAGER_RESISTANCE_ZONE_IDENTIFIED": ("Repeated swing highs form a resistance zone", 0.0),
    "SCHWAGER_SUPPORT_ZONE_HELD": ("Support zone has repeated touches", 0.0),
    "SCHWAGER_RESISTANCE_ZONE_HELD": ("Resistance zone has repeated touches", 0.0),
    "SCHWAGER_ZONE_TOO_WIDE": ("A level zone is too wide for stable context", 0.0),
    "SCHWAGER_ZONE_OVERLAP_CONFLICT": ("Support and resistance zones overlap", 0.0),
    "SCHWAGER_INSUFFICIENT_LEVEL_TOUCHES": ("Level touches are insufficient", 0.0),
    "SCHWAGER_TRADING_RANGE_DETECTED": ("Repeated boundaries define a trading range", 0.0),
    "SCHWAGER_PRICE_INSIDE_RANGE": ("Closing prices are commonly inside the range", 0.0),
    "SCHWAGER_RANGE_UPPER_BOUNDARY_HELD": ("The upper range boundary has repeated touches", 0.0),
    "SCHWAGER_RANGE_LOWER_BOUNDARY_HELD": ("The lower range boundary has repeated touches", 0.0),
    "SCHWAGER_RANGE_NOT_CONFIRMED": ("Range conditions are not confirmed", 0.0),
    "SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT": ("Closing price moved above the range boundary", 0.12),
    "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT": ("Closing price moved below the range boundary", -0.12),
    "SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION": ("Boundary movement requires confirmation", 0.0),
    "SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED": ("Closing prices confirm follow-through", 0.08),
    "SCHWAGER_BREAKOUT_NO_FOLLOW_THROUGH": ("Boundary movement lacks follow-through", 0.0),
    "SCHWAGER_BREAKOUT_RETEST_HELD": ("The former boundary held on a retest", 0.0),
    "SCHWAGER_BREAKOUT_RETEST_FAILED": ("The former boundary failed on a retest", 0.0),
    "SCHWAGER_RESISTANCE_TURNED_SUPPORT": ("Former resistance held as support", 0.08),
    "SCHWAGER_SUPPORT_TURNED_RESISTANCE": ("Former support held as resistance", -0.08),
    "SCHWAGER_POLARITY_FLIP_CONFIRMED": ("Boundary polarity flip is confirmed", 0.0),
    "SCHWAGER_POLARITY_FLIP_FAILED": ("Boundary polarity flip failed", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_UP": ("Upward boundary movement returned to the range", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_DOWN": ("Downward boundary movement returned to the range", 0.0),
    "SCHWAGER_PRICE_RETURNED_TO_RANGE": ("Closing price returned inside the range", 0.0),
    "SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED": ("A significant previous extreme defines a potential zone", 0.0),
    "SCHWAGER_RANGE_DURATION_CONFIRMED": ("Range boundaries persisted across a sufficient candle span", 0.0),
    "SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED": ("Price alternated between both range boundaries", 0.0),
    "SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT": ("Multiple closes beyond the boundary confirm the movement", 0.0),
    "SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE": ("Movement depth beyond the boundary confirms the movement", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_INITIAL_CONFIRMATION": ("Price returned to the middle portion of the prior range", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_STRONG_CONFIRMATION": ("Price returned to the far boundary of the prior range", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_TIME_CONFIRMATION": ("Price did not revisit the post-breakout extreme", 0.0),
    "SCHWAGER_FALSE_BREAKOUT_INVALIDATED": ("Price revisited the post-breakout extreme", 0.0),
    "SCHWAGER_POLARITY_RETEST_AWAITING_DEPARTURE": ("Price has not departed far enough for a separate boundary test", 0.0),
}


def _evidence(code: str, contribution_sign: int = 1, **metadata: Any) -> EngineTrendEvidence:
    description, contribution = _EVIDENCE[code]
    if code == "SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED":
        contribution *= contribution_sign
    return EngineTrendEvidence(BookSource.SCHWAGER, code, description, contribution, metadata)


def build_support_resistance_zones(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint] | None = None,
) -> tuple[SupportResistanceZone, ...]:
    points = detect_swing_points(candles) if swing_points is None else tuple(swing_points)
    zones: list[SupportResistanceZone] = []
    ordered = sorted(points, key=lambda item: item.price)
    clusters: list[list[SwingPoint]] = []
    for point in ordered:
        if not clusters:
            clusters.append([point])
            continue
        cluster_mid = sum(item.price for item in clusters[-1]) / len(clusters[-1])
        tolerance = max(abs(cluster_mid), abs(point.price), 1.0) * ZONE_CLUSTER_TOLERANCE_RATIO
        if abs(point.price - cluster_mid) <= tolerance:
            clusters[-1].append(point)
        else:
            clusters.append([point])
    reference_close = candles[-1].close if candles else 0.0
    period_high = max((item.high for item in candles), default=0.0)
    period_low = min((item.low for item in candles), default=0.0)
    for cluster in clusters:
        significant_single = len(cluster) == 1 and cluster[0].price in {period_low, period_high}
        if len(cluster) < MIN_ZONE_TOUCHES and not significant_single:
            continue
        prices = [item.price for item in cluster]
        lower, upper = min(prices), max(prices)
        mid = sum(prices) / len(prices)
        width = upper - lower
        indexes = tuple(sorted(item.index for item in cluster))
        point_types = tuple(item.point_type for item in sorted(cluster, key=lambda item: item.index))
        low_count = sum(item is SwingPointType.LOW for item in point_types)
        high_count = len(point_types) - low_count
        if low_count > high_count:
            zone_type = ZoneType.SUPPORT
        elif high_count > low_count:
            zone_type = ZoneType.RESISTANCE
        else:
            zone_type = ZoneType.SUPPORT if mid <= reference_close else ZoneType.RESISTANCE
        positional_type = ZoneType.SUPPORT if mid <= reference_close else ZoneType.RESISTANCE
        zones.append(SupportResistanceZone(
            zone_type, lower, upper, mid, len(cluster), indexes, width,
            width / abs(mid) if mid else 0.0,
            indexes[-1], indexes[0], indexes[-1], point_types,
            zone_type, zone_type, None, significant_single, positional_type,
        ))
    return tuple(sorted(zones, key=lambda item: (item.mid_price, item.zone_type.value)))


def detect_trading_range(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    zones: tuple[SupportResistanceZone, ...] | list[SupportResistanceZone],
) -> TradingRange:
    supports = sorted((item for item in zones if item.zone_type is ZoneType.SUPPORT and item.touch_count >= MIN_ZONE_TOUCHES), key=lambda item: (-item.touch_count, item.mid_price))
    resistances = sorted((item for item in zones if item.zone_type is ZoneType.RESISTANCE and item.touch_count >= MIN_ZONE_TOUCHES), key=lambda item: (-item.touch_count, -item.mid_price))
    support = supports[0] if supports else None
    resistance = next((item for item in resistances if support and item.mid_price > support.mid_price), resistances[0] if resistances else None)
    if support is None or resistance is None:
        return TradingRange(support, resistance, False, None, None, None, 0.0, 0.0, (support.touch_count if support else 0) + (resistance.touch_count if resistance else 0), 0.0)
    lower, upper = support.lower_price, resistance.upper_price
    width = upper - lower
    midline = (lower + upper) / 2.0
    width_ratio = width / abs(midline) if midline else 0.0
    touch_events = sorted(
        [(index, "support") for index in support.source_indexes]
        + [(index, "resistance") for index in resistance.source_indexes]
    )
    alternations = sum(left[1] != right[1] for left, right in zip(touch_events, touch_events[1:]))
    first_touch = min((item[0] for item in touch_events), default=0)
    formed_at = max(
        support.formed_at_index,
        resistance.formed_at_index,
        max(support.source_indexes, default=0),
        max(resistance.source_indexes, default=0),
    )
    formation_window = candles[first_touch:formed_at + 1]
    inside_count = sum(lower <= item.close <= upper for item in formation_window)
    inside_ratio = inside_count / len(formation_window) if formation_window else 0.0
    duration = formed_at - first_touch + 1
    touches = support.touch_count + resistance.touch_count
    separated = resistance.mid_price > support.mid_price and support.upper_price < resistance.lower_price
    detected = (
        separated and touches >= MIN_RANGE_TOUCHES
        and inside_ratio >= MIN_INSIDE_CLOSE_RATIO
        and MIN_RANGE_WIDTH_RATIO <= width_ratio <= MAX_RANGE_WIDTH_RATIO
        and duration >= MIN_RANGE_DURATION
        and alternations >= MIN_BOUNDARY_ALTERNATIONS
    )
    return TradingRange(
        support, resistance, detected, lower, upper, midline, width,
        width_ratio, touches, inside_ratio, formed_at, first_touch,
        duration, alternations,
    )


def analyze_breakout_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    trading_range: TradingRange,
) -> BreakoutContext:
    if not trading_range.is_detected or trading_range.lower_boundary is None or trading_range.upper_boundary is None:
        return BreakoutContext(BreakoutDirection.NONE, BreakoutConfirmationStatus.NO_BREAKOUT, None, None, None, 0.0, False, 0, ())
    lower, upper = trading_range.lower_boundary, trading_range.upper_boundary
    analysis_start = min(len(candles), trading_range.formed_at_index + 1)
    attempt: tuple[int, BreakoutDirection, float] | None = None
    for index in range(analysis_start, len(candles)):
        item = candles[index]
        if item.close > upper * (1.0 + BREAKOUT_BUFFER_RATIO):
            attempt = (index, BreakoutDirection.UPWARD, upper)
            break
        if item.close < lower * (1.0 - BREAKOUT_BUFFER_RATIO):
            attempt = (index, BreakoutDirection.DOWNWARD, lower)
            break
    if attempt is None:
        return BreakoutContext(
            BreakoutDirection.NONE, BreakoutConfirmationStatus.NO_BREAKOUT,
            None, None, None, 0.0, False, 0, (), analysis_start,
        )
    index, direction, boundary = attempt
    close = candles[index].close
    later = candles[index + 1:]
    beyond = (lambda value: value > upper) if direction is BreakoutDirection.UPWARD else (lambda value: value < lower)
    observation = candles[index:index + max(FALSE_BREAKOUT_TIME_LOOKAHEAD, RETEST_LOOKAHEAD) + 1]
    beyond_closes: list[tuple[int, EngineTrendCandle]] = []
    for offset, item in enumerate(observation):
        if beyond(item.close):
            beyond_closes.append((index + offset, item))
        else:
            break
    close_count = len(beyond_closes)
    follow_count = max(0, close_count - 1)
    if direction is BreakoutDirection.UPWARD:
        extreme_offset, extreme_candle = max(enumerate(observation), key=lambda pair: pair[1].high)
        extreme_price = extreme_candle.high
        maximum_distance = max(0.0, extreme_price - boundary) / abs(boundary) if boundary else 0.0
    else:
        extreme_offset, extreme_candle = min(enumerate(observation), key=lambda pair: pair[1].low)
        extreme_price = extreme_candle.low
        maximum_distance = max(0.0, boundary - extreme_price) / abs(boundary) if boundary else 0.0
    extreme_index = index + extreme_offset
    closes_confirm = close_count >= MIN_CONFIRMATION_CLOSES
    distance_confirms = maximum_distance >= BREAKOUT_CONFIRMATION_DISTANCE_RATIO
    if closes_confirm and distance_confirms:
        method = BreakoutConfirmationMethod.CLOSE_COUNT_AND_DISTANCE
    elif closes_confirm:
        method = BreakoutConfirmationMethod.CLOSE_COUNT
    elif distance_confirms:
        method = BreakoutConfirmationMethod.DISTANCE
    else:
        method = BreakoutConfirmationMethod.NONE
    confirmed = method is not BreakoutConfirmationMethod.NONE

    return_index: int | None = None
    return_close: float | None = None
    for candidate_index in range(index + 1, min(len(candles), index + 1 + FALSE_BREAKOUT_LOOKAHEAD)):
        candidate_close = candles[candidate_index].close
        if lower <= candidate_close <= upper:
            return_index, return_close = candidate_index, candidate_close
            break
    returned = return_index is not None
    if return_index is not None:
        pre_return = candles[index:return_index]
        if direction is BreakoutDirection.UPWARD:
            extreme_offset, extreme_candle = max(enumerate(pre_return), key=lambda pair: pair[1].high)
            extreme_price = extreme_candle.high
            maximum_distance = max(0.0, extreme_price - boundary) / abs(boundary) if boundary else 0.0
        else:
            extreme_offset, extreme_candle = min(enumerate(pre_return), key=lambda pair: pair[1].low)
            extreme_price = extreme_candle.low
            maximum_distance = max(0.0, boundary - extreme_price) / abs(boundary) if boundary else 0.0
        extreme_index = index + extreme_offset
        distance_confirms = maximum_distance >= BREAKOUT_CONFIRMATION_DISTANCE_RATIO
        if closes_confirm and distance_confirms:
            method = BreakoutConfirmationMethod.CLOSE_COUNT_AND_DISTANCE
        elif closes_confirm:
            method = BreakoutConfirmationMethod.CLOSE_COUNT
        elif distance_confirms:
            method = BreakoutConfirmationMethod.DISTANCE
        else:
            method = BreakoutConfirmationMethod.NONE
        confirmed = method is not BreakoutConfirmationMethod.NONE
    return_depth = 0.0
    false_confirmation = FalseBreakoutConfirmationStatus.NONE
    invalidated = False
    if returned and return_close is not None:
        return_depth = (upper - return_close) / trading_range.width if direction is BreakoutDirection.UPWARD else (return_close - lower) / trading_range.width
        false_confirmation = FalseBreakoutConfirmationStatus.RETURNED_INSIDE
        if return_depth >= 1.0:
            false_confirmation = FalseBreakoutConfirmationStatus.STRONG_PRICE_CONFIRMATION
        elif return_depth >= 0.5:
            false_confirmation = FalseBreakoutConfirmationStatus.INITIAL_PRICE_CONFIRMATION
        time_window_end = min(len(candles), return_index + 1 + FALSE_BREAKOUT_TIME_LOOKAHEAD)
        time_window = candles[return_index + 1:time_window_end]
        revisited = any(
            item.high >= extreme_price if direction is BreakoutDirection.UPWARD else item.low <= extreme_price
            for item in time_window
        )
        if revisited:
            false_confirmation = FalseBreakoutConfirmationStatus.INVALIDATED
            invalidated = True
        elif len(time_window) == FALSE_BREAKOUT_TIME_LOOKAHEAD and false_confirmation is FalseBreakoutConfirmationStatus.RETURNED_INSIDE:
            false_confirmation = FalseBreakoutConfirmationStatus.TIME_CONFIRMATION
    false_confirmed = false_confirmation in {
        FalseBreakoutConfirmationStatus.INITIAL_PRICE_CONFIRMATION,
        FalseBreakoutConfirmationStatus.STRONG_PRICE_CONFIRMATION,
        FalseBreakoutConfirmationStatus.TIME_CONFIRMATION,
    }
    enough_observations = len(candles) - index - 1 >= FOLLOW_THROUGH_LOOKAHEAD
    if false_confirmed:
        status = BreakoutConfirmationStatus.FALSE_BREAKOUT
    elif returned:
        status = BreakoutConfirmationStatus.RETURNED_TO_RANGE
    elif confirmed:
        status = BreakoutConfirmationStatus.CONFIRMED
    elif not enough_observations:
        status = BreakoutConfirmationStatus.ATTEMPT
    else:
        status = BreakoutConfirmationStatus.NO_FOLLOW_THROUGH
    direction_code = "SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT" if direction is BreakoutDirection.UPWARD else "SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT"
    items = [_evidence(direction_code, breakout_index=index), _evidence("SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION")]
    if returned:
        items.append(_evidence("SCHWAGER_PRICE_RETURNED_TO_RANGE", return_index=return_index, return_depth_ratio=return_depth))
        if false_confirmed:
            false_code = "SCHWAGER_FALSE_BREAKOUT_UP" if direction is BreakoutDirection.UPWARD else "SCHWAGER_FALSE_BREAKOUT_DOWN"
            items.append(_evidence(false_code))
        confirmation_codes = {
            FalseBreakoutConfirmationStatus.INITIAL_PRICE_CONFIRMATION: "SCHWAGER_FALSE_BREAKOUT_INITIAL_CONFIRMATION",
            FalseBreakoutConfirmationStatus.STRONG_PRICE_CONFIRMATION: "SCHWAGER_FALSE_BREAKOUT_STRONG_CONFIRMATION",
            FalseBreakoutConfirmationStatus.TIME_CONFIRMATION: "SCHWAGER_FALSE_BREAKOUT_TIME_CONFIRMATION",
            FalseBreakoutConfirmationStatus.INVALIDATED: "SCHWAGER_FALSE_BREAKOUT_INVALIDATED",
        }
        if false_confirmation in confirmation_codes:
            items.append(_evidence(confirmation_codes[false_confirmation]))
    elif confirmed:
        items.append(_evidence("SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED", 1 if direction is BreakoutDirection.UPWARD else -1, count=follow_count))
        if closes_confirm:
            items.append(_evidence("SCHWAGER_BREAKOUT_CONFIRMED_BY_CLOSE_COUNT", count=close_count))
        if distance_confirms:
            items.append(_evidence("SCHWAGER_BREAKOUT_CONFIRMED_BY_DISTANCE", distance_ratio=maximum_distance))
    elif status is BreakoutConfirmationStatus.ATTEMPT:
        pass
    else:
        items.append(_evidence("SCHWAGER_BREAKOUT_NO_FOLLOW_THROUGH", count=follow_count))
    return BreakoutContext(
        direction, status, index, boundary, close,
        abs(close - boundary) / abs(boundary) if boundary else 0.0,
        returned, follow_count, tuple(items), analysis_start, method,
        close_count, extreme_index, extreme_price, maximum_distance,
        return_index, return_depth, (return_index - index if return_index is not None else 0),
        false_confirmation, invalidated,
    )


def analyze_polarity_flip_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    trading_range: TradingRange,
    breakout_context: BreakoutContext,
) -> PolarityFlipContext:
    index = breakout_context.breakout_index
    if index is None or breakout_context.direction is BreakoutDirection.NONE:
        return PolarityFlipContext(PolarityFlipStatus.NONE, None, None, False, ())
    upward = breakout_context.direction is BreakoutDirection.UPWARD
    boundary = trading_range.upper_boundary if upward else trading_range.lower_boundary
    if boundary is None:
        return PolarityFlipContext(PolarityFlipStatus.NONE, None, None, False, ())
    source = ZoneType.RESISTANCE if upward else ZoneType.SUPPORT
    if breakout_context.returned_to_range:
        test_index = breakout_context.return_index
        evidence = (
            _evidence("SCHWAGER_BREAKOUT_RETEST_FAILED", test_index=test_index),
            _evidence("SCHWAGER_POLARITY_FLIP_FAILED"),
        )
        return PolarityFlipContext(PolarityFlipStatus.FAILED, source, test_index, False, evidence)
    if breakout_context.status is not BreakoutConfirmationStatus.CONFIRMED:
        return PolarityFlipContext(PolarityFlipStatus.NONE, source, None, False, ())
    departure_index: int | None = None
    for candidate_index in range(index, min(len(candles), index + 1 + RETEST_LOOKAHEAD)):
        candidate = candles[candidate_index]
        departure_close = candidate.close >= boundary * (1.0 + RETEST_DEPARTURE_RATIO) if upward else candidate.close <= boundary * (1.0 - RETEST_DEPARTURE_RATIO)
        if departure_close:
            departure_index = candidate_index
            break
    if departure_index is None:
        return PolarityFlipContext(
            PolarityFlipStatus.NONE, source, None, False,
            (_evidence("SCHWAGER_POLARITY_RETEST_AWAITING_DEPARTURE"),),
        )
    for test_index in range(departure_index + 1, min(len(candles), departure_index + 1 + RETEST_LOOKAHEAD)):
        item = candles[test_index]
        held = item.low <= boundary and item.close >= boundary if upward else item.high >= boundary and item.close <= boundary
        if held:
            status = PolarityFlipStatus.RESISTANCE_TO_SUPPORT if upward else PolarityFlipStatus.SUPPORT_TO_RESISTANCE
            code = "SCHWAGER_RESISTANCE_TURNED_SUPPORT" if upward else "SCHWAGER_SUPPORT_TURNED_RESISTANCE"
            evidence = (_evidence("SCHWAGER_BREAKOUT_RETEST_HELD", test_index=test_index), _evidence(code), _evidence("SCHWAGER_POLARITY_FLIP_CONFIRMED"))
            return PolarityFlipContext(status, source, test_index, True, evidence, departure_index, test_index)
        returned = trading_range.lower_boundary <= item.close <= trading_range.upper_boundary
        if returned:
            evidence = (_evidence("SCHWAGER_BREAKOUT_RETEST_FAILED", test_index=test_index), _evidence("SCHWAGER_POLARITY_FLIP_FAILED"))
            return PolarityFlipContext(PolarityFlipStatus.FAILED, source, test_index, False, evidence, departure_index, None)
    return PolarityFlipContext(PolarityFlipStatus.NONE, source, None, False, (), departure_index, None)


def analyze_schwager_range_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
    swing_points: tuple[SwingPoint, ...] | list[SwingPoint] | None = None,
) -> SchwagerRangeContext:
    swings = (
        detect_swing_points(candles)
        if swing_points is None
        else tuple(swing_points)
    )
    zones = build_support_resistance_zones(candles, swings)
    trading_range = detect_trading_range(candles, zones)
    breakout = analyze_breakout_context(candles, trading_range)
    polarity = analyze_polarity_flip_context(candles, trading_range, breakout)
    if polarity.held and polarity.source_zone_type is not None:
        changed_role = ZoneType.SUPPORT if polarity.status is PolarityFlipStatus.RESISTANCE_TO_SUPPORT else ZoneType.RESISTANCE
        zones = tuple(
            replace(
                zone,
                current_zone_type=changed_role,
                role_changed_at_index=polarity.role_changed_at_index,
            )
            if zone.zone_type is polarity.source_zone_type
            and zone is (trading_range.resistance_zone if polarity.source_zone_type is ZoneType.RESISTANCE else trading_range.support_zone)
            else zone
            for zone in zones
        )
    items: list[EngineTrendEvidence] = []
    for zone in zones:
        identified = "SCHWAGER_SUPPORT_ZONE_IDENTIFIED" if zone.zone_type is ZoneType.SUPPORT else "SCHWAGER_RESISTANCE_ZONE_IDENTIFIED"
        held = "SCHWAGER_SUPPORT_ZONE_HELD" if zone.zone_type is ZoneType.SUPPORT else "SCHWAGER_RESISTANCE_ZONE_HELD"
        items.append(_evidence(identified, touches=zone.touch_count))
        if zone.touch_count >= MIN_ZONE_TOUCHES:
            items.append(_evidence(held, touches=zone.touch_count))
        if zone.is_significant_single_extreme:
            items.append(_evidence("SCHWAGER_PREVIOUS_EXTREME_ZONE_IDENTIFIED", index=zone.source_indexes[0]))
        if zone.zone_width_ratio > ZONE_CLUSTER_TOLERANCE_RATIO:
            items.append(_evidence("SCHWAGER_ZONE_TOO_WIDE", width_ratio=zone.zone_width_ratio))
    if not zones:
        items.append(_evidence("SCHWAGER_INSUFFICIENT_LEVEL_TOUCHES", swing_count=len(swings)))
    if trading_range.support_zone and trading_range.resistance_zone and trading_range.support_zone.upper_price >= trading_range.resistance_zone.lower_price:
        items.append(_evidence("SCHWAGER_ZONE_OVERLAP_CONFLICT"))
    if trading_range.is_detected:
        items.extend((
            _evidence("SCHWAGER_TRADING_RANGE_DETECTED"),
            _evidence("SCHWAGER_PRICE_INSIDE_RANGE", ratio=trading_range.inside_close_ratio),
            _evidence("SCHWAGER_RANGE_UPPER_BOUNDARY_HELD"),
            _evidence("SCHWAGER_RANGE_LOWER_BOUNDARY_HELD"),
            _evidence("SCHWAGER_RANGE_DURATION_CONFIRMED", duration=trading_range.duration_candles),
            _evidence("SCHWAGER_RANGE_BOUNDARY_ALTERNATION_CONFIRMED", count=trading_range.boundary_alternation_count),
        ))
    else:
        items.append(_evidence("SCHWAGER_RANGE_NOT_CONFIRMED"))
        if trading_range.touch_count < MIN_RANGE_TOUCHES:
            items.append(_evidence("SCHWAGER_INSUFFICIENT_LEVEL_TOUCHES", touches=trading_range.touch_count))
    items.extend(breakout.evidence)
    items.extend(polarity.evidence)
    evidence = tuple(items)
    reason_codes = tuple(dict.fromkeys(item.code for item in evidence))
    summary = {
        "swing_count": len(swings), "zone_count": len(zones),
        "range_detected": trading_range.is_detected,
        "range_formed_at_index": trading_range.formed_at_index,
        "range_duration_candles": trading_range.duration_candles,
        "inside_close_ratio": trading_range.inside_close_ratio,
        "breakout_direction": breakout.direction.value,
        "breakout_status": breakout.status.value,
        "polarity_status": polarity.status.value,
    }
    return SchwagerRangeContext(len(candles), zones, trading_range, breakout, polarity, evidence, reason_codes, summary)
