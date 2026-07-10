from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.market_reader.candle_morphology import (
    CandleDirection,
    CandleMorphologyAnalyzer,
)
from app.market_reader.candle_window import CandleBar, CandleWindow


def _bar(
    *,
    index: int = 0,
    open_price: float = 100.0,
    high: float = 110.0,
    low: float = 95.0,
    close: float = 108.0,
    volume: float = 10.0,
) -> CandleBar:
    return CandleBar(
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_analyze_bullish_candle_morphology_values() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=110.0, low=95.0, close=108.0)
    )

    assert morphology.direction == CandleDirection.BULLISH
    assert morphology.is_bullish is True
    assert morphology.is_bearish is False
    assert morphology.is_neutral is False
    assert morphology.body_signed == 8.0
    assert morphology.body_abs == 8.0
    assert morphology.candle_range == 15.0
    assert morphology.upper_shadow == 2.0
    assert morphology.lower_shadow == 5.0
    assert morphology.body_to_range_ratio == pytest.approx(8.0 / 15.0)
    assert morphology.upper_shadow_to_range_ratio == pytest.approx(2.0 / 15.0)
    assert morphology.lower_shadow_to_range_ratio == pytest.approx(5.0 / 15.0)
    assert morphology.close_position_in_range == pytest.approx(13.0 / 15.0)


def test_analyze_bearish_candle_direction() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=108.0, high=110.0, low=95.0, close=100.0)
    )

    assert morphology.direction == CandleDirection.BEARISH
    assert morphology.is_bullish is False
    assert morphology.is_bearish is True
    assert morphology.is_neutral is False
    assert morphology.body_signed == -8.0
    assert morphology.body_abs == 8.0


def test_analyze_neutral_zero_range_candle_is_safe() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=100.0, low=100.0, close=100.0)
    )

    assert morphology.direction == CandleDirection.NEUTRAL
    assert morphology.candle_range == 0.0
    assert morphology.body_to_range_ratio == 0.0
    assert morphology.upper_shadow_to_range_ratio == 0.0
    assert morphology.lower_shadow_to_range_ratio == 0.0
    assert morphology.close_position_in_range == 0.5
    assert morphology.is_doji_like is True
    assert morphology.is_strong_body is False
    assert morphology.has_long_upper_shadow is False
    assert morphology.has_long_lower_shadow is False


def test_analyze_doji_like_candle() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=105.0, low=95.0, close=100.5)
    )

    assert morphology.body_to_range_ratio == pytest.approx(0.05)
    assert morphology.is_doji_like is True
    assert morphology.is_strong_body is False


def test_analyze_strong_body_candle() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=109.0, low=99.0, close=108.0)
    )

    assert morphology.body_to_range_ratio == pytest.approx(0.8)
    assert morphology.is_doji_like is False
    assert morphology.is_strong_body is True


def test_analyze_long_upper_shadow() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=110.0, low=99.0, close=101.0)
    )

    assert morphology.upper_shadow == 9.0
    assert morphology.upper_shadow_to_range_ratio == pytest.approx(9.0 / 11.0)
    assert morphology.has_long_upper_shadow is True
    assert morphology.has_long_lower_shadow is False


def test_analyze_long_lower_shadow() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=102.0, low=90.0, close=101.0)
    )

    assert morphology.lower_shadow == 10.0
    assert morphology.lower_shadow_to_range_ratio == pytest.approx(10.0 / 12.0)
    assert morphology.has_long_upper_shadow is False
    assert morphology.has_long_lower_shadow is True


def test_analyze_window_returns_morphology_for_each_candle() -> None:
    window = CandleWindow.from_candles(
        symbol="BTCUSDT",
        interval="15m",
        candles=[
            _bar(index=0, close=108.0),
            _bar(index=1, open_price=108.0, close=100.0),
            _bar(index=2, open_price=100.0, high=100.0, low=100.0, close=100.0),
        ],
        min_size=3,
    )

    result = CandleMorphologyAnalyzer().analyze_window(window)

    assert len(result) == 3
    assert result[0].direction == CandleDirection.BULLISH
    assert result[1].direction == CandleDirection.BEARISH
    assert result[2].direction == CandleDirection.NEUTRAL


def test_latest_returns_latest_window_candle_morphology() -> None:
    window = CandleWindow.from_candles(
        symbol="BTCUSDT",
        interval="15m",
        candles=[
            _bar(index=0, close=108.0),
            _bar(index=1, open_price=108.0, close=100.0),
        ],
        min_size=2,
    )

    morphology = CandleMorphologyAnalyzer().latest(window)

    assert morphology.open_time == datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc)
    assert morphology.direction == CandleDirection.BEARISH


def test_morphology_to_dict_uses_plain_values() -> None:
    morphology = CandleMorphologyAnalyzer().analyze_bar(
        _bar(open_price=100.0, high=110.0, low=95.0, close=108.0)
    )

    payload = morphology.to_dict()

    assert payload["open_time"] == "2026-01-01T00:00:00+00:00"
    assert payload["direction"] == "BULLISH"
    assert payload["body_signed"] == 8.0
    assert payload["is_bullish"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"doji_body_to_range_threshold": -0.01},
        {"doji_body_to_range_threshold": 1.01},
        {"strong_body_to_range_threshold": -0.01},
        {"strong_body_to_range_threshold": 1.01},
        {"long_shadow_to_range_threshold": -0.01},
        {"long_shadow_to_range_threshold": 1.01},
    ],
)
def test_analyzer_rejects_invalid_thresholds(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        CandleMorphologyAnalyzer(**kwargs)


def test_analyzer_requires_strong_body_threshold_greater_than_doji_threshold() -> None:
    with pytest.raises(ValueError, match="greater than doji"):
        CandleMorphologyAnalyzer(
            doji_body_to_range_threshold=0.40,
            strong_body_to_range_threshold=0.30,
        )
