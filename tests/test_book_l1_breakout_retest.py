from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.market_reader.breakout_retest import (
    BreakoutDirection,
    BreakoutRetestAnalyzer,
    BreakoutRetestClassification,
    BreakoutRetestResult,
)
from app.market_reader.candle_window import CandleWindow


def _window(rows: list[dict[str, Any]]) -> CandleWindow:
    candles: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        open_price = float(row.get("open", row["close"]))
        close_price = float(row["close"])
        high = float(row.get("high", max(open_price, close_price) + 1.0))
        low = float(row.get("low", min(open_price, close_price) - 1.0))
        candles.append(
            {
                "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": float(row.get("volume", 10.0)),
            }
        )
    return CandleWindow.from_candles(symbol="BTCUSDT", interval="15m", candles=candles)


def test_breakout_retest_detects_bullish_close_breakout() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 111.0, "close": 103.0},
            {"low": 100.0, "high": 112.0, "close": 112.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.BULLISH_BREAKOUT
    assert result.breakout_direction == BreakoutDirection.BULLISH
    assert result.breakout_level == 111.0
    assert result.breakout_index == 3
    assert result.has_breakout is True
    assert result.follow_through_count == 1
    assert result.latest_close == 112.0
    assert "BULLISH_CLOSE_BREAKOUT" in result.reason_codes
    assert "BULLISH_FOLLOW_THROUGH" in result.reason_codes


def test_breakout_retest_detects_bearish_close_breakout() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 98.8, "high": 111.0, "close": 103.0},
            {"low": 96.5, "high": 101.0, "close": 97.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.BEARISH_BREAKOUT
    assert result.breakout_direction == BreakoutDirection.BEARISH
    assert result.breakout_level == 99.0
    assert result.breakout_index == 3
    assert result.has_breakout is True
    assert result.follow_through_count == 1
    assert "BEARISH_CLOSE_BREAKOUT" in result.reason_codes
    assert "BEARISH_FOLLOW_THROUGH" in result.reason_codes


def test_breakout_retest_detects_bullish_breakout_retest() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 100.5, "high": 113.0, "close": 112.0},
            {"low": 110.8, "high": 114.0, "close": 112.5},
            {"low": 112.0, "high": 115.0, "close": 114.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
        retest_tolerance_pct=0.003,
    )

    assert result.classification == BreakoutRetestClassification.BULLISH_BREAKOUT_RETEST
    assert result.breakout_direction == BreakoutDirection.BULLISH
    assert result.retest_detected is True
    assert result.follow_through_count >= 2
    assert "BULLISH_RETEST_CONFIRMED" in result.reason_codes


def test_breakout_retest_detects_bearish_breakout_retest() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 96.0, "high": 100.5, "close": 97.0},
            {"low": 95.0, "high": 99.2, "close": 97.5},
            {"low": 94.0, "high": 98.0, "close": 95.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
        retest_tolerance_pct=0.003,
    )

    assert result.classification == BreakoutRetestClassification.BEARISH_BREAKOUT_RETEST
    assert result.breakout_direction == BreakoutDirection.BEARISH
    assert result.retest_detected is True
    assert result.follow_through_count >= 2
    assert "BEARISH_RETEST_CONFIRMED" in result.reason_codes


def test_breakout_retest_detects_false_bullish_wick_breakout() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 101.0, "high": 113.0, "close": 110.5},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.FALSE_BULLISH_BREAKOUT
    assert result.breakout_direction == BreakoutDirection.BULLISH
    assert result.false_breakout_detected is True
    assert "BULLISH_WICK_BREAKOUT" in result.reason_codes
    assert "FALSE_BULLISH_BREAKOUT" in result.reason_codes


def test_breakout_retest_detects_false_bearish_wick_breakout() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 97.0, "high": 106.0, "close": 99.5},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.FALSE_BEARISH_BREAKOUT
    assert result.breakout_direction == BreakoutDirection.BEARISH
    assert result.false_breakout_detected is True
    assert "BEARISH_WICK_BREAKOUT" in result.reason_codes
    assert "FALSE_BEARISH_BREAKOUT" in result.reason_codes


def test_breakout_retest_detects_false_bullish_close_breakout_after_return_inside() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 113.0, "close": 112.0},
            {"low": 100.0, "high": 110.0, "close": 109.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.FALSE_BULLISH_BREAKOUT
    assert result.false_breakout_detected is True
    assert "CLOSE_RETURNED_INSIDE_RANGE" in result.reason_codes


def test_breakout_retest_detects_false_bearish_close_breakout_after_return_inside() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 96.0, "high": 100.0, "close": 97.0},
            {"low": 99.0, "high": 104.0, "close": 100.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.FALSE_BEARISH_BREAKOUT
    assert result.false_breakout_detected is True
    assert "CLOSE_RETURNED_INSIDE_RANGE" in result.reason_codes


def test_breakout_retest_returns_inside_range_without_breakout() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 110.5, "close": 105.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
    )

    assert result.classification == BreakoutRetestClassification.INSIDE_RANGE
    assert result.breakout_direction == BreakoutDirection.NONE
    assert result.breakout_score == 0.0
    assert result.has_breakout is False
    assert result.reason_codes == ("NO_CLOSE_BREAKOUT", "PRICE_INSIDE_RANGE")


def test_breakout_retest_returns_unknown_without_range_boundaries() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(window)

    assert result.classification == BreakoutRetestClassification.UNKNOWN
    assert result.breakout_direction == BreakoutDirection.UNKNOWN
    assert result.breakout_score == 0.0
    assert result.reason_codes == ("NO_RANGE_BOUNDARIES_FOR_BREAKOUT_ANALYSIS",)


def test_breakout_retest_reads_range_result_object() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 113.0, "close": 112.0},
        ]
    )
    range_result = SimpleNamespace(support_level=99.0, resistance_level=111.0)

    result = BreakoutRetestAnalyzer().analyze(
        window,
        range_result=range_result,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.BULLISH_BREAKOUT
    assert result.support_level == 99.0
    assert result.resistance_level == 111.0


def test_breakout_retest_reads_range_result_mapping() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 96.0, "high": 100.0, "close": 97.0},
        ]
    )
    range_result = {"support_level": 99.0, "resistance_level": 111.0}

    result = BreakoutRetestAnalyzer().analyze(
        window,
        range_result=range_result,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.BEARISH_BREAKOUT
    assert result.support_level == 99.0
    assert result.resistance_level == 111.0


def test_breakout_retest_direct_levels_override_range_result() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 113.0, "close": 112.0},
        ]
    )
    range_result = {"support_level": 50.0, "resistance_level": 200.0}

    result = BreakoutRetestAnalyzer().analyze(
        window,
        range_result=range_result,
        support_level=99.0,
        resistance_level=111.0,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.BULLISH_BREAKOUT
    assert result.support_level == 99.0
    assert result.resistance_level == 111.0


def test_breakout_retest_uses_latest_lookback_only() -> None:
    window = _window(
        [
            {"low": 100.0, "high": 150.0, "close": 140.0},
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 110.5, "close": 105.0},
        ]
    )

    result = BreakoutRetestAnalyzer().analyze(
        window,
        support_level=99.0,
        resistance_level=111.0,
        lookback=3,
        breakout_tolerance_pct=0.001,
    )

    assert result.classification == BreakoutRetestClassification.INSIDE_RANGE
    assert result.candle_count == 3


def test_breakout_retest_result_to_dict_uses_plain_values() -> None:
    open_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = BreakoutRetestResult(
        classification=BreakoutRetestClassification.BULLISH_BREAKOUT_RETEST,
        breakout_direction=BreakoutDirection.BULLISH,
        breakout_score=0.85,
        support_level=99.0,
        resistance_level=111.0,
        breakout_level=111.0,
        breakout_index=3,
        breakout_open_time=open_time,
        latest_close=114.0,
        breakout_distance_pct=0.027,
        retest_detected=True,
        false_breakout_detected=False,
        follow_through_count=3,
        candle_count=5,
        reason_codes=("BULLISH_CLOSE_BREAKOUT", "BULLISH_RETEST_CONFIRMED"),
    )

    assert result.to_dict() == {
        "classification": "BULLISH_BREAKOUT_RETEST",
        "breakout_direction": "BULLISH",
        "breakout_score": 0.85,
        "support_level": 99.0,
        "resistance_level": 111.0,
        "breakout_level": 111.0,
        "breakout_index": 3,
        "breakout_open_time": "2026-01-01T00:00:00+00:00",
        "latest_close": 114.0,
        "breakout_distance_pct": 0.027,
        "retest_detected": True,
        "false_breakout_detected": False,
        "follow_through_count": 3,
        "candle_count": 5,
        "has_breakout": True,
        "reason_codes": ["BULLISH_CLOSE_BREAKOUT", "BULLISH_RETEST_CONFIRMED"],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lookback": 0},
        {"breakout_tolerance_pct": -0.01},
        {"retest_tolerance_pct": -0.01},
        {"min_follow_through_count": -1},
    ],
)
def test_breakout_retest_rejects_invalid_parameters(kwargs: dict[str, Any]) -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
        ]
    )

    with pytest.raises(ValueError):
        BreakoutRetestAnalyzer().analyze(
            window,
            support_level=99.0,
            resistance_level=111.0,
            **kwargs,
        )


@pytest.mark.parametrize(
    ("support_level", "resistance_level"),
    [
        (0.0, 111.0),
        (99.0, 0.0),
        (111.0, 99.0),
        (99.0, 99.0),
        (float("nan"), 111.0),
    ],
)
def test_breakout_retest_rejects_invalid_levels(
    support_level: float,
    resistance_level: float,
) -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
        ]
    )

    with pytest.raises(ValueError):
        BreakoutRetestAnalyzer().analyze(
            window,
            support_level=support_level,
            resistance_level=resistance_level,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": -0.01,
        },
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": 1.01,
        },
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": 0.5,
            "breakout_distance_pct": -0.01,
        },
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": 0.5,
            "follow_through_count": -1,
        },
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": 0.5,
            "candle_count": -1,
        },
        {
            "classification": BreakoutRetestClassification.BULLISH_BREAKOUT,
            "breakout_direction": BreakoutDirection.BULLISH,
            "breakout_score": 0.5,
            "breakout_index": -1,
        },
    ],
)
def test_breakout_retest_result_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        BreakoutRetestResult(**kwargs)
