from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.market_reader.candle_window import CandleWindow


class SwingPointType(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass(frozen=True)
class SwingPoint:
    point_type: SwingPointType
    index: int
    open_time: datetime
    price: float
    left_strength: float
    right_strength: float

    def to_dict(self) -> dict[str, object]:
        return {
            "point_type": self.point_type.value,
            "index": self.index,
            "open_time": self.open_time.isoformat(),
            "price": self.price,
            "left_strength": self.left_strength,
            "right_strength": self.right_strength,
        }


class SwingDetector:
    def __init__(self, *, left_window: int = 2, right_window: int = 2) -> None:
        if left_window <= 0:
            raise ValueError("left_window must be positive")
        if right_window <= 0:
            raise ValueError("right_window must be positive")

        self.left_window = left_window
        self.right_window = right_window

    def detect(self, window: CandleWindow) -> tuple[SwingPoint, ...]:
        required_size = self.left_window + self.right_window + 1
        if window.size < required_size:
            return ()

        points: list[SwingPoint] = []
        highs = window.highs
        lows = window.lows

        start_index = self.left_window
        end_index = window.size - self.right_window

        for index in range(start_index, end_index):
            if self._is_swing_high(highs, index):
                points.append(self._build_swing_high(window, index))

            if self._is_swing_low(lows, index):
                points.append(self._build_swing_low(window, index))

        return tuple(points)

    @staticmethod
    def highs(points: tuple[SwingPoint, ...]) -> tuple[SwingPoint, ...]:
        return tuple(point for point in points if point.point_type == SwingPointType.HIGH)

    @staticmethod
    def lows(points: tuple[SwingPoint, ...]) -> tuple[SwingPoint, ...]:
        return tuple(point for point in points if point.point_type == SwingPointType.LOW)

    def _is_swing_high(self, highs: tuple[float, ...], index: int) -> bool:
        current = highs[index]
        left_values = highs[index - self.left_window : index]
        right_values = highs[index + 1 : index + 1 + self.right_window]
        return current > max(left_values) and current > max(right_values)

    def _is_swing_low(self, lows: tuple[float, ...], index: int) -> bool:
        current = lows[index]
        left_values = lows[index - self.left_window : index]
        right_values = lows[index + 1 : index + 1 + self.right_window]
        return current < min(left_values) and current < min(right_values)

    def _build_swing_high(self, window: CandleWindow, index: int) -> SwingPoint:
        price = window.highs[index]
        left_max = max(window.highs[index - self.left_window : index])
        right_max = max(window.highs[index + 1 : index + 1 + self.right_window])
        return SwingPoint(
            point_type=SwingPointType.HIGH,
            index=index,
            open_time=window.candles[index].open_time,
            price=price,
            left_strength=price - left_max,
            right_strength=price - right_max,
        )

    def _build_swing_low(self, window: CandleWindow, index: int) -> SwingPoint:
        price = window.lows[index]
        left_min = min(window.lows[index - self.left_window : index])
        right_min = min(window.lows[index + 1 : index + 1 + self.right_window])
        return SwingPoint(
            point_type=SwingPointType.LOW,
            index=index,
            open_time=window.candles[index].open_time,
            price=price,
            left_strength=left_min - price,
            right_strength=right_min - price,
        )
