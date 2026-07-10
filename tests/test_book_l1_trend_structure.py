from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.market_reader.trend_structure import (
    TrendStructureAnalyzer,
    TrendStructureDirection,
    TrendStructureResult,
    TrendSwingPoint,
)


@dataclass(frozen=True)
class DummySwingPoint:
    index: int
    open_time: datetime
    price: Any


def _point(index: int, price: Any) -> DummySwingPoint:
    return DummySwingPoint(
        index=index,
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        price=price,
    )


def test_trend_swing_point_converts_numeric_price() -> None:
    point = TrendSwingPoint.from_point(_point(3, "105.50"))

    assert point.index == 3
    assert point.price == 105.5
    assert point.open_time == datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc)


def test_trend_structure_detects_up_structure() -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=[_point(1, 100.0), _point(3, 110.0), _point(5, 120.0)],
        swing_lows=[_point(0, 90.0), _point(2, 95.0), _point(4, 103.0)],
    )

    assert result.direction == TrendStructureDirection.UP
    assert result.higher_high_count == 2
    assert result.higher_low_count == 2
    assert result.lower_high_count == 0
    assert result.lower_low_count == 0
    assert result.swing_high_count == 3
    assert result.swing_low_count == 3
    assert result.has_enough_structure is True
    assert result.strength_score == 1.0
    assert result.reason_codes == (
        "UP_TREND_STRUCTURE",
        "HIGHER_HIGHS",
        "HIGHER_LOWS",
    )


def test_trend_structure_detects_down_structure() -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=[_point(1, 120.0), _point(3, 110.0), _point(5, 100.0)],
        swing_lows=[_point(0, 105.0), _point(2, 95.0), _point(4, 90.0)],
    )

    assert result.direction == TrendStructureDirection.DOWN
    assert result.lower_high_count == 2
    assert result.lower_low_count == 2
    assert result.higher_high_count == 0
    assert result.higher_low_count == 0
    assert result.strength_score == 1.0
    assert result.reason_codes == (
        "DOWN_TREND_STRUCTURE",
        "LOWER_HIGHS",
        "LOWER_LOWS",
    )


def test_trend_structure_detects_mixed_structure() -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=[_point(1, 100.0), _point(3, 110.0), _point(5, 104.0)],
        swing_lows=[_point(0, 90.0), _point(2, 85.0), _point(4, 92.0)],
    )

    assert result.direction == TrendStructureDirection.MIXED
    assert result.higher_high_count == 1
    assert result.lower_high_count == 1
    assert result.higher_low_count == 1
    assert result.lower_low_count == 1
    assert result.reason_codes == ("MIXED_SWING_STRUCTURE",)


@pytest.mark.parametrize(
    ("swing_highs", "swing_lows"),
    [
        ([], []),
        ([_point(1, 100.0)], [_point(0, 90.0)]),
        ([_point(1, 100.0), _point(3, 110.0)], [_point(0, 90.0)]),
        ([_point(1, 100.0)], [_point(0, 90.0), _point(2, 95.0)]),
    ],
)
def test_trend_structure_returns_unknown_when_not_enough_swings(
    swing_highs: list[DummySwingPoint],
    swing_lows: list[DummySwingPoint],
) -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=swing_highs,
        swing_lows=swing_lows,
    )

    assert result.direction == TrendStructureDirection.UNKNOWN
    assert result.strength_score == 0.0
    assert result.has_enough_structure is False
    assert result.reason_codes == ("NOT_ENOUGH_SWING_POINTS",)


def test_trend_structure_counts_equal_highs_and_lows_with_tolerance() -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=[_point(1, 100.0), _point(3, 100.05), _point(5, 100.10)],
        swing_lows=[_point(0, 90.0), _point(2, 90.05), _point(4, 90.10)],
        tolerance_pct=0.002,
    )

    assert result.direction == TrendStructureDirection.MIXED
    assert result.equal_high_count == 2
    assert result.equal_low_count == 2
    assert result.higher_high_count == 0
    assert result.higher_low_count == 0


def test_trend_structure_rejects_negative_tolerance() -> None:
    with pytest.raises(ValueError, match="tolerance_pct"):
        TrendStructureAnalyzer().analyze(
            swing_highs=[],
            swing_lows=[],
            tolerance_pct=-0.01,
        )


@pytest.mark.parametrize(
    "bad_points",
    [
        [_point(3, 100.0), _point(1, 110.0)],
        [_point(3, 100.0), _point(3, 110.0)],
    ],
)
def test_trend_structure_rejects_non_increasing_swing_high_indices(
    bad_points: list[DummySwingPoint],
) -> None:
    with pytest.raises(ValueError, match="swing_highs"):
        TrendStructureAnalyzer().analyze(
            swing_highs=bad_points,
            swing_lows=[_point(0, 90.0), _point(2, 95.0)],
        )


def test_trend_structure_rejects_non_increasing_swing_low_indices() -> None:
    with pytest.raises(ValueError, match="swing_lows"):
        TrendStructureAnalyzer().analyze(
            swing_highs=[_point(1, 100.0), _point(3, 110.0)],
            swing_lows=[_point(2, 90.0), _point(2, 95.0)],
        )


def test_trend_structure_accepts_mapping_points() -> None:
    result = TrendStructureAnalyzer().analyze(
        swing_highs=[
            {"index": 1, "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc), "price": "100.0"},
            {"index": 3, "open_time": datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc), "price": "110.0"},
        ],
        swing_lows=[
            {"index": 0, "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc), "price": "90.0"},
            {"index": 2, "open_time": datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc), "price": "95.0"},
        ],
    )

    assert result.direction == TrendStructureDirection.UP
    assert result.higher_high_count == 1
    assert result.higher_low_count == 1


def test_trend_structure_can_read_detection_result_like_object() -> None:
    detection_result = SimpleNamespace(
        swing_highs=[_point(1, 100.0), _point(3, 110.0)],
        swing_lows=[_point(0, 90.0), _point(2, 95.0)],
    )

    result = TrendStructureAnalyzer().analyze_detection_result(detection_result)

    assert result.direction == TrendStructureDirection.UP
    assert result.reason_codes == (
        "UP_TREND_STRUCTURE",
        "HIGHER_HIGHS",
        "HIGHER_LOWS",
    )


def test_trend_structure_result_to_dict_uses_plain_values() -> None:
    result = TrendStructureResult(
        direction=TrendStructureDirection.UP,
        strength_score=0.75,
        higher_high_count=2,
        higher_low_count=1,
        swing_high_count=3,
        swing_low_count=2,
        reason_codes=("UP_TREND_STRUCTURE", "HIGHER_HIGHS"),
    )

    assert result.to_dict() == {
        "direction": "UP",
        "strength_score": 0.75,
        "higher_high_count": 2,
        "lower_high_count": 0,
        "equal_high_count": 0,
        "higher_low_count": 1,
        "lower_low_count": 0,
        "equal_low_count": 0,
        "swing_high_count": 3,
        "swing_low_count": 2,
        "has_enough_structure": True,
        "reason_codes": ["UP_TREND_STRUCTURE", "HIGHER_HIGHS"],
    }


@pytest.mark.parametrize("strength_score", [-0.01, 1.01])
def test_trend_structure_result_rejects_invalid_strength_score(strength_score: float) -> None:
    with pytest.raises(ValueError, match="strength_score"):
        TrendStructureResult(
            direction=TrendStructureDirection.UNKNOWN,
            strength_score=strength_score,
        )


@pytest.mark.parametrize(
    "bad_point",
    [
        {"index": -1, "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc), "price": 100.0},
        {"index": 1, "open_time": "not-datetime", "price": 100.0},
        {"index": 1, "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc), "price": 0.0},
        {"index": 1, "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc), "price": float("nan")},
    ],
)
def test_trend_swing_point_rejects_invalid_values(bad_point: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        TrendSwingPoint.from_point(bad_point)
