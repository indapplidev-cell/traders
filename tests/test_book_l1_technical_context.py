from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.market_reader.candle_window import CandleWindow
from app.market_reader.technical_context import (
    EmaTrendDirection,
    PriceEmaPosition,
    TechnicalContextAnalyzer,
    TechnicalContextResult,
    VolatilityContext,
)


def _window_from_closes(
    closes: list[float],
    *,
    high_padding: float = 1.0,
    low_padding: float = 1.0,
) -> CandleWindow:
    candles: list[dict[str, Any]] = []

    for index, close in enumerate(closes):
        open_price = closes[index - 1] if index > 0 else close
        high = max(open_price, close) + high_padding
        low = min(open_price, close) - low_padding

        candles.append(
            {
                "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 10.0 + index,
            }
        )

    return CandleWindow.from_candles(symbol="BTCUSDT", interval="15m", candles=candles)


def test_technical_context_detects_bullish_ema_context() -> None:
    window = _window_from_closes([100.0 + index for index in range(40)])

    result = TechnicalContextAnalyzer().analyze(
        window,
        fast_ema_period=5,
        slow_ema_period=12,
        atr_period=5,
        slope_lookback=3,
    )

    assert result.ema_direction == EmaTrendDirection.UP
    assert result.price_ema_position == PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW
    assert result.volatility_context == VolatilityContext.NORMAL
    assert result.fast_ema is not None
    assert result.slow_ema is not None
    assert result.fast_ema > result.slow_ema
    assert result.fast_ema_slope_pct is not None
    assert result.fast_ema_slope_pct > 0.0
    assert result.slow_ema_slope_pct is not None
    assert result.slow_ema_slope_pct > 0.0
    assert result.technical_score > 0.0
    assert result.has_technical_context is True
    assert "EMA_TREND_UP" in result.reason_codes
    assert "FAST_EMA_ABOVE_SLOW_EMA" in result.reason_codes
    assert "PRICE_ABOVE_EMAS" in result.reason_codes


def test_technical_context_detects_bearish_ema_context() -> None:
    window = _window_from_closes([140.0 - index for index in range(40)])

    result = TechnicalContextAnalyzer().analyze(
        window,
        fast_ema_period=5,
        slow_ema_period=12,
        atr_period=5,
        slope_lookback=3,
    )

    assert result.ema_direction == EmaTrendDirection.DOWN
    assert result.price_ema_position == PriceEmaPosition.BELOW_FAST_BELOW_SLOW
    assert result.volatility_context == VolatilityContext.NORMAL
    assert result.fast_ema is not None
    assert result.slow_ema is not None
    assert result.fast_ema < result.slow_ema
    assert result.fast_ema_slope_pct is not None
    assert result.fast_ema_slope_pct < 0.0
    assert result.slow_ema_slope_pct is not None
    assert result.slow_ema_slope_pct < 0.0
    assert "EMA_TREND_DOWN" in result.reason_codes
    assert "FAST_EMA_BELOW_SLOW_EMA" in result.reason_codes
    assert "PRICE_BELOW_EMAS" in result.reason_codes


def test_technical_context_detects_flat_low_volatility_context() -> None:
    window = _window_from_closes([100.0 for _ in range(40)], high_padding=0.1, low_padding=0.1)

    result = TechnicalContextAnalyzer().analyze(
        window,
        fast_ema_period=5,
        slow_ema_period=12,
        atr_period=5,
        slope_lookback=3,
        low_volatility_atr_pct=0.003,
    )

    assert result.ema_direction == EmaTrendDirection.FLAT
    assert result.price_ema_position == PriceEmaPosition.AROUND_EMAS
    assert result.volatility_context == VolatilityContext.LOW
    assert result.atr_pct is not None
    assert result.atr_pct <= 0.003
    assert "EMA_TREND_FLAT" in result.reason_codes
    assert "PRICE_AROUND_EMA" in result.reason_codes
    assert "ATR_LOW_VOLATILITY" in result.reason_codes


def test_technical_context_detects_high_volatility_context() -> None:
    window = _window_from_closes([100.0 + ((-1) ** index) * 2.0 for index in range(40)], high_padding=5.0, low_padding=5.0)

    result = TechnicalContextAnalyzer().analyze(
        window,
        fast_ema_period=5,
        slow_ema_period=12,
        atr_period=5,
        slope_lookback=3,
        high_volatility_atr_pct=0.03,
    )

    assert result.volatility_context == VolatilityContext.HIGH
    assert result.atr_pct is not None
    assert result.atr_pct >= 0.03
    assert "ATR_HIGH_VOLATILITY" in result.reason_codes


def test_technical_context_returns_unknown_when_not_enough_candles() -> None:
    window = _window_from_closes([100.0, 101.0, 102.0])

    result = TechnicalContextAnalyzer().analyze(
        window,
        fast_ema_period=5,
        slow_ema_period=12,
        atr_period=5,
        slope_lookback=3,
    )

    assert result.ema_direction == EmaTrendDirection.UNKNOWN
    assert result.price_ema_position == PriceEmaPosition.UNKNOWN
    assert result.volatility_context == VolatilityContext.UNKNOWN
    assert result.technical_score == 0.0
    assert result.candle_count == 3
    assert result.has_technical_context is False
    assert result.reason_codes == ("NOT_ENOUGH_CANDLES_FOR_TECHNICAL_CONTEXT",)


def test_technical_context_result_to_dict_uses_plain_values() -> None:
    result = TechnicalContextResult(
        ema_direction=EmaTrendDirection.UP,
        price_ema_position=PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
        volatility_context=VolatilityContext.NORMAL,
        technical_score=0.85,
        candle_count=30,
        fast_ema=110.0,
        slow_ema=105.0,
        atr=2.0,
        atr_pct=0.018,
        fast_ema_slope_pct=0.01,
        slow_ema_slope_pct=0.008,
        price_to_fast_ema_pct=0.02,
        price_to_slow_ema_pct=0.07,
        ema_spread_pct=0.047,
        reason_codes=("EMA_TREND_UP", "PRICE_ABOVE_EMAS"),
    )

    assert result.to_dict() == {
        "ema_direction": "UP",
        "price_ema_position": "ABOVE_FAST_ABOVE_SLOW",
        "volatility_context": "NORMAL",
        "technical_score": 0.85,
        "candle_count": 30,
        "fast_ema": 110.0,
        "slow_ema": 105.0,
        "atr": 2.0,
        "atr_pct": 0.018,
        "fast_ema_slope_pct": 0.01,
        "slow_ema_slope_pct": 0.008,
        "price_to_fast_ema_pct": 0.02,
        "price_to_slow_ema_pct": 0.07,
        "ema_spread_pct": 0.047,
        "has_technical_context": True,
        "reason_codes": ["EMA_TREND_UP", "PRICE_ABOVE_EMAS"],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fast_ema_period": 1},
        {"fast_ema_period": 5, "slow_ema_period": 5},
        {"fast_ema_period": 5, "slow_ema_period": 4},
        {"atr_period": 1},
        {"slope_lookback": 0},
        {"flat_slope_tolerance_pct": -0.01},
        {"around_ema_tolerance_pct": -0.01},
        {"high_volatility_atr_pct": 0.0},
        {"low_volatility_atr_pct": -0.01},
        {"low_volatility_atr_pct": 0.05, "high_volatility_atr_pct": 0.03},
    ],
)
def test_technical_context_rejects_invalid_parameters(kwargs: dict[str, Any]) -> None:
    window = _window_from_closes([100.0 + index for index in range(40)])

    with pytest.raises(ValueError):
        TechnicalContextAnalyzer().analyze(window, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": -0.01,
            "candle_count": 10,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 1.01,
            "candle_count": 10,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 0.5,
            "candle_count": -1,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 0.5,
            "candle_count": 10,
            "fast_ema": 0.0,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 0.5,
            "candle_count": 10,
            "atr": -0.01,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 0.5,
            "candle_count": 10,
            "atr_pct": -0.01,
        },
        {
            "ema_direction": EmaTrendDirection.UP,
            "price_ema_position": PriceEmaPosition.ABOVE_FAST_ABOVE_SLOW,
            "volatility_context": VolatilityContext.NORMAL,
            "technical_score": 0.5,
            "candle_count": 10,
            "slow_ema": float("nan"),
        },
    ],
)
def test_technical_context_result_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        TechnicalContextResult(**kwargs)
