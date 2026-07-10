from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.market_reader.candle_window import CandleBar, CandleWindow


class CandleDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class CandleMorphology:
    open_time: datetime
    direction: CandleDirection
    body_signed: float
    body_abs: float
    candle_range: float
    upper_shadow: float
    lower_shadow: float
    body_to_range_ratio: float
    upper_shadow_to_range_ratio: float
    lower_shadow_to_range_ratio: float
    close_position_in_range: float
    is_bullish: bool
    is_bearish: bool
    is_neutral: bool
    is_doji_like: bool
    is_strong_body: bool
    has_long_upper_shadow: bool
    has_long_lower_shadow: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "open_time": self.open_time.isoformat(),
            "direction": self.direction.value,
            "body_signed": self.body_signed,
            "body_abs": self.body_abs,
            "candle_range": self.candle_range,
            "upper_shadow": self.upper_shadow,
            "lower_shadow": self.lower_shadow,
            "body_to_range_ratio": self.body_to_range_ratio,
            "upper_shadow_to_range_ratio": self.upper_shadow_to_range_ratio,
            "lower_shadow_to_range_ratio": self.lower_shadow_to_range_ratio,
            "close_position_in_range": self.close_position_in_range,
            "is_bullish": self.is_bullish,
            "is_bearish": self.is_bearish,
            "is_neutral": self.is_neutral,
            "is_doji_like": self.is_doji_like,
            "is_strong_body": self.is_strong_body,
            "has_long_upper_shadow": self.has_long_upper_shadow,
            "has_long_lower_shadow": self.has_long_lower_shadow,
        }


@dataclass(frozen=True)
class CandleMorphologyAnalyzer:
    doji_body_to_range_threshold: float = 0.10
    strong_body_to_range_threshold: float = 0.60
    long_shadow_to_range_threshold: float = 0.55

    def __post_init__(self) -> None:
        _validate_ratio_threshold(self.doji_body_to_range_threshold, "doji_body_to_range_threshold")
        _validate_ratio_threshold(self.strong_body_to_range_threshold, "strong_body_to_range_threshold")
        _validate_ratio_threshold(self.long_shadow_to_range_threshold, "long_shadow_to_range_threshold")

        if self.strong_body_to_range_threshold <= self.doji_body_to_range_threshold:
            raise ValueError("strong_body_to_range_threshold must be greater than doji_body_to_range_threshold")

    def analyze_bar(self, candle: CandleBar) -> CandleMorphology:
        body_signed = candle.close - candle.open
        body_abs = abs(body_signed)
        candle_range = candle.high - candle.low
        upper_shadow = candle.high - max(candle.open, candle.close)
        lower_shadow = min(candle.open, candle.close) - candle.low

        body_to_range_ratio = _safe_ratio(body_abs, candle_range)
        upper_shadow_to_range_ratio = _safe_ratio(upper_shadow, candle_range)
        lower_shadow_to_range_ratio = _safe_ratio(lower_shadow, candle_range)
        close_position_in_range = _close_position_in_range(
            close=candle.close,
            low=candle.low,
            candle_range=candle_range,
        )

        direction = _direction(body_signed)

        is_bullish = direction == CandleDirection.BULLISH
        is_bearish = direction == CandleDirection.BEARISH
        is_neutral = direction == CandleDirection.NEUTRAL

        is_zero_range = candle_range == 0.0
        is_doji_like = is_zero_range or body_to_range_ratio <= self.doji_body_to_range_threshold
        is_strong_body = (not is_zero_range) and body_to_range_ratio >= self.strong_body_to_range_threshold
        has_long_upper_shadow = (not is_zero_range) and (
            upper_shadow_to_range_ratio >= self.long_shadow_to_range_threshold
        )
        has_long_lower_shadow = (not is_zero_range) and (
            lower_shadow_to_range_ratio >= self.long_shadow_to_range_threshold
        )

        return CandleMorphology(
            open_time=candle.open_time,
            direction=direction,
            body_signed=body_signed,
            body_abs=body_abs,
            candle_range=candle_range,
            upper_shadow=upper_shadow,
            lower_shadow=lower_shadow,
            body_to_range_ratio=body_to_range_ratio,
            upper_shadow_to_range_ratio=upper_shadow_to_range_ratio,
            lower_shadow_to_range_ratio=lower_shadow_to_range_ratio,
            close_position_in_range=close_position_in_range,
            is_bullish=is_bullish,
            is_bearish=is_bearish,
            is_neutral=is_neutral,
            is_doji_like=is_doji_like,
            is_strong_body=is_strong_body,
            has_long_upper_shadow=has_long_upper_shadow,
            has_long_lower_shadow=has_long_lower_shadow,
        )

    def analyze_window(self, window: CandleWindow) -> tuple[CandleMorphology, ...]:
        return tuple(self.analyze_bar(candle) for candle in window.candles)

    def latest(self, window: CandleWindow) -> CandleMorphology:
        return self.analyze_bar(window.latest)


def _direction(body_signed: float) -> CandleDirection:
    if body_signed > 0.0:
        return CandleDirection.BULLISH
    if body_signed < 0.0:
        return CandleDirection.BEARISH
    return CandleDirection.NEUTRAL


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def _close_position_in_range(*, close: float, low: float, candle_range: float) -> float:
    if candle_range <= 0.0:
        return 0.5
    return (close - low) / candle_range


def _validate_ratio_threshold(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")
