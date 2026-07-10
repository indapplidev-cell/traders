from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from app.market_reader.candle_window import CandleBar, CandleWindow


class RangeStructureClassification(str, Enum):
    RANGE = "RANGE"
    NOT_RANGE = "NOT_RANGE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RangeStructureResult:
    classification: RangeStructureClassification
    range_score: float
    support_level: float | None = None
    resistance_level: float | None = None
    range_width: float | None = None
    range_width_pct: float | None = None
    range_position: float | None = None
    support_touch_count: int = 0
    resistance_touch_count: int = 0
    inside_close_ratio: float = 0.0
    close_drift_ratio: float | None = None
    candle_count: int = 0
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _validate_unit_interval(self.range_score, "range_score")
        _validate_unit_interval(self.inside_close_ratio, "inside_close_ratio")

        if self.range_width is not None and self.range_width < 0.0:
            raise ValueError("range_width must be non-negative")
        if self.range_width_pct is not None:
            _validate_unit_interval(self.range_width_pct, "range_width_pct", allow_above_one=True)
        if self.range_position is not None:
            _validate_unit_interval(self.range_position, "range_position")
        if self.close_drift_ratio is not None:
            _validate_unit_interval(self.close_drift_ratio, "close_drift_ratio", allow_above_one=True)
        if self.support_touch_count < 0:
            raise ValueError("support_touch_count must be non-negative")
        if self.resistance_touch_count < 0:
            raise ValueError("resistance_touch_count must be non-negative")
        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")

        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    @property
    def has_range_boundaries(self) -> bool:
        return self.support_level is not None and self.resistance_level is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "range_score": self.range_score,
            "support_level": self.support_level,
            "resistance_level": self.resistance_level,
            "range_width": self.range_width,
            "range_width_pct": self.range_width_pct,
            "range_position": self.range_position,
            "support_touch_count": self.support_touch_count,
            "resistance_touch_count": self.resistance_touch_count,
            "inside_close_ratio": self.inside_close_ratio,
            "close_drift_ratio": self.close_drift_ratio,
            "candle_count": self.candle_count,
            "has_range_boundaries": self.has_range_boundaries,
            "reason_codes": list(self.reason_codes),
        }


class RangeStructureAnalyzer:
    def analyze(
        self,
        window: CandleWindow,
        *,
        lookback: int = 20,
        min_size: int = 5,
        boundary_tolerance_pct: float = 0.01,
        max_range_width_pct: float = 0.08,
        max_close_drift_ratio: float = 0.60,
        min_boundary_touch_count: int = 2,
    ) -> RangeStructureResult:
        _validate_positive_int(lookback, "lookback")
        _validate_positive_int(min_size, "min_size")
        _validate_non_negative(boundary_tolerance_pct, "boundary_tolerance_pct")
        _validate_positive(max_range_width_pct, "max_range_width_pct")
        _validate_positive(max_close_drift_ratio, "max_close_drift_ratio")
        _validate_positive_int(min_boundary_touch_count, "min_boundary_touch_count")

        if window.size < min_size:
            return RangeStructureResult(
                classification=RangeStructureClassification.UNKNOWN,
                range_score=0.0,
                candle_count=window.size,
                reason_codes=("NOT_ENOUGH_CANDLES_FOR_RANGE_STRUCTURE",),
            )

        candles = window.candles[-lookback:]
        support_level = min(candle.low for candle in candles)
        resistance_level = max(candle.high for candle in candles)
        range_width = resistance_level - support_level

        if support_level <= 0.0 or resistance_level <= 0.0 or range_width <= 0.0:
            return RangeStructureResult(
                classification=RangeStructureClassification.UNKNOWN,
                range_score=0.0,
                support_level=support_level,
                resistance_level=resistance_level,
                range_width=max(0.0, range_width),
                candle_count=len(candles),
                reason_codes=("INVALID_RANGE_BOUNDARIES",),
            )

        midpoint = (support_level + resistance_level) / 2.0
        range_width_pct = range_width / midpoint
        latest_close = candles[-1].close
        range_position = _clamp((latest_close - support_level) / range_width)
        support_touch_count = _count_support_touches(
            candles=candles,
            support_level=support_level,
            tolerance_pct=boundary_tolerance_pct,
        )
        resistance_touch_count = _count_resistance_touches(
            candles=candles,
            resistance_level=resistance_level,
            tolerance_pct=boundary_tolerance_pct,
        )
        inside_close_ratio = _inside_close_ratio(
            candles=candles,
            support_level=support_level,
            resistance_level=resistance_level,
        )
        close_drift_ratio = abs(candles[-1].close - candles[0].close) / range_width

        width_ok = range_width_pct <= max_range_width_pct
        touches_ok = (
            support_touch_count >= min_boundary_touch_count
            and resistance_touch_count >= min_boundary_touch_count
        )
        drift_ok = close_drift_ratio <= max_close_drift_ratio

        range_score = _range_score(
            range_width_pct=range_width_pct,
            max_range_width_pct=max_range_width_pct,
            support_touch_count=support_touch_count,
            resistance_touch_count=resistance_touch_count,
            min_boundary_touch_count=min_boundary_touch_count,
            close_drift_ratio=close_drift_ratio,
            max_close_drift_ratio=max_close_drift_ratio,
            inside_close_ratio=inside_close_ratio,
        )

        if width_ok and touches_ok and drift_ok:
            classification = RangeStructureClassification.RANGE
            reason_codes = _range_reason_codes(
                support_touch_count=support_touch_count,
                resistance_touch_count=resistance_touch_count,
            )
        else:
            classification = RangeStructureClassification.NOT_RANGE
            reason_codes = _not_range_reason_codes(
                width_ok=width_ok,
                touches_ok=touches_ok,
                drift_ok=drift_ok,
            )

        return RangeStructureResult(
            classification=classification,
            range_score=range_score,
            support_level=support_level,
            resistance_level=resistance_level,
            range_width=range_width,
            range_width_pct=range_width_pct,
            range_position=range_position,
            support_touch_count=support_touch_count,
            resistance_touch_count=resistance_touch_count,
            inside_close_ratio=inside_close_ratio,
            close_drift_ratio=close_drift_ratio,
            candle_count=len(candles),
            reason_codes=reason_codes,
        )


def _count_support_touches(
    *,
    candles: Sequence[CandleBar],
    support_level: float,
    tolerance_pct: float,
) -> int:
    threshold = support_level * (1.0 + tolerance_pct)
    return sum(1 for candle in candles if candle.low <= threshold)


def _count_resistance_touches(
    *,
    candles: Sequence[CandleBar],
    resistance_level: float,
    tolerance_pct: float,
) -> int:
    threshold = resistance_level * (1.0 - tolerance_pct)
    return sum(1 for candle in candles if candle.high >= threshold)


def _inside_close_ratio(
    *,
    candles: Sequence[CandleBar],
    support_level: float,
    resistance_level: float,
) -> float:
    if not candles:
        return 0.0
    inside_count = sum(1 for candle in candles if support_level <= candle.close <= resistance_level)
    return inside_count / len(candles)


def _range_score(
    *,
    range_width_pct: float,
    max_range_width_pct: float,
    support_touch_count: int,
    resistance_touch_count: int,
    min_boundary_touch_count: int,
    close_drift_ratio: float,
    max_close_drift_ratio: float,
    inside_close_ratio: float,
) -> float:
    width_component = _clamp(1.0 - (range_width_pct / max_range_width_pct))
    support_component = _clamp(support_touch_count / min_boundary_touch_count)
    resistance_component = _clamp(resistance_touch_count / min_boundary_touch_count)
    drift_component = _clamp(1.0 - (close_drift_ratio / max_close_drift_ratio))
    return _clamp(
        (
            width_component
            + support_component
            + resistance_component
            + drift_component
            + inside_close_ratio
        )
        / 5.0
    )


def _range_reason_codes(*, support_touch_count: int, resistance_touch_count: int) -> tuple[str, ...]:
    reasons = [
        "RANGE_STRUCTURE_DETECTED",
        "RANGE_WIDTH_ACCEPTABLE",
        "LOW_CLOSE_DRIFT_INSIDE_RANGE",
    ]
    if support_touch_count > 0:
        reasons.append("SUPPORT_TOUCHES_DETECTED")
    if resistance_touch_count > 0:
        reasons.append("RESISTANCE_TOUCHES_DETECTED")
    return tuple(reasons)


def _not_range_reason_codes(*, width_ok: bool, touches_ok: bool, drift_ok: bool) -> tuple[str, ...]:
    reasons = ["NOT_RANGE_STRUCTURE"]
    if not width_ok:
        reasons.append("RANGE_TOO_WIDE")
    if not touches_ok:
        reasons.append("WEAK_BOUNDARY_TOUCHES")
    if not drift_ok:
        reasons.append("DIRECTIONAL_CLOSE_DRIFT")
    return tuple(reasons)


def _validate_positive_int(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _validate_positive(value: float, field_name: str) -> None:
    if value <= 0.0:
        raise ValueError(f"{field_name} must be positive")


def _validate_non_negative(value: float, field_name: str) -> None:
    if value < 0.0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_unit_interval(value: float, field_name: str, *, allow_above_one: bool = False) -> None:
    if value < 0.0:
        raise ValueError(f"{field_name} must be non-negative")
    if not allow_above_one and value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
