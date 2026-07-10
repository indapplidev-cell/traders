from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from app.market_reader.candle_window import CandleBar, CandleWindow


class EmaTrendDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class PriceEmaPosition(str, Enum):
    ABOVE_FAST_ABOVE_SLOW = "ABOVE_FAST_ABOVE_SLOW"
    BELOW_FAST_BELOW_SLOW = "BELOW_FAST_BELOW_SLOW"
    BETWEEN_EMAS = "BETWEEN_EMAS"
    AROUND_EMAS = "AROUND_EMAS"
    UNKNOWN = "UNKNOWN"


class VolatilityContext(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TechnicalContextResult:
    ema_direction: EmaTrendDirection
    price_ema_position: PriceEmaPosition
    volatility_context: VolatilityContext
    technical_score: float
    candle_count: int
    fast_ema: float | None = None
    slow_ema: float | None = None
    atr: float | None = None
    atr_pct: float | None = None
    fast_ema_slope_pct: float | None = None
    slow_ema_slope_pct: float | None = None
    price_to_fast_ema_pct: float | None = None
    price_to_slow_ema_pct: float | None = None
    ema_spread_pct: float | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.technical_score <= 1.0:
            raise ValueError("technical_score must be between 0.0 and 1.0")

        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")

        _validate_optional_finite(self.fast_ema, "fast_ema")
        _validate_optional_finite(self.slow_ema, "slow_ema")
        _validate_optional_finite(self.atr, "atr")
        _validate_optional_finite(self.atr_pct, "atr_pct")
        _validate_optional_finite(self.fast_ema_slope_pct, "fast_ema_slope_pct")
        _validate_optional_finite(self.slow_ema_slope_pct, "slow_ema_slope_pct")
        _validate_optional_finite(self.price_to_fast_ema_pct, "price_to_fast_ema_pct")
        _validate_optional_finite(self.price_to_slow_ema_pct, "price_to_slow_ema_pct")
        _validate_optional_finite(self.ema_spread_pct, "ema_spread_pct")

        if self.fast_ema is not None and self.fast_ema <= 0.0:
            raise ValueError("fast_ema must be positive")

        if self.slow_ema is not None and self.slow_ema <= 0.0:
            raise ValueError("slow_ema must be positive")

        if self.atr is not None and self.atr < 0.0:
            raise ValueError("atr must be non-negative")

        if self.atr_pct is not None and self.atr_pct < 0.0:
            raise ValueError("atr_pct must be non-negative")

        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    @property
    def has_technical_context(self) -> bool:
        return (
            self.ema_direction != EmaTrendDirection.UNKNOWN
            and self.price_ema_position != PriceEmaPosition.UNKNOWN
            and self.volatility_context != VolatilityContext.UNKNOWN
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "ema_direction": self.ema_direction.value,
            "price_ema_position": self.price_ema_position.value,
            "volatility_context": self.volatility_context.value,
            "technical_score": self.technical_score,
            "candle_count": self.candle_count,
            "fast_ema": self.fast_ema,
            "slow_ema": self.slow_ema,
            "atr": self.atr,
            "atr_pct": self.atr_pct,
            "fast_ema_slope_pct": self.fast_ema_slope_pct,
            "slow_ema_slope_pct": self.slow_ema_slope_pct,
            "price_to_fast_ema_pct": self.price_to_fast_ema_pct,
            "price_to_slow_ema_pct": self.price_to_slow_ema_pct,
            "ema_spread_pct": self.ema_spread_pct,
            "has_technical_context": self.has_technical_context,
            "reason_codes": list(self.reason_codes),
        }


class TechnicalContextAnalyzer:
    def analyze(
        self,
        window: CandleWindow,
        *,
        fast_ema_period: int = 9,
        slow_ema_period: int = 21,
        atr_period: int = 14,
        slope_lookback: int = 3,
        flat_slope_tolerance_pct: float = 0.0005,
        around_ema_tolerance_pct: float = 0.001,
        high_volatility_atr_pct: float = 0.03,
        low_volatility_atr_pct: float = 0.003,
    ) -> TechnicalContextResult:
        _validate_parameters(
            fast_ema_period=fast_ema_period,
            slow_ema_period=slow_ema_period,
            atr_period=atr_period,
            slope_lookback=slope_lookback,
            flat_slope_tolerance_pct=flat_slope_tolerance_pct,
            around_ema_tolerance_pct=around_ema_tolerance_pct,
            high_volatility_atr_pct=high_volatility_atr_pct,
            low_volatility_atr_pct=low_volatility_atr_pct,
        )

        required_candles = max(slow_ema_period + slope_lookback, atr_period + 1)
        if window.size < required_candles:
            return TechnicalContextResult(
                ema_direction=EmaTrendDirection.UNKNOWN,
                price_ema_position=PriceEmaPosition.UNKNOWN,
                volatility_context=VolatilityContext.UNKNOWN,
                technical_score=0.0,
                candle_count=window.size,
                reason_codes=("NOT_ENOUGH_CANDLES_FOR_TECHNICAL_CONTEXT",),
            )

        closes = window.closes
        latest_close = closes[-1]

        fast_ema_values = _ema_series(closes, fast_ema_period)
        slow_ema_values = _ema_series(closes, slow_ema_period)

        latest_fast_ema = _last_defined(fast_ema_values, "fast_ema")
        latest_slow_ema = _last_defined(slow_ema_values, "slow_ema")

        previous_fast_ema = fast_ema_values[-1 - slope_lookback]
        previous_slow_ema = slow_ema_values[-1 - slope_lookback]

        if previous_fast_ema is None or previous_slow_ema is None:
            return TechnicalContextResult(
                ema_direction=EmaTrendDirection.UNKNOWN,
                price_ema_position=PriceEmaPosition.UNKNOWN,
                volatility_context=VolatilityContext.UNKNOWN,
                technical_score=0.0,
                candle_count=window.size,
                reason_codes=("NOT_ENOUGH_EMA_HISTORY_FOR_SLOPE",),
            )

        fast_slope_pct = _pct_change(previous_fast_ema, latest_fast_ema)
        slow_slope_pct = _pct_change(previous_slow_ema, latest_slow_ema)

        atr = _latest_atr(window.candles, atr_period)
        atr_pct = atr / latest_close if latest_close > 0.0 else 0.0

        price_to_fast_ema_pct = _pct_distance(latest_close, latest_fast_ema)
        price_to_slow_ema_pct = _pct_distance(latest_close, latest_slow_ema)
        ema_spread_pct = abs(latest_fast_ema - latest_slow_ema) / latest_slow_ema

        ema_direction = _classify_ema_direction(
            fast_ema=latest_fast_ema,
            slow_ema=latest_slow_ema,
            fast_slope_pct=fast_slope_pct,
            slow_slope_pct=slow_slope_pct,
            flat_slope_tolerance_pct=flat_slope_tolerance_pct,
        )
        price_position = _classify_price_ema_position(
            close=latest_close,
            fast_ema=latest_fast_ema,
            slow_ema=latest_slow_ema,
            around_ema_tolerance_pct=around_ema_tolerance_pct,
        )
        volatility_context = _classify_volatility(
            atr_pct=atr_pct,
            high_volatility_atr_pct=high_volatility_atr_pct,
            low_volatility_atr_pct=low_volatility_atr_pct,
        )

        reason_codes = _build_reason_codes(
            ema_direction=ema_direction,
            price_position=price_position,
            volatility_context=volatility_context,
            fast_ema=latest_fast_ema,
            slow_ema=latest_slow_ema,
        )

        technical_score = _score_technical_context(
            ema_direction=ema_direction,
            price_position=price_position,
            volatility_context=volatility_context,
        )

        return TechnicalContextResult(
            ema_direction=ema_direction,
            price_ema_position=price_position,
            volatility_context=volatility_context,
            technical_score=technical_score,
            candle_count=window.size,
            fast_ema=latest_fast_ema,
            slow_ema=latest_slow_ema,
            atr=atr,
            atr_pct=atr_pct,
            fast_ema_slope_pct=fast_slope_pct,
            slow_ema_slope_pct=slow_slope_pct,
            price_to_fast_ema_pct=price_to_fast_ema_pct,
            price_to_slow_ema_pct=price_to_slow_ema_pct,
            ema_spread_pct=ema_spread_pct,
            reason_codes=reason_codes,
        )


def _validate_parameters(
    *,
    fast_ema_period: int,
    slow_ema_period: int,
    atr_period: int,
    slope_lookback: int,
    flat_slope_tolerance_pct: float,
    around_ema_tolerance_pct: float,
    high_volatility_atr_pct: float,
    low_volatility_atr_pct: float,
) -> None:
    if fast_ema_period <= 1:
        raise ValueError("fast_ema_period must be greater than 1")

    if slow_ema_period <= fast_ema_period:
        raise ValueError("slow_ema_period must be greater than fast_ema_period")

    if atr_period <= 1:
        raise ValueError("atr_period must be greater than 1")

    if slope_lookback <= 0:
        raise ValueError("slope_lookback must be positive")

    if flat_slope_tolerance_pct < 0.0:
        raise ValueError("flat_slope_tolerance_pct must be non-negative")

    if around_ema_tolerance_pct < 0.0:
        raise ValueError("around_ema_tolerance_pct must be non-negative")

    if high_volatility_atr_pct <= 0.0:
        raise ValueError("high_volatility_atr_pct must be positive")

    if low_volatility_atr_pct < 0.0:
        raise ValueError("low_volatility_atr_pct must be non-negative")

    if low_volatility_atr_pct >= high_volatility_atr_pct:
        raise ValueError("low_volatility_atr_pct must be lower than high_volatility_atr_pct")


def _ema_series(values: Sequence[float], period: int) -> tuple[float | None, ...]:
    if len(values) < period:
        return tuple(None for _ in values)

    result: list[float | None] = [None for _ in values]
    first_ema = sum(values[:period]) / period
    result[period - 1] = first_ema

    multiplier = 2.0 / (period + 1.0)
    previous_ema = first_ema

    for index in range(period, len(values)):
        previous_ema = (values[index] - previous_ema) * multiplier + previous_ema
        result[index] = previous_ema

    return tuple(result)


def _last_defined(values: Sequence[float | None], field_name: str) -> float:
    for value in reversed(values):
        if value is not None:
            return value
    raise ValueError(f"{field_name} is not available")


def _latest_atr(candles: Sequence[CandleBar], period: int) -> float:
    true_ranges: list[float] = []

    for previous, current in zip(candles, candles[1:]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )

    if len(true_ranges) < period:
        raise ValueError("not enough candles for ATR")

    return sum(true_ranges[-period:]) / period


def _pct_change(previous: float, current: float) -> float:
    if previous == 0.0:
        return 0.0
    return (current - previous) / abs(previous)


def _pct_distance(value: float, baseline: float) -> float:
    if baseline == 0.0:
        return 0.0
    return (value - baseline) / baseline


def _classify_ema_direction(
    *,
    fast_ema: float,
    slow_ema: float,
    fast_slope_pct: float,
    slow_slope_pct: float,
    flat_slope_tolerance_pct: float,
) -> EmaTrendDirection:
    fast_up = fast_slope_pct > flat_slope_tolerance_pct
    slow_up = slow_slope_pct > flat_slope_tolerance_pct
    fast_down = fast_slope_pct < -flat_slope_tolerance_pct
    slow_down = slow_slope_pct < -flat_slope_tolerance_pct
    fast_flat = abs(fast_slope_pct) <= flat_slope_tolerance_pct
    slow_flat = abs(slow_slope_pct) <= flat_slope_tolerance_pct

    if fast_ema > slow_ema and fast_up and slow_up:
        return EmaTrendDirection.UP

    if fast_ema < slow_ema and fast_down and slow_down:
        return EmaTrendDirection.DOWN

    if fast_flat and slow_flat:
        return EmaTrendDirection.FLAT

    return EmaTrendDirection.MIXED


def _classify_price_ema_position(
    *,
    close: float,
    fast_ema: float,
    slow_ema: float,
    around_ema_tolerance_pct: float,
) -> PriceEmaPosition:
    fast_tolerance = abs(fast_ema) * around_ema_tolerance_pct
    slow_tolerance = abs(slow_ema) * around_ema_tolerance_pct

    near_fast = abs(close - fast_ema) <= fast_tolerance
    near_slow = abs(close - slow_ema) <= slow_tolerance

    if near_fast or near_slow:
        return PriceEmaPosition.AROUND_EMAS

    if close > fast_ema and close > slow_ema:
        return PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW

    if close < fast_ema and close < slow_ema:
        return PriceEmaPosition.BELOW_FAST_BELOW_SLOW

    return PriceEmaPosition.BETWEEN_EMAS


def _classify_volatility(
    *,
    atr_pct: float,
    high_volatility_atr_pct: float,
    low_volatility_atr_pct: float,
) -> VolatilityContext:
    if atr_pct >= high_volatility_atr_pct:
        return VolatilityContext.HIGH

    if atr_pct <= low_volatility_atr_pct:
        return VolatilityContext.LOW

    return VolatilityContext.NORMAL


def _build_reason_codes(
    *,
    ema_direction: EmaTrendDirection,
    price_position: PriceEmaPosition,
    volatility_context: VolatilityContext,
    fast_ema: float,
    slow_ema: float,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if ema_direction == EmaTrendDirection.UP:
        reasons.append("EMA_TREND_UP")
    elif ema_direction == EmaTrendDirection.DOWN:
        reasons.append("EMA_TREND_DOWN")
    elif ema_direction == EmaTrendDirection.FLAT:
        reasons.append("EMA_TREND_FLAT")
    elif ema_direction == EmaTrendDirection.MIXED:
        reasons.append("EMA_TREND_MIXED")

    if fast_ema > slow_ema:
        reasons.append("FAST_EMA_ABOVE_SLOW_EMA")
    elif fast_ema < slow_ema:
        reasons.append("FAST_EMA_BELOW_SLOW_EMA")
    else:
        reasons.append("FAST_EMA_EQUAL_SLOW_EMA")

    if price_position == PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW:
        reasons.append("PRICE_ABOVE_EMAS")
    elif price_position == PriceEmaPosition.BELOW_FAST_BELOW_SLOW:
        reasons.append("PRICE_BELOW_EMAS")
    elif price_position == PriceEmaPosition.BETWEEN_EMAS:
        reasons.append("PRICE_BETWEEN_EMAS")
    elif price_position == PriceEmaPosition.AROUND_EMAS:
        reasons.append("PRICE_AROUND_EMA")

    if volatility_context == VolatilityContext.HIGH:
        reasons.append("ATR_HIGH_VOLATILITY")
    elif volatility_context == VolatilityContext.LOW:
        reasons.append("ATR_LOW_VOLATILITY")
    elif volatility_context == VolatilityContext.NORMAL:
        reasons.append("ATR_NORMAL_VOLATILITY")

    return tuple(reasons)


def _score_technical_context(
    *,
    ema_direction: EmaTrendDirection,
    price_position: PriceEmaPosition,
    volatility_context: VolatilityContext,
) -> float:
    score = 0.0

    if ema_direction in {EmaTrendDirection.UP, EmaTrendDirection.DOWN}:
        score += 0.45
    elif ema_direction == EmaTrendDirection.FLAT:
        score += 0.25
    elif ema_direction == EmaTrendDirection.MIXED:
        score += 0.15

    if price_position in {
        PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
        PriceEmaPosition.BELOW_FAST_BELOW_SLOW,
    }:
        score += 0.35
    elif price_position in {PriceEmaPosition.BETWEEN_EMAS, PriceEmaPosition.AROUND_EMAS}:
        score += 0.15

    if volatility_context == VolatilityContext.NORMAL:
        score += 0.20
    elif volatility_context in {VolatilityContext.HIGH, VolatilityContext.LOW}:
        score += 0.10

    return _clamp(score)


def _validate_optional_finite(value: float | None, field_name: str) -> None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
