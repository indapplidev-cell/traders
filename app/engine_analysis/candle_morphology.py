"""Measured candle morphology for the clean engine_analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.engine_analysis.schemas import EngineAnalysisCandle


DOJI_BODY_TO_RANGE_MAX = 0.10
SPINNING_TOP_BODY_TO_RANGE_MAX = 0.25
SMALL_BODY_TO_RANGE_MAX = 0.30
LARGE_BODY_TO_RANGE_MIN = 0.60
STRONG_BODY_TO_RANGE_MIN = 0.70
EXTENDED_SHADOW_TO_RANGE_MIN = 0.55
NEAR_HIGH_THRESHOLD = 0.75
NEAR_LOW_THRESHOLD = 0.25


class CandleDirection(str, Enum):
    """Direction of a candle body."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class CandleMorphology:
    """Numerical description of one OHLCV candle."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    real_body_size: float
    full_range_size: float
    upper_shadow_size: float
    lower_shadow_size: float
    body_to_range_ratio: float
    upper_shadow_to_range_ratio: float
    lower_shadow_to_range_ratio: float
    close_position_in_range: float
    open_position_in_range: float
    direction: CandleDirection
    is_bullish: bool
    is_bearish: bool
    is_neutral: bool
    is_doji: bool
    is_spinning_top: bool
    is_small_body: bool
    is_long_body: bool
    is_strong_bullish_body: bool
    is_strong_bearish_body: bool
    has_long_upper_shadow: bool
    has_long_lower_shadow: bool
    close_near_high: bool
    close_near_low: bool

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["direction"] = self.direction.value
        return payload


def _bounded_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def analyze_candle_morphology(candle: EngineAnalysisCandle) -> CandleMorphology:
    """Measure a candle without assigning market state or forecasting meaning."""

    real_body_size = abs(candle.close - candle.open)
    full_range_size = max(0.0, candle.high - candle.low)
    upper_shadow_size = max(0.0, candle.high - max(candle.open, candle.close))
    lower_shadow_size = max(0.0, min(candle.open, candle.close) - candle.low)

    body_ratio = _bounded_ratio(real_body_size, full_range_size)
    upper_ratio = _bounded_ratio(upper_shadow_size, full_range_size)
    lower_ratio = _bounded_ratio(lower_shadow_size, full_range_size)
    if full_range_size == 0.0:
        close_position = open_position = 0.5
    else:
        close_position = _bounded_ratio(candle.close - candle.low, full_range_size)
        open_position = _bounded_ratio(candle.open - candle.low, full_range_size)

    if candle.close > candle.open:
        direction = CandleDirection.BULLISH
    elif candle.close < candle.open:
        direction = CandleDirection.BEARISH
    else:
        direction = CandleDirection.NEUTRAL

    is_bullish = direction is CandleDirection.BULLISH
    is_bearish = direction is CandleDirection.BEARISH

    return CandleMorphology(
        timestamp=candle.timestamp,
        open=float(candle.open),
        high=float(candle.high),
        low=float(candle.low),
        close=float(candle.close),
        volume=float(candle.volume),
        real_body_size=float(real_body_size),
        full_range_size=float(full_range_size),
        upper_shadow_size=float(upper_shadow_size),
        lower_shadow_size=float(lower_shadow_size),
        body_to_range_ratio=float(body_ratio),
        upper_shadow_to_range_ratio=float(upper_ratio),
        lower_shadow_to_range_ratio=float(lower_ratio),
        close_position_in_range=float(close_position),
        open_position_in_range=float(open_position),
        direction=direction,
        is_bullish=is_bullish,
        is_bearish=is_bearish,
        is_neutral=direction is CandleDirection.NEUTRAL,
        is_doji=body_ratio <= DOJI_BODY_TO_RANGE_MAX,
        # Nison defines a spinning top by its small real body; shadow size is
        # not a defining condition.  Doji remains a distinct morphology.
        is_spinning_top=(
            DOJI_BODY_TO_RANGE_MAX < body_ratio <= SPINNING_TOP_BODY_TO_RANGE_MAX
        ),
        is_small_body=body_ratio <= SMALL_BODY_TO_RANGE_MAX,
        is_long_body=body_ratio >= LARGE_BODY_TO_RANGE_MIN,
        is_strong_bullish_body=(
            is_bullish
            and body_ratio >= STRONG_BODY_TO_RANGE_MIN
            and close_position >= NEAR_HIGH_THRESHOLD
        ),
        is_strong_bearish_body=(
            is_bearish
            and body_ratio >= STRONG_BODY_TO_RANGE_MIN
            and close_position <= NEAR_LOW_THRESHOLD
        ),
        has_long_upper_shadow=upper_ratio >= EXTENDED_SHADOW_TO_RANGE_MIN,
        has_long_lower_shadow=lower_ratio >= EXTENDED_SHADOW_TO_RANGE_MIN,
        close_near_high=close_position >= NEAR_HIGH_THRESHOLD,
        close_near_low=close_position <= NEAR_LOW_THRESHOLD,
    )


def analyze_candle_window_morphology(
    candles: tuple[EngineAnalysisCandle, ...] | list[EngineAnalysisCandle],
) -> tuple[CandleMorphology, ...]:
    """Measure each candle in input order."""

    return tuple(analyze_candle_morphology(candle) for candle in candles)
