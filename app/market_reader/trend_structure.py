from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence


class TrendStructureDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TrendSwingPoint:
    index: int
    open_time: datetime
    price: float

    @classmethod
    def from_point(cls, point: Any) -> "TrendSwingPoint":
        index = _to_int(_read_field(point, "index"), "index")
        open_time = _read_field(point, "open_time")
        if not isinstance(open_time, datetime):
            raise ValueError("swing point open_time must be a datetime")

        price = _to_finite_float(_read_field(point, "price"), "price")
        if price <= 0.0:
            raise ValueError("swing point price must be positive")

        if index < 0:
            raise ValueError("swing point index must be non-negative")

        return cls(index=index, open_time=open_time, price=price)


@dataclass(frozen=True)
class TrendStructureResult:
    direction: TrendStructureDirection
    strength_score: float
    higher_high_count: int = 0
    lower_high_count: int = 0
    equal_high_count: int = 0
    higher_low_count: int = 0
    lower_low_count: int = 0
    equal_low_count: int = 0
    swing_high_count: int = 0
    swing_low_count: int = 0
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength_score <= 1.0:
            raise ValueError("strength_score must be between 0.0 and 1.0")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    @property
    def has_enough_structure(self) -> bool:
        return self.swing_high_count >= 2 and self.swing_low_count >= 2

    def to_dict(self) -> dict[str, object]:
        return {
            "direction": self.direction.value,
            "strength_score": self.strength_score,
            "higher_high_count": self.higher_high_count,
            "lower_high_count": self.lower_high_count,
            "equal_high_count": self.equal_high_count,
            "higher_low_count": self.higher_low_count,
            "lower_low_count": self.lower_low_count,
            "equal_low_count": self.equal_low_count,
            "swing_high_count": self.swing_high_count,
            "swing_low_count": self.swing_low_count,
            "has_enough_structure": self.has_enough_structure,
            "reason_codes": list(self.reason_codes),
        }


class TrendStructureAnalyzer:
    def analyze(
        self,
        *,
        swing_highs: Sequence[Any],
        swing_lows: Sequence[Any],
        tolerance_pct: float = 0.0,
    ) -> TrendStructureResult:
        if tolerance_pct < 0.0:
            raise ValueError("tolerance_pct must be non-negative")

        highs = tuple(TrendSwingPoint.from_point(point) for point in swing_highs)
        lows = tuple(TrendSwingPoint.from_point(point) for point in swing_lows)

        _validate_strictly_increasing_indices(highs, "swing_highs")
        _validate_strictly_increasing_indices(lows, "swing_lows")

        high_counts = self._count_high_structure(highs=highs, tolerance_pct=tolerance_pct)
        low_counts = self._count_low_structure(lows=lows, tolerance_pct=tolerance_pct)

        if len(highs) < 2 or len(lows) < 2:
            return TrendStructureResult(
                direction=TrendStructureDirection.UNKNOWN,
                strength_score=0.0,
                higher_high_count=high_counts["higher"],
                lower_high_count=high_counts["lower"],
                equal_high_count=high_counts["equal"],
                higher_low_count=low_counts["higher"],
                lower_low_count=low_counts["lower"],
                equal_low_count=low_counts["equal"],
                swing_high_count=len(highs),
                swing_low_count=len(lows),
                reason_codes=("NOT_ENOUGH_SWING_POINTS",),
            )

        up_score = high_counts["higher"] + low_counts["higher"]
        down_score = high_counts["lower"] + low_counts["lower"]
        total_comparisons = max(
            1,
            high_counts["higher"]
            + high_counts["lower"]
            + high_counts["equal"]
            + low_counts["higher"]
            + low_counts["lower"]
            + low_counts["equal"],
        )

        if high_counts["higher"] > high_counts["lower"] and low_counts["higher"] > low_counts["lower"]:
            direction = TrendStructureDirection.UP
            strength_score = up_score / total_comparisons
            reason_codes = self._up_reason_codes(high_counts=high_counts, low_counts=low_counts)
        elif high_counts["lower"] > high_counts["higher"] and low_counts["lower"] > low_counts["higher"]:
            direction = TrendStructureDirection.DOWN
            strength_score = down_score / total_comparisons
            reason_codes = self._down_reason_codes(high_counts=high_counts, low_counts=low_counts)
        else:
            direction = TrendStructureDirection.MIXED
            strength_score = max(up_score, down_score) / total_comparisons
            reason_codes = ("MIXED_SWING_STRUCTURE",)

        return TrendStructureResult(
            direction=direction,
            strength_score=_clamp(strength_score),
            higher_high_count=high_counts["higher"],
            lower_high_count=high_counts["lower"],
            equal_high_count=high_counts["equal"],
            higher_low_count=low_counts["higher"],
            lower_low_count=low_counts["lower"],
            equal_low_count=low_counts["equal"],
            swing_high_count=len(highs),
            swing_low_count=len(lows),
            reason_codes=reason_codes,
        )

    def analyze_detection_result(
        self,
        detection_result: Any,
        *,
        tolerance_pct: float = 0.0,
    ) -> TrendStructureResult:
        return self.analyze(
            swing_highs=_read_field(detection_result, "swing_highs"),
            swing_lows=_read_field(detection_result, "swing_lows"),
            tolerance_pct=tolerance_pct,
        )

    @staticmethod
    def _count_high_structure(
        *,
        highs: Sequence[TrendSwingPoint],
        tolerance_pct: float,
    ) -> dict[str, int]:
        return _count_price_progression(points=highs, tolerance_pct=tolerance_pct)

    @staticmethod
    def _count_low_structure(
        *,
        lows: Sequence[TrendSwingPoint],
        tolerance_pct: float,
    ) -> dict[str, int]:
        return _count_price_progression(points=lows, tolerance_pct=tolerance_pct)

    @staticmethod
    def _up_reason_codes(
        *,
        high_counts: Mapping[str, int],
        low_counts: Mapping[str, int],
    ) -> tuple[str, ...]:
        reasons: list[str] = ["UP_TREND_STRUCTURE"]
        if high_counts["higher"] > 0:
            reasons.append("HIGHER_HIGHS")
        if low_counts["higher"] > 0:
            reasons.append("HIGHER_LOWS")
        return tuple(reasons)

    @staticmethod
    def _down_reason_codes(
        *,
        high_counts: Mapping[str, int],
        low_counts: Mapping[str, int],
    ) -> tuple[str, ...]:
        reasons: list[str] = ["DOWN_TREND_STRUCTURE"]
        if high_counts["lower"] > 0:
            reasons.append("LOWER_HIGHS")
        if low_counts["lower"] > 0:
            reasons.append("LOWER_LOWS")
        return tuple(reasons)


def _count_price_progression(
    *,
    points: Sequence[TrendSwingPoint],
    tolerance_pct: float,
) -> dict[str, int]:
    counts = {"higher": 0, "lower": 0, "equal": 0}

    for previous, current in zip(points, points[1:]):
        tolerance = abs(previous.price) * tolerance_pct
        if current.price > previous.price + tolerance:
            counts["higher"] += 1
        elif current.price < previous.price - tolerance:
            counts["lower"] += 1
        else:
            counts["equal"] += 1

    return counts


def _validate_strictly_increasing_indices(points: Sequence[TrendSwingPoint], name: str) -> None:
    for previous, current in zip(points, points[1:]):
        if current.index <= previous.index:
            raise ValueError(f"{name} must be ordered by strictly increasing index")


def _read_field(source: Any, field_name: str) -> Any:
    if isinstance(source, Mapping):
        if field_name not in source:
            raise ValueError(f"missing field: {field_name}")
        return source[field_name]

    if not hasattr(source, field_name):
        raise ValueError(f"missing field: {field_name}")

    return getattr(source, field_name)


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _to_finite_float(value: Any, field_name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must be finite")

    return numeric_value


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
