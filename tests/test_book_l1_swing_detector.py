from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.market_reader import SwingDetector as ExportedSwingDetector
from app.market_reader import SwingPoint, SwingPointType
from app.market_reader.candle_window import CandleWindow
from app.market_reader.swing_detector import SwingDetector


def _window(*, highs: list[float], lows: list[float]) -> CandleWindow:
    assert len(highs) == len(lows)
    candles = []
    for index, (high, low) in enumerate(zip(highs, lows)):
        middle = (high + low) / 2
        candles.append(
            {
                "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
                "open": middle,
                "high": high,
                "low": low,
                "close": middle,
                "volume": 100.0 + index,
            }
        )
    return CandleWindow.from_candles(symbol="BTCUSDT", interval="15m", candles=candles, min_size=1)


def test_swing_detector_is_exported_from_package() -> None:
    assert ExportedSwingDetector is SwingDetector
    assert SwingPointType.HIGH.value == "HIGH"
    assert SwingPointType.LOW.value == "LOW"


def test_detects_single_swing_high() -> None:
    window = _window(highs=[10.0, 15.0, 11.0], lows=[8.0, 9.0, 8.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert points == (
        SwingPoint(
            point_type=SwingPointType.HIGH,
            index=1,
            open_time=datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc),
            price=15.0,
            left_strength=5.0,
            right_strength=4.0,
        ),
    )


def test_detects_single_swing_low() -> None:
    window = _window(highs=[12.0, 11.0, 12.0], lows=[8.0, 5.0, 8.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert points == (
        SwingPoint(
            point_type=SwingPointType.LOW,
            index=1,
            open_time=datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc),
            price=5.0,
            left_strength=3.0,
            right_strength=3.0,
        ),
    )


def test_detects_multiple_points_in_chronological_order() -> None:
    window = _window(
        highs=[10.0, 15.0, 11.0, 13.0, 9.0],
        lows=[8.0, 9.0, 7.0, 8.0, 6.0],
    )

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert [(point.point_type, point.index, point.price) for point in points] == [
        (SwingPointType.HIGH, 1, 15.0),
        (SwingPointType.LOW, 2, 7.0),
        (SwingPointType.HIGH, 3, 13.0),
    ]


def test_ignores_edge_candles_because_they_are_not_confirmed() -> None:
    window = _window(highs=[20.0, 10.0, 9.0, 21.0], lows=[8.0, 7.0, 6.0, 5.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert points == ()


def test_respects_left_and_right_window_size() -> None:
    window = _window(
        highs=[10.0, 11.0, 20.0, 12.0, 10.0],
        lows=[8.0, 8.5, 9.0, 8.5, 8.0],
    )

    points = SwingDetector(left_window=2, right_window=2).detect(window)

    assert len(points) == 1
    assert points[0].point_type == SwingPointType.HIGH
    assert points[0].index == 2
    assert points[0].price == 20.0


def test_plateau_high_is_not_a_swing_high() -> None:
    window = _window(highs=[10.0, 15.0, 15.0, 11.0], lows=[8.0, 9.0, 9.0, 8.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert SwingDetector.highs(points) == ()


def test_plateau_low_is_not_a_swing_low() -> None:
    window = _window(highs=[12.0, 11.0, 11.0, 12.0], lows=[8.0, 5.0, 5.0, 9.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert SwingDetector.lows(points) == ()


def test_returns_empty_when_window_is_too_small_for_confirmation() -> None:
    window = _window(highs=[10.0, 15.0], lows=[8.0, 9.0])

    points = SwingDetector(left_window=1, right_window=1).detect(window)

    assert points == ()


@pytest.mark.parametrize(
    "left_window,right_window,error_match",
    [
        (0, 1, "left_window"),
        (1, 0, "right_window"),
        (-1, 1, "left_window"),
        (1, -1, "right_window"),
    ],
)
def test_rejects_invalid_window_sizes(left_window: int, right_window: int, error_match: str) -> None:
    with pytest.raises(ValueError, match=error_match):
        SwingDetector(left_window=left_window, right_window=right_window)


def test_filters_highs_and_lows() -> None:
    window = _window(
        highs=[10.0, 15.0, 11.0, 13.0, 9.0],
        lows=[8.0, 9.0, 7.0, 8.0, 6.0],
    )
    points = SwingDetector(left_window=1, right_window=1).detect(window)

    highs = SwingDetector.highs(points)
    lows = SwingDetector.lows(points)

    assert [(point.index, point.price) for point in highs] == [(1, 15.0), (3, 13.0)]
    assert [(point.index, point.price) for point in lows] == [(2, 7.0)]


def test_swing_point_to_dict_uses_plain_values() -> None:
    point = SwingPoint(
        point_type=SwingPointType.HIGH,
        index=3,
        open_time=datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc),
        price=13.0,
        left_strength=2.0,
        right_strength=4.0,
    )

    assert point.to_dict() == {
        "point_type": "HIGH",
        "index": 3,
        "open_time": "2026-01-01T00:45:00+00:00",
        "price": 13.0,
        "left_strength": 2.0,
        "right_strength": 4.0,
    }
