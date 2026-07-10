from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

from app.market_reader.candle_window import CandleBar, CandleWindow


class BreakoutDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class BreakoutRetestClassification(str, Enum):
    BULLISH_BREAKOUT = "BULLISH_BREAKOUT"
    BEARISH_BREAKOUT = "BEARISH_BREAKOUT"
    BULLISH_BREAKOUT_RETEST = "BULLISH_BREAKOUT_RETEST"
    BEARISH_BREAKOUT_RETEST = "BEARISH_BREAKOUT_RETEST"
    FALSE_BULLISH_BREAKOUT = "FALSE_BULLISH_BREAKOUT"
    FALSE_BEARISH_BREAKOUT = "FALSE_BEARISH_BREAKOUT"
    INSIDE_RANGE = "INSIDE_RANGE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BreakoutRetestResult:
    classification: BreakoutRetestClassification
    breakout_direction: BreakoutDirection
    breakout_score: float
    support_level: float | None = None
    resistance_level: float | None = None
    breakout_level: float | None = None
    breakout_index: int | None = None
    breakout_open_time: datetime | None = None
    latest_close: float | None = None
    breakout_distance_pct: float = 0.0
    retest_detected: bool = False
    false_breakout_detected: bool = False
    follow_through_count: int = 0
    candle_count: int = 0
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.breakout_score <= 1.0:
            raise ValueError("breakout_score must be between 0.0 and 1.0")

        if self.breakout_distance_pct < 0.0:
            raise ValueError("breakout_distance_pct must be non-negative")

        if self.follow_through_count < 0:
            raise ValueError("follow_through_count must be non-negative")

        if self.candle_count < 0:
            raise ValueError("candle_count must be non-negative")

        if self.breakout_index is not None and self.breakout_index < 0:
            raise ValueError("breakout_index must be non-negative")

        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))

    @property
    def has_breakout(self) -> bool:
        return self.breakout_direction in {
            BreakoutDirection.BULLISH,
            BreakoutDirection.BEARISH,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "breakout_direction": self.breakout_direction.value,
            "breakout_score": self.breakout_score,
            "support_level": self.support_level,
            "resistance_level": self.resistance_level,
            "breakout_level": self.breakout_level,
            "breakout_index": self.breakout_index,
            "breakout_open_time": self.breakout_open_time.isoformat() if self.breakout_open_time else None,
            "latest_close": self.latest_close,
            "breakout_distance_pct": self.breakout_distance_pct,
            "retest_detected": self.retest_detected,
            "false_breakout_detected": self.false_breakout_detected,
            "follow_through_count": self.follow_through_count,
            "candle_count": self.candle_count,
            "has_breakout": self.has_breakout,
            "reason_codes": list(self.reason_codes),
        }


class BreakoutRetestAnalyzer:
    def analyze(
        self,
        window: CandleWindow,
        *,
        range_result: Any | None = None,
        support_level: float | None = None,
        resistance_level: float | None = None,
        lookback: int = 20,
        breakout_tolerance_pct: float = 0.001,
        retest_tolerance_pct: float = 0.005,
        min_follow_through_count: int = 1,
    ) -> BreakoutRetestResult:
        self._validate_parameters(
            lookback=lookback,
            breakout_tolerance_pct=breakout_tolerance_pct,
            retest_tolerance_pct=retest_tolerance_pct,
            min_follow_through_count=min_follow_through_count,
        )

        candles = tuple(window.candles[-lookback:])
        support = _resolve_level(
            direct_level=support_level,
            source=range_result,
            field_name="support_level",
        )
        resistance = _resolve_level(
            direct_level=resistance_level,
            source=range_result,
            field_name="resistance_level",
        )

        if support is None or resistance is None:
            return BreakoutRetestResult(
                classification=BreakoutRetestClassification.UNKNOWN,
                breakout_direction=BreakoutDirection.UNKNOWN,
                breakout_score=0.0,
                support_level=support,
                resistance_level=resistance,
                latest_close=candles[-1].close if candles else None,
                candle_count=len(candles),
                reason_codes=("NO_RANGE_BOUNDARIES_FOR_BREAKOUT_ANALYSIS",),
            )

        _validate_levels(support=support, resistance=resistance)

        breakout_sequence = _find_latest_breakout_sequence_start(
            candles=candles,
            support=support,
            resistance=resistance,
            breakout_tolerance_pct=breakout_tolerance_pct,
        )

        if breakout_sequence is None:
            return self._classify_no_close_breakout(
                candles=candles,
                support=support,
                resistance=resistance,
                breakout_tolerance_pct=breakout_tolerance_pct,
            )

        breakout_direction, breakout_index = breakout_sequence

        if breakout_direction == BreakoutDirection.BULLISH:
            return self._classify_bullish_breakout(
                candles=candles,
                breakout_index=breakout_index,
                support=support,
                resistance=resistance,
                breakout_tolerance_pct=breakout_tolerance_pct,
                retest_tolerance_pct=retest_tolerance_pct,
                min_follow_through_count=min_follow_through_count,
            )

        return self._classify_bearish_breakout(
            candles=candles,
            breakout_index=breakout_index,
            support=support,
            resistance=resistance,
            breakout_tolerance_pct=breakout_tolerance_pct,
            retest_tolerance_pct=retest_tolerance_pct,
            min_follow_through_count=min_follow_through_count,
        )

    @staticmethod
    def _validate_parameters(
        *,
        lookback: int,
        breakout_tolerance_pct: float,
        retest_tolerance_pct: float,
        min_follow_through_count: int,
    ) -> None:
        if lookback <= 0:
            raise ValueError("lookback must be positive")
        if breakout_tolerance_pct < 0.0:
            raise ValueError("breakout_tolerance_pct must be non-negative")
        if retest_tolerance_pct < 0.0:
            raise ValueError("retest_tolerance_pct must be non-negative")
        if min_follow_through_count < 0:
            raise ValueError("min_follow_through_count must be non-negative")

    @staticmethod
    def _classify_no_close_breakout(
        *,
        candles: Sequence[CandleBar],
        support: float,
        resistance: float,
        breakout_tolerance_pct: float,
    ) -> BreakoutRetestResult:
        latest = candles[-1]
        resistance_tolerance = _level_tolerance(resistance, breakout_tolerance_pct)
        support_tolerance = _level_tolerance(support, breakout_tolerance_pct)

        if latest.high > resistance + resistance_tolerance and latest.close <= resistance + resistance_tolerance:
            return BreakoutRetestResult(
                classification=BreakoutRetestClassification.FALSE_BULLISH_BREAKOUT,
                breakout_direction=BreakoutDirection.BULLISH,
                breakout_score=0.25,
                support_level=support,
                resistance_level=resistance,
                breakout_level=resistance,
                breakout_index=len(candles) - 1,
                breakout_open_time=latest.open_time,
                latest_close=latest.close,
                breakout_distance_pct=_distance_pct(latest.high, resistance),
                false_breakout_detected=True,
                candle_count=len(candles),
                reason_codes=(
                    "BULLISH_WICK_BREAKOUT",
                    "CLOSE_RETURNED_INSIDE_RANGE",
                    "FALSE_BULLISH_BREAKOUT",
                ),
            )

        if latest.low < support - support_tolerance and latest.close >= support - support_tolerance:
            return BreakoutRetestResult(
                classification=BreakoutRetestClassification.FALSE_BEARISH_BREAKOUT,
                breakout_direction=BreakoutDirection.BEARISH,
                breakout_score=0.25,
                support_level=support,
                resistance_level=resistance,
                breakout_level=support,
                breakout_index=len(candles) - 1,
                breakout_open_time=latest.open_time,
                latest_close=latest.close,
                breakout_distance_pct=_distance_pct(support, latest.low),
                false_breakout_detected=True,
                candle_count=len(candles),
                reason_codes=(
                    "BEARISH_WICK_BREAKOUT",
                    "CLOSE_RETURNED_INSIDE_RANGE",
                    "FALSE_BEARISH_BREAKOUT",
                ),
            )

        return BreakoutRetestResult(
            classification=BreakoutRetestClassification.INSIDE_RANGE,
            breakout_direction=BreakoutDirection.NONE,
            breakout_score=0.0,
            support_level=support,
            resistance_level=resistance,
            latest_close=latest.close,
            candle_count=len(candles),
            reason_codes=("NO_CLOSE_BREAKOUT", "PRICE_INSIDE_RANGE"),
        )

    @staticmethod
    def _classify_bullish_breakout(
        *,
        candles: Sequence[CandleBar],
        breakout_index: int,
        support: float,
        resistance: float,
        breakout_tolerance_pct: float,
        retest_tolerance_pct: float,
        min_follow_through_count: int,
    ) -> BreakoutRetestResult:
        latest = candles[-1]
        breakout_candle = candles[breakout_index]
        breakout_tolerance = _level_tolerance(resistance, breakout_tolerance_pct)

        if latest.close < resistance - breakout_tolerance:
            return BreakoutRetestResult(
                classification=BreakoutRetestClassification.FALSE_BULLISH_BREAKOUT,
                breakout_direction=BreakoutDirection.BULLISH,
                breakout_score=0.30,
                support_level=support,
                resistance_level=resistance,
                breakout_level=resistance,
                breakout_index=breakout_index,
                breakout_open_time=breakout_candle.open_time,
                latest_close=latest.close,
                breakout_distance_pct=0.0,
                false_breakout_detected=True,
                candle_count=len(candles),
                reason_codes=(
                    "BULLISH_CLOSE_BREAKOUT",
                    "CLOSE_RETURNED_INSIDE_RANGE",
                    "FALSE_BULLISH_BREAKOUT",
                ),
            )

        follow_through_count = sum(
            1 for candle in candles[breakout_index:] if candle.close > resistance + breakout_tolerance
        )
        retest_detected = _has_bullish_retest(
            candles=candles[breakout_index + 1 :],
            resistance=resistance,
            breakout_tolerance_pct=breakout_tolerance_pct,
            retest_tolerance_pct=retest_tolerance_pct,
        )
        breakout_distance_pct = _distance_pct(latest.close, resistance)

        reason_codes = ["BULLISH_CLOSE_BREAKOUT"]
        if retest_detected:
            reason_codes.append("BULLISH_RETEST_CONFIRMED")
        if follow_through_count >= min_follow_through_count:
            reason_codes.append("BULLISH_FOLLOW_THROUGH")
        else:
            reason_codes.append("WEAK_BULLISH_FOLLOW_THROUGH")

        classification = (
            BreakoutRetestClassification.BULLISH_BREAKOUT_RETEST
            if retest_detected
            else BreakoutRetestClassification.BULLISH_BREAKOUT
        )

        return BreakoutRetestResult(
            classification=classification,
            breakout_direction=BreakoutDirection.BULLISH,
            breakout_score=_breakout_score(
                retest_detected=retest_detected,
                follow_through_count=follow_through_count,
                min_follow_through_count=min_follow_through_count,
                breakout_distance_pct=breakout_distance_pct,
            ),
            support_level=support,
            resistance_level=resistance,
            breakout_level=resistance,
            breakout_index=breakout_index,
            breakout_open_time=breakout_candle.open_time,
            latest_close=latest.close,
            breakout_distance_pct=breakout_distance_pct,
            retest_detected=retest_detected,
            follow_through_count=follow_through_count,
            candle_count=len(candles),
            reason_codes=tuple(reason_codes),
        )

    @staticmethod
    def _classify_bearish_breakout(
        *,
        candles: Sequence[CandleBar],
        breakout_index: int,
        support: float,
        resistance: float,
        breakout_tolerance_pct: float,
        retest_tolerance_pct: float,
        min_follow_through_count: int,
    ) -> BreakoutRetestResult:
        latest = candles[-1]
        breakout_candle = candles[breakout_index]
        breakout_tolerance = _level_tolerance(support, breakout_tolerance_pct)

        if latest.close > support + breakout_tolerance:
            return BreakoutRetestResult(
                classification=BreakoutRetestClassification.FALSE_BEARISH_BREAKOUT,
                breakout_direction=BreakoutDirection.BEARISH,
                breakout_score=0.30,
                support_level=support,
                resistance_level=resistance,
                breakout_level=support,
                breakout_index=breakout_index,
                breakout_open_time=breakout_candle.open_time,
                latest_close=latest.close,
                breakout_distance_pct=0.0,
                false_breakout_detected=True,
                candle_count=len(candles),
                reason_codes=(
                    "BEARISH_CLOSE_BREAKOUT",
                    "CLOSE_RETURNED_INSIDE_RANGE",
                    "FALSE_BEARISH_BREAKOUT",
                ),
            )

        follow_through_count = sum(
            1 for candle in candles[breakout_index:] if candle.close < support - breakout_tolerance
        )
        retest_detected = _has_bearish_retest(
            candles=candles[breakout_index + 1 :],
            support=support,
            breakout_tolerance_pct=breakout_tolerance_pct,
            retest_tolerance_pct=retest_tolerance_pct,
        )
        breakout_distance_pct = _distance_pct(support, latest.close)

        reason_codes = ["BEARISH_CLOSE_BREAKOUT"]
        if retest_detected:
            reason_codes.append("BEARISH_RETEST_CONFIRMED")
        if follow_through_count >= min_follow_through_count:
            reason_codes.append("BEARISH_FOLLOW_THROUGH")
        else:
            reason_codes.append("WEAK_BEARISH_FOLLOW_THROUGH")

        classification = (
            BreakoutRetestClassification.BEARISH_BREAKOUT_RETEST
            if retest_detected
            else BreakoutRetestClassification.BEARISH_BREAKOUT
        )

        return BreakoutRetestResult(
            classification=classification,
            breakout_direction=BreakoutDirection.BEARISH,
            breakout_score=_breakout_score(
                retest_detected=retest_detected,
                follow_through_count=follow_through_count,
                min_follow_through_count=min_follow_through_count,
                breakout_distance_pct=breakout_distance_pct,
            ),
            support_level=support,
            resistance_level=resistance,
            breakout_level=support,
            breakout_index=breakout_index,
            breakout_open_time=breakout_candle.open_time,
            latest_close=latest.close,
            breakout_distance_pct=breakout_distance_pct,
            retest_detected=retest_detected,
            follow_through_count=follow_through_count,
            candle_count=len(candles),
            reason_codes=tuple(reason_codes),
        )


def _find_latest_breakout_sequence_start(
    *,
    candles: Sequence[CandleBar],
    support: float,
    resistance: float,
    breakout_tolerance_pct: float,
) -> tuple[BreakoutDirection, int] | None:
    support_tolerance = _level_tolerance(support, breakout_tolerance_pct)
    resistance_tolerance = _level_tolerance(resistance, breakout_tolerance_pct)

    latest_direction: BreakoutDirection | None = None
    latest_start_index: int | None = None
    previous_state = BreakoutDirection.NONE

    for index, candle in enumerate(candles):
        if candle.close > resistance + resistance_tolerance:
            current_state = BreakoutDirection.BULLISH
        elif candle.close < support - support_tolerance:
            current_state = BreakoutDirection.BEARISH
        else:
            current_state = BreakoutDirection.NONE

        if current_state in {BreakoutDirection.BULLISH, BreakoutDirection.BEARISH}:
            if current_state != previous_state:
                latest_direction = current_state
                latest_start_index = index

        previous_state = current_state

    if latest_direction is None or latest_start_index is None:
        return None

    return latest_direction, latest_start_index


def _find_bullish_close_breakouts(
    *,
    candles: Sequence[CandleBar],
    resistance: float,
    breakout_tolerance_pct: float,
) -> list[int]:
    tolerance = _level_tolerance(resistance, breakout_tolerance_pct)
    return [
        index
        for index, candle in enumerate(candles)
        if candle.close > resistance + tolerance
    ]


def _find_bearish_close_breakouts(
    *,
    candles: Sequence[CandleBar],
    support: float,
    breakout_tolerance_pct: float,
) -> list[int]:
    tolerance = _level_tolerance(support, breakout_tolerance_pct)
    return [
        index
        for index, candle in enumerate(candles)
        if candle.close < support - tolerance
    ]


def _has_bullish_retest(
    *,
    candles: Sequence[CandleBar],
    resistance: float,
    breakout_tolerance_pct: float,
    retest_tolerance_pct: float,
) -> bool:
    breakout_tolerance = _level_tolerance(resistance, breakout_tolerance_pct)
    retest_tolerance = _level_tolerance(resistance, retest_tolerance_pct)

    return any(
        candle.low <= resistance + retest_tolerance
        and candle.close >= resistance - breakout_tolerance
        for candle in candles
    )


def _has_bearish_retest(
    *,
    candles: Sequence[CandleBar],
    support: float,
    breakout_tolerance_pct: float,
    retest_tolerance_pct: float,
) -> bool:
    breakout_tolerance = _level_tolerance(support, breakout_tolerance_pct)
    retest_tolerance = _level_tolerance(support, retest_tolerance_pct)

    return any(
        candle.high >= support - retest_tolerance
        and candle.close <= support + breakout_tolerance
        for candle in candles
    )


def _resolve_level(
    *,
    direct_level: float | None,
    source: Any | None,
    field_name: str,
) -> float | None:
    if direct_level is not None:
        return _to_positive_float(direct_level, field_name)

    if source is None:
        return None

    try:
        value = _read_field(source, field_name)
    except ValueError:
        return None

    if value is None:
        return None

    return _to_positive_float(value, field_name)


def _read_field(source: Any, field_name: str) -> Any:
    if isinstance(source, Mapping):
        if field_name not in source:
            raise ValueError(f"missing field: {field_name}")
        return source[field_name]

    if not hasattr(source, field_name):
        raise ValueError(f"missing field: {field_name}")

    return getattr(source, field_name)


def _to_positive_float(value: Any, field_name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must be finite")

    if numeric_value <= 0.0:
        raise ValueError(f"{field_name} must be positive")

    return numeric_value


def _validate_levels(*, support: float, resistance: float) -> None:
    if support >= resistance:
        raise ValueError("support_level must be lower than resistance_level")


def _level_tolerance(level: float, tolerance_pct: float) -> float:
    return abs(level) * tolerance_pct


def _distance_pct(price: float, level: float) -> float:
    if level <= 0.0:
        return 0.0
    return max(0.0, abs(price - level) / level)


def _breakout_score(
    *,
    retest_detected: bool,
    follow_through_count: int,
    min_follow_through_count: int,
    breakout_distance_pct: float,
) -> float:
    score = 0.45

    if retest_detected:
        score += 0.20

    if min_follow_through_count == 0 or follow_through_count >= min_follow_through_count:
        score += 0.20

    score += min(0.15, breakout_distance_pct * 5.0)

    return _clamp(score)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
