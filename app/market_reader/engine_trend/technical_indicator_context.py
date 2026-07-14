"""Classical technical indicators used only as hypothesis confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import sqrt

from app.market_reader.engine_trend.schemas import EngineTrendCandle


class IndicatorDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNAVAILABLE = "UNAVAILABLE"


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((period - 1) * average_gain + gain) / period
        average_loss = ((period - 1) * average_loss + loss) / period
    if average_loss == 0.0:
        return 100.0 if average_gain > 0.0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - 100.0 / (1.0 + relative_strength)


def _true_ranges(candles: tuple[EngineTrendCandle, ...]) -> list[float]:
    output: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            output.append(candle.high - candle.low)
            continue
        previous_close = candles[index - 1].close
        output.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )
    return output


def _adx(candles: tuple[EngineTrendCandle, ...], period: int = 14) -> float | None:
    if len(candles) < period + 2:
        return None
    true_ranges = _true_ranges(candles)[1:]
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for previous, current in zip(candles, candles[1:]):
        up = current.high - previous.high
        down = previous.low - current.low
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    dx_values: list[float] = []
    for end in range(period, len(true_ranges) + 1):
        tr = sum(true_ranges[end - period:end])
        if tr <= 0:
            continue
        plus_di = 100.0 * sum(plus_dm[end - period:end]) / tr
        minus_di = 100.0 * sum(minus_dm[end - period:end]) / tr
        denominator = plus_di + minus_di
        if denominator > 0:
            dx_values.append(100.0 * abs(plus_di - minus_di) / denominator)
    return sum(dx_values[-period:]) / min(period, len(dx_values)) if dx_values else None


@dataclass(frozen=True)
class TechnicalIndicatorContext:
    available: bool
    sma_20: float | None
    ema_12: float | None
    ema_26: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    atr_14: float | None
    atr_ratio: float | None
    adx_14: float | None
    bollinger_mid: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    vwap: float | None
    direction: IndicatorDirection
    bullish_votes: int
    bearish_votes: int
    reason_codes: tuple[str, ...]

    def confirms(self, direction: IndicatorDirection) -> bool:
        return self.direction is direction

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "sma_20": self.sma_20,
            "ema_12": self.ema_12,
            "ema_26": self.ema_26,
            "rsi_14": self.rsi_14,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "atr_14": self.atr_14,
            "atr_ratio": self.atr_ratio,
            "adx_14": self.adx_14,
            "bollinger_mid": self.bollinger_mid,
            "bollinger_upper": self.bollinger_upper,
            "bollinger_lower": self.bollinger_lower,
            "vwap": self.vwap,
            "direction": self.direction.value,
            "bullish_votes": self.bullish_votes,
            "bearish_votes": self.bearish_votes,
            "reason_codes": list(self.reason_codes),
        }


def analyze_technical_indicators(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> TechnicalIndicatorContext:
    items = tuple(candles)
    closes = [float(item.close) for item in items]
    sma20 = _sma(closes, 20)
    ema12_series = _ema_series(closes, 12) if closes else []
    ema26_series = _ema_series(closes, 26) if closes else []
    ema12 = ema12_series[-1] if len(closes) >= 12 else None
    ema26 = ema26_series[-1] if len(closes) >= 26 else None
    macd_series = [fast - slow for fast, slow in zip(ema12_series, ema26_series)]
    macd = macd_series[-1] if len(closes) >= 26 else None
    signal_series = _ema_series(macd_series, 9)
    macd_signal = signal_series[-1] if len(closes) >= 34 else None
    rsi14 = _rsi(closes)
    true_ranges = _true_ranges(items)
    atr14 = _sma(true_ranges, 14)
    atr_ratio = atr14 / closes[-1] if atr14 is not None and closes[-1] > 0 else None
    adx14 = _adx(items)
    bollinger_mid = sma20
    bollinger_upper = bollinger_lower = None
    if sma20 is not None:
        variance = sum((value - sma20) ** 2 for value in closes[-20:]) / 20
        deviation = sqrt(variance)
        bollinger_upper = sma20 + 2.0 * deviation
        bollinger_lower = sma20 - 2.0 * deviation
    total_volume = sum(item.volume for item in items)
    vwap = (
        sum(((item.high + item.low + item.close) / 3.0) * item.volume for item in items)
        / total_volume
        if total_volume > 0
        else None
    )

    bullish = bearish = 0
    codes: list[str] = []
    close = closes[-1] if closes else None
    if ema12 is not None and ema26 is not None:
        if ema12 > ema26:
            bullish += 1
            codes.append("INDICATOR_EMA_BULLISH")
        elif ema12 < ema26:
            bearish += 1
            codes.append("INDICATOR_EMA_BEARISH")
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            bullish += 1
            codes.append("INDICATOR_MACD_BULLISH")
        elif macd < macd_signal:
            bearish += 1
            codes.append("INDICATOR_MACD_BEARISH")
    if rsi14 is not None:
        if rsi14 >= 55.0:
            bullish += 1
            codes.append("INDICATOR_RSI_BULLISH")
        elif rsi14 <= 45.0:
            bearish += 1
            codes.append("INDICATOR_RSI_BEARISH")
        else:
            codes.append("INDICATOR_RSI_NEUTRAL")
    if close is not None and sma20 is not None:
        if close > sma20:
            bullish += 1
            codes.append("INDICATOR_PRICE_ABOVE_SMA20")
        elif close < sma20:
            bearish += 1
            codes.append("INDICATOR_PRICE_BELOW_SMA20")
    if close is not None and vwap is not None:
        if close > vwap:
            bullish += 1
            codes.append("INDICATOR_PRICE_ABOVE_VWAP")
        elif close < vwap:
            bearish += 1
            codes.append("INDICATOR_PRICE_BELOW_VWAP")

    available = len(closes) >= 26
    minimum_votes = 2
    if available and bullish >= minimum_votes and bullish >= bearish + 1:
        direction = IndicatorDirection.BULLISH
    elif available and bearish >= minimum_votes and bearish >= bullish + 1:
        direction = IndicatorDirection.BEARISH
    elif available:
        direction = IndicatorDirection.NEUTRAL
    else:
        direction = IndicatorDirection.UNAVAILABLE
        codes.append("INDICATOR_CONTEXT_INSUFFICIENT_HISTORY")
    if adx14 is not None:
        codes.append("INDICATOR_ADX_TRENDING" if adx14 >= 20.0 else "INDICATOR_ADX_WEAK_TREND")
    return TechnicalIndicatorContext(
        available,
        sma20,
        ema12,
        ema26,
        rsi14,
        macd,
        macd_signal,
        atr14,
        atr_ratio,
        adx14,
        bollinger_mid,
        bollinger_upper,
        bollinger_lower,
        vwap,
        direction,
        bullish,
        bearish,
        tuple(codes),
    )
