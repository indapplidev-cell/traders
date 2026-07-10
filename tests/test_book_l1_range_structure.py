from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.market_reader.candle_window import CandleWindow
from app.market_reader.range_structure import (
    RangeStructureAnalyzer,
    RangeStructureClassification,
    RangeStructureResult,
)


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


def test_range_structure_detects_sideways_range() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 111.0, "close": 103.0},
            {"low": 100.0, "high": 110.5, "close": 105.0},
            {"low": 99.2, "high": 109.8, "close": 104.5},
            {"low": 100.1, "high": 110.2, "close": 105.5},
        ]
    )

    result = RangeStructureAnalyzer().analyze(
        window,
        lookback=6,
        boundary_tolerance_pct=0.02,
        max_range_width_pct=0.12,
        max_close_drift_ratio=0.60,
        min_boundary_touch_count=2,
    )

    assert result.classification == RangeStructureClassification.RANGE
    assert result.support_level == pytest.approx(99.0)
    assert result.resistance_level == pytest.approx(111.0)
    assert result.range_width == pytest.approx(12.0)
    assert result.range_width_pct == pytest.approx(12.0 / 105.0)
    assert result.range_position == pytest.approx((105.5 - 99.0) / 12.0)
    assert result.support_touch_count >= 2
    assert result.resistance_touch_count >= 2
    assert result.inside_close_ratio == 1.0
    assert result.range_score > 0.0
    assert "RANGE_STRUCTURE_DETECTED" in result.reason_codes
    assert "SUPPORT_TOUCHES_DETECTED" in result.reason_codes
    assert "RESISTANCE_TOUCHES_DETECTED" in result.reason_codes


def test_range_structure_returns_unknown_when_not_enough_candles() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
        ]
    )

    result = RangeStructureAnalyzer().analyze(window, min_size=5)

    assert result.classification == RangeStructureClassification.UNKNOWN
    assert result.range_score == 0.0
    assert result.candle_count == 2
    assert result.reason_codes == ("NOT_ENOUGH_CANDLES_FOR_RANGE_STRUCTURE",)


def test_range_structure_marks_too_wide_range_as_not_range() -> None:
    window = _window(
        [
            {"low": 80.0, "high": 130.0, "close": 100.0},
            {"low": 81.0, "high": 129.0, "close": 101.0},
            {"low": 80.5, "high": 130.5, "close": 99.0},
            {"low": 81.2, "high": 129.8, "close": 102.0},
            {"low": 80.8, "high": 130.2, "close": 100.5},
        ]
    )

    result = RangeStructureAnalyzer().analyze(
        window,
        lookback=5,
        boundary_tolerance_pct=0.02,
        max_range_width_pct=0.10,
        min_boundary_touch_count=2,
    )

    assert result.classification == RangeStructureClassification.NOT_RANGE
    assert "RANGE_TOO_WIDE" in result.reason_codes


def test_range_structure_marks_weak_boundary_touches_as_not_range() -> None:
    window = _window(
        [
            {"low": 95.0, "high": 101.0, "close": 100.0},
            {"low": 97.0, "high": 104.0, "close": 103.0},
            {"low": 99.0, "high": 106.0, "close": 105.0},
            {"low": 101.0, "high": 108.0, "close": 107.0},
            {"low": 103.0, "high": 110.0, "close": 109.0},
        ]
    )

    result = RangeStructureAnalyzer().analyze(
        window,
        lookback=5,
        boundary_tolerance_pct=0.001,
        max_range_width_pct=0.20,
        min_boundary_touch_count=2,
    )

    assert result.classification == RangeStructureClassification.NOT_RANGE
    assert "WEAK_BOUNDARY_TOUCHES" in result.reason_codes


def test_range_structure_marks_directional_close_drift_as_not_range() -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 100.0},
            {"low": 100.0, "high": 109.0, "close": 102.0},
            {"low": 99.5, "high": 111.0, "close": 104.0},
            {"low": 100.0, "high": 110.5, "close": 106.0},
            {"low": 99.2, "high": 109.8, "close": 108.0},
            {"low": 100.1, "high": 110.2, "close": 109.5},
        ]
    )

    result = RangeStructureAnalyzer().analyze(
        window,
        lookback=6,
        boundary_tolerance_pct=0.02,
        max_range_width_pct=0.12,
        max_close_drift_ratio=0.50,
        min_boundary_touch_count=2,
    )

    assert result.classification == RangeStructureClassification.NOT_RANGE
    assert "DIRECTIONAL_CLOSE_DRIFT" in result.reason_codes


def test_range_structure_uses_latest_lookback_only() -> None:
    window = _window(
        [
            {"low": 50.0, "high": 200.0, "close": 100.0},
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 111.0, "close": 103.0},
            {"low": 100.0, "high": 110.5, "close": 105.0},
            {"low": 99.2, "high": 109.8, "close": 104.5},
        ]
    )

    result = RangeStructureAnalyzer().analyze(
        window,
        lookback=5,
        boundary_tolerance_pct=0.02,
        max_range_width_pct=0.12,
        min_boundary_touch_count=2,
    )

    assert result.support_level == pytest.approx(99.0)
    assert result.resistance_level == pytest.approx(111.0)
    assert result.candle_count == 5


def test_range_structure_result_to_dict_uses_plain_values() -> None:
    result = RangeStructureResult(
        classification=RangeStructureClassification.RANGE,
        range_score=0.75,
        support_level=100.0,
        resistance_level=110.0,
        range_width=10.0,
        range_width_pct=0.095,
        range_position=0.5,
        support_touch_count=3,
        resistance_touch_count=2,
        inside_close_ratio=1.0,
        close_drift_ratio=0.2,
        candle_count=20,
        reason_codes=("RANGE_STRUCTURE_DETECTED",),
    )

    assert result.to_dict() == {
        "classification": "RANGE",
        "range_score": 0.75,
        "support_level": 100.0,
        "resistance_level": 110.0,
        "range_width": 10.0,
        "range_width_pct": 0.095,
        "range_position": 0.5,
        "support_touch_count": 3,
        "resistance_touch_count": 2,
        "inside_close_ratio": 1.0,
        "close_drift_ratio": 0.2,
        "candle_count": 20,
        "has_range_boundaries": True,
        "reason_codes": ["RANGE_STRUCTURE_DETECTED"],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lookback": 0},
        {"min_size": 0},
        {"boundary_tolerance_pct": -0.01},
        {"max_range_width_pct": 0.0},
        {"max_close_drift_ratio": 0.0},
        {"min_boundary_touch_count": 0},
    ],
)
def test_range_structure_rejects_invalid_parameters(kwargs: dict[str, Any]) -> None:
    window = _window(
        [
            {"low": 99.0, "high": 110.0, "close": 104.0},
            {"low": 100.0, "high": 109.0, "close": 106.0},
            {"low": 99.5, "high": 111.0, "close": 103.0},
            {"low": 100.0, "high": 110.5, "close": 105.0},
            {"low": 99.2, "high": 109.8, "close": 104.5},
        ]
    )

    with pytest.raises(ValueError):
        RangeStructureAnalyzer().analyze(window, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"classification": RangeStructureClassification.RANGE, "range_score": -0.01},
        {"classification": RangeStructureClassification.RANGE, "range_score": 1.01},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "range_position": -0.01},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "range_position": 1.01},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "inside_close_ratio": 1.01},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "support_touch_count": -1},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "resistance_touch_count": -1},
        {"classification": RangeStructureClassification.RANGE, "range_score": 0.5, "candle_count": -1},
    ],
)
def test_range_structure_result_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        RangeStructureResult(**kwargs)
