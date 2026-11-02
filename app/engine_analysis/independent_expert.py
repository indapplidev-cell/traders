"""Causal OHLCV-only calibration used by the production PAPER contour.

The implementation mirrors the independently verified October 2026 rubric.
Only closed candles at the supplied boundary are accepted; labels, future
extrema and project aggregate verdicts are deliberately absent.
"""

from __future__ import annotations

import itertools
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from app.engine_market_data.candle import Candle

CALIBRATION_ID = "bull-run-expert-october-2026-v1"
RUBRIC_VERSION = "independent-ohlcv-rubric/1"


@dataclass(frozen=True, slots=True)
class Indicators:
    ema9: float
    ema21: float
    sma20: float
    sma50: float
    macd: float
    macd_signal: float
    rsi14: float
    atr14: float
    adx14: float
    bollinger_mid: float
    bollinger_upper: float
    bollinger_lower: float
    vwap20: float
    volume_ratio: float


def _clip(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _score_direction(score: float, *, bullish: float = 60.0, bearish: float = 35.0) -> str:
    if score >= bullish:
        return "BULLISH"
    if score < bearish:
        return "BEARISH"
    return "NEUTRAL"


def _ema(values: Sequence[float], period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _rows(candles: Sequence[Candle], boundary_ms: int) -> list[dict[str, float | int]]:
    # Runtime snapshots use the inclusive close timestamp (..999), whereas
    # exit boundaries use the following millisecond. Both forms are causal.
    selected = [item for item in candles if item.is_closed and item.close_time_ms <= boundary_ms][-60:]
    return [{
        "open_time_ms": item.open_time_ms,
        "close_time_ms": item.close_time_ms,
        "open": float(item.open), "high": float(item.high), "low": float(item.low),
        "close": float(item.close), "volume": float(item.volume),
    } for item in selected]


def _rsi(values: Sequence[float], period: int = 14) -> float:
    changes = [right - left for left, right in itertools.pairwise(values)][-period:]
    if not changes:
        return 50.0
    gain = sum(max(0.0, value) for value in changes) / len(changes)
    loss = sum(max(0.0, -value) for value in changes) / len(changes)
    return 100.0 if loss == 0 and gain > 0 else (50.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss))


def _atr(rows: Sequence[Mapping[str, float | int]], period: int = 14) -> float:
    ranges, previous = [], None
    for row in rows[-(period + 1):]:
        high, low, close = (float(row[name]) for name in ("high", "low", "close"))
        ranges.append(high - low if previous is None else max(high - low, abs(high - previous), abs(low - previous)))
        previous = close
    return sum(ranges[-period:]) / max(1, min(period, len(ranges)))


def _adx(rows: Sequence[Mapping[str, float | int]], period: int = 14) -> float:
    plus = minus = true_range = 0.0
    for left, right in itertools.pairwise(rows[-(period + 1):]):
        up, down = float(right["high"]) - float(left["high"]), float(left["low"]) - float(right["low"])
        plus += up if up > down and up > 0 else 0.0
        minus += down if down > up and down > 0 else 0.0
        true_range += max(float(right["high"]) - float(right["low"]), abs(float(right["high"]) - float(left["close"])), abs(float(right["low"]) - float(left["close"])))
    if true_range <= 0:
        return 0.0
    plus_di, minus_di = 100.0 * plus / true_range, 100.0 * minus / true_range
    return 100.0 * abs(plus_di - minus_di) / max(1e-12, plus_di + minus_di)


def _indicators(rows: Sequence[Mapping[str, float | int]]) -> Indicators:
    if len(rows) < 20:
        raise ValueError("EXPERT_MINIMUM_20_CLOSED_CANDLES")
    closes, volumes = [float(row["close"]) for row in rows], [float(row["volume"]) for row in rows]
    ema12, ema26 = _ema(closes, 12), _ema(closes, 26)
    macd_series = [_ema(closes[:index], 12) - _ema(closes[:index], 26) for index in range(max(2, len(closes) - 20), len(closes) + 1)]
    sample = closes[-20:]
    middle, deviation = sum(sample) / len(sample), statistics.pstdev(sample)
    recent = rows[-20:]
    volume_total = sum(float(row["volume"]) for row in recent)
    vwap = sum(float(row["close"]) * float(row["volume"]) for row in recent) / volume_total if volume_total > 0 else middle
    baseline_volume = sum(volumes[-20:-5]) / max(1, len(volumes[-20:-5]))
    recent_volume = sum(volumes[-5:]) / max(1, len(volumes[-5:]))
    return Indicators(_ema(closes, 9), _ema(closes, 21), middle,
        sum(closes[-50:]) / min(50, len(closes)), ema12 - ema26, _ema(macd_series, 9),
        _rsi(closes), _atr(rows), _adx(rows), middle, middle + 2 * deviation,
        middle - 2 * deviation, vwap, recent_volume / baseline_volume if baseline_volume > 0 else 1.0)


def _regime(rows: Sequence[Mapping[str, float | int]], indicators: Indicators) -> str:
    current, prior = rows[-1], rows[-11:-1]
    close, low, resistance = float(current["close"]), float(current["low"]), max(float(row["high"]) for row in prior)
    tolerance = max(indicators.atr14 * 0.25, close * 0.0005)
    if close > resistance and indicators.volume_ratio >= 1.05:
        return "IMPULSE_BREAKOUT"
    crossed = any(float(row["close"]) > max(float(item["high"]) for item in rows[max(0, index - 10):index])
                  for index, row in enumerate(rows[-6:], start=len(rows) - 6) if index >= 10)
    return "BREAKOUT_RETEST" if crossed and low <= resistance + tolerance and close >= resistance - tolerance else "LOCAL_LOW_RECOVERY"


def entry_verdict(symbol: str, boundary_ms: int, candles_1m: Sequence[Candle], candles_5m: Sequence[Candle]) -> dict[str, object]:
    one, five = _rows(candles_1m, boundary_ms), _rows(candles_5m, boundary_ms)
    i1, i5 = _indicators(one), _indicators(five)
    current, previous, close, recent = five[-1], five[-2], float(five[-1]["close"]), five[-7:-1]
    higher_high = float(current["high"]) >= max(float(row["high"]) for row in recent)
    higher_low = float(current["low"]) >= min(float(row["low"]) for row in recent[-3:])
    structure = 50.0 + 25.0 * higher_high + 25.0 * higher_low
    resistance = max(float(row["high"]) for row in five[-11:-1])
    breakout, near_retest = close > resistance, abs(close - resistance) <= max(i5.atr14 * 0.35, close * 0.001)
    breakout_score = 100.0 if breakout else (75.0 if near_retest and close > float(previous["close"]) else 35.0)
    candle_range = max(1e-12, float(current["high"]) - float(current["low"]))
    candle_score = _clip(50.0 + 50.0 * ((float(current["close"]) - float(current["open"])) / candle_range))
    alignment = 100.0 if i1.ema9 > i1.ema21 and i5.ema9 > i5.ema21 else (65.0 if i1.ema9 > i1.ema21 or i5.ema9 > i5.ema21 else 20.0)
    invalidation = 100.0 if close > i5.vwap20 and close > i5.bollinger_lower else 35.0
    graphical = .35 * structure + .25 * breakout_score + .15 * candle_score + .15 * alignment + .10 * invalidation
    trend = 100.0 if i1.ema9 > i1.ema21 and i5.ema9 > i5.ema21 else alignment
    macd = 100.0 if i1.macd > i1.macd_signal and i5.macd >= i5.macd_signal else 40.0
    rsi = 100.0 if 52 <= i1.rsi14 <= 75 else (65.0 if 45 <= i1.rsi14 < 80 else 20.0)
    adx, vwap = _clip(i5.adx14 * 2.0), 100.0 if close >= i5.vwap20 else 25.0
    volume = _clip(50.0 + (i1.volume_ratio - 1.0) * 100.0)
    volatility = 100.0 if i5.bollinger_lower < close < i5.bollinger_upper * 1.01 else 45.0
    technical = .25 * trend + .15 * macd + .10 * rsi + .15 * adx + .15 * vwap + .10 * volume + .10 * volatility
    # The original book modules intentionally remain conservative.  This
    # explicit interaction projection adapts their evidence to the 5-30 minute
    # scalp horizon instead of silently replacing their verdict downstream.
    altunina_score = _clip(structure)
    schwager_score = _clip(breakout_score)
    nison_score = _clip(candle_score)
    calibrated_modules = {
        "altunina": {
            "direction": (
                "BULLISH" if higher_low and (higher_high or alignment >= 65.0)
                else "BEARISH" if not higher_low and close < i5.vwap20
                else "NEUTRAL"
            ),
            "score": altunina_score,
            "higher_high": higher_high,
            "higher_low": higher_low,
        },
        "schwager": {
            "direction": "BULLISH" if breakout or (
                near_retest and close > float(previous["close"])
            ) else "NEUTRAL",
            "score": schwager_score,
            "breakout": breakout,
            "retest": bool(near_retest and not breakout),
        },
        "nison": {
            "direction": (
                "BULLISH" if close > float(current["open"]) and nison_score >= 55.0
                else "BEARISH" if close < float(current["open"]) and nison_score <= 45.0
                else "NEUTRAL"
            ),
            "score": nison_score,
            "bullish_body": close > float(current["open"]),
        },
        "technical": {
            "direction": _score_direction(technical),
            "score": _clip(technical),
        },
    }
    bullish_modules = tuple(
        name for name, value in calibrated_modules.items()
        if value["direction"] == "BULLISH"
    )
    bearish_modules = tuple(
        name for name, value in calibrated_modules.items()
        if value["direction"] == "BEARISH"
    )
    consensus = (
        "BULLISH" if len(bullish_modules) >= 2 and len(bearish_modules) <= 1
        else "BEARISH" if len(bearish_modules) >= 2
        else "NEUTRAL"
    )
    module_calibration = {
        "contract_version": "scalping-module-interaction/1",
        "direction": consensus,
        "confirmed": consensus == "BULLISH",
        "bullish_modules": bullish_modules,
        "bearish_modules": bearish_modules,
        "modules": calibrated_modules,
    }
    components = {"structure": _clip(graphical), "context": _clip((alignment + trend) / 2),
        "momentum": _clip((macd + rsi + adx) / 3), "volume": volume,
        "entry_quality": _clip((breakout_score + candle_score + invalidation) / 3),
        "liquidity": 100.0, "confirmation": _clip((candle_score + alignment + macd) / 3)}
    strength = (graphical + technical) / 2
    return {"calibration_id": CALIBRATION_ID, "rubric_version": RUBRIC_VERSION,
        "symbol": symbol, "boundary_ms": boundary_ms, "regime": _regime(five, i5),
        "direction": consensus, "module_calibration": module_calibration,
        "strength": _clip(strength), "confidence": _clip(abs(strength - 50) * 2),
        "graphical_score": _clip(graphical), "technical_score": _clip(technical),
        "entry_components": components, "indicators": {"1m_" + k: v for k, v in asdict(i1).items()} | {"5m_" + k: v for k, v in asdict(i5).items()},
        "source_open_times_ms": [int(row["open_time_ms"]) for row in one + five],
        "future_bars_used": False}


def exit_components(boundary_ms: int, candles_1m: Sequence[Candle], candles_5m: Sequence[Candle], *, entry_price: float, net_profit_bps: float | None) -> dict[str, object]:
    one, five = _rows(candles_1m, boundary_ms), _rows(candles_5m, boundary_ms)
    i1 = _indicators(one)
    _indicators(five)  # Enforce the same closed-5m availability contract as entry.
    current, previous, close = one[-1], one[-2], float(one[-1]["close"])
    bearish_body, lower_close, lost_fast_ema = close < float(current["open"]), close < float(previous["close"]), close < i1.ema9
    below_vwap = close < i1.vwap20
    lower_high = float(current["high"]) < max(float(row["high"]) for row in one[-5:-1])
    graphical = _clip(15 + 25 * lower_high + 25 * bearish_body + 20 * lower_close + 15 * lost_fast_ema)
    macd_weak, rsi_rollover = i1.macd <= i1.macd_signal, i1.rsi14 < 55 or i1.rsi14 > 78
    technical = _clip(10 + 30 * macd_weak + 20 * rsi_rollover + 25 * lost_fast_ema + 15 * below_vwap)
    volume_decay = i1.volume_ratio < .90
    peak_close = max(float(row["close"]) for row in one)
    distance_from_peak = max(0.0, (peak_close - close) / max(1e-12, peak_close) * 10_000.0)
    momentum = _clip(10 + 35 * volume_decay + 25 * lower_close + min(30.0, distance_from_peak * 2.0))
    gross = (close / entry_price - 1.0) * 10_000.0
    economics = 100.0 if net_profit_bps is not None and net_profit_bps >= 8.0 else _clip(gross * 4.0)
    return {"calibration_id": CALIBRATION_ID, "rubric_version": RUBRIC_VERSION,
        "component_values": {"graphical_structure": graphical, "technical_indicators": technical,
            "momentum_volume": momentum, "holding_economics": economics},
        "strong_reversal": bool(lower_high and bearish_body and lost_fast_ema and macd_weak),
        "future_bars_used": False}


def weighted_score(components: Mapping[str, float], weights: Mapping[str, float]) -> float:
    return sum(float(components[name]) * float(weights[name]) / 100.0 for name in components)


__all__ = ("CALIBRATION_ID", "RUBRIC_VERSION", "entry_verdict", "exit_components", "weighted_score")
