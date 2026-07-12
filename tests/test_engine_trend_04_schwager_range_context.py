from pathlib import Path

import pytest

from app.market_reader.engine_trend.altunina_trend_context import SwingPoint, SwingPointType
from app.market_reader.engine_trend.schemas import BookSource, EngineTrendCandle
from app.market_reader.engine_trend.schwager_range_context import (
    BreakoutConfirmationMethod, BreakoutConfirmationStatus, BreakoutDirection,
    FalseBreakoutConfirmationStatus, PolarityFlipStatus,
    SchwagerRangeContext, SupportResistanceZone, TradingRange, ZoneType,
    analyze_breakout_context, analyze_polarity_flip_context,
    analyze_schwager_range_context, build_support_resistance_zones,
    detect_trading_range,
)


def candle(timestamp: str, open_: float, high: float, low: float, close: float) -> EngineTrendCandle:
    return EngineTrendCandle(timestamp, open_, high, low, close)


def zone(kind: ZoneType, lower: float, upper: float, touches: int = 2) -> SupportResistanceZone:
    mid = (lower + upper) / 2
    indexes = (0, 4) if kind is ZoneType.SUPPORT else (2, 6)
    return SupportResistanceZone(kind, lower, upper, mid, touches, indexes[:touches], upper - lower, (upper - lower) / mid, indexes[touches - 1])


def found_range() -> TradingRange:
    support = zone(ZoneType.SUPPORT, 99.8, 100.2)
    resistance = zone(ZoneType.RESISTANCE, 109.8, 110.0)
    return TradingRange(support, resistance, True, 99.8, 110.0, 104.9, 10.2, 10.2 / 104.9, 4, 0.8, 8, 1, 8, 3)


def range_candles() -> list[EngineTrendCandle]:
    values = [(105, 106, 104, 105), (105, 110, 104, 109), (109, 109.5, 100, 101),
              (101, 106, 99.9, 105), (105, 110.1, 104, 109), (109, 109.4, 100.1, 101),
              (101, 106, 99.8, 105), (105, 110, 104, 109), (109, 109.5, 100, 101)]
    return [candle(str(index), *item) for index, item in enumerate(values)]


def test_builds_support_and_resistance_bands() -> None:
    swings = (SwingPoint(1, "1", 100.0, SwingPointType.LOW), SwingPoint(3, "3", 100.2, SwingPointType.LOW),
              SwingPoint(2, "2", 110.0, SwingPointType.HIGH), SwingPoint(4, "4", 109.8, SwingPointType.HIGH))
    zones = build_support_resistance_zones(range_candles(), swings)
    assert [item.zone_type for item in zones] == [ZoneType.SUPPORT, ZoneType.RESISTANCE]
    assert (zones[0].lower_price, zones[0].upper_price, zones[0].touch_count) == (100.0, 100.2, 2)
    assert zones[0].mid_price == pytest.approx(100.1)
    assert zones[0].zone_width == pytest.approx(0.2)
    assert {"zone_type", "formed_at_index", "source_point_types", "current_zone_type"} <= set(zones[0].to_dict())


def test_missing_repeated_touches_produce_evidence() -> None:
    context = analyze_schwager_range_context([candle("0", 100, 101, 99, 100)])
    assert context.zones == ()
    assert "SCHWAGER_INSUFFICIENT_LEVEL_TOUCHES" in context.reason_codes


def test_detects_range_and_inside_ratio() -> None:
    result = detect_trading_range(range_candles(), [zone(ZoneType.SUPPORT, 99.8, 100.2), zone(ZoneType.RESISTANCE, 109.8, 110.0)])
    assert result.is_detected
    assert (result.lower_boundary, result.upper_boundary) == (99.8, 110.0)
    assert result.inside_close_ratio == 1.0
    assert "support_zone" in result.to_dict()


@pytest.mark.parametrize("zones", [[], [zone(ZoneType.SUPPORT, 100, 100.1)]])
def test_range_rejects_a_missing_side(zones: list[SupportResistanceZone]) -> None:
    assert not detect_trading_range(range_candles(), zones).is_detected


@pytest.mark.parametrize("support,resistance", [
    (zone(ZoneType.SUPPORT, 100, 101), zone(ZoneType.RESISTANCE, 100.5, 102)),
    (zone(ZoneType.SUPPORT, 100, 100.01), zone(ZoneType.RESISTANCE, 100.02, 100.03)),
    (zone(ZoneType.SUPPORT, 80, 81), zone(ZoneType.RESISTANCE, 120, 121)),
])
def test_range_rejects_overlap_or_invalid_width(support: SupportResistanceZone, resistance: SupportResistanceZone) -> None:
    assert not detect_trading_range(range_candles(), [support, resistance]).is_detected


@pytest.mark.parametrize("tail,direction,status,returned", [
    ([(109, 111, 108, 111), (111, 112, 110.5, 111.5), (111.5, 113, 111, 112)], BreakoutDirection.UPWARD, BreakoutConfirmationStatus.CONFIRMED, False),
    ([(101, 102, 98, 98), (98, 99, 97, 98.5), (98.5, 99, 96, 97)], BreakoutDirection.DOWNWARD, BreakoutConfirmationStatus.CONFIRMED, False),
    ([(109, 111, 108, 111), (111, 112, 105, 106)], BreakoutDirection.UPWARD, BreakoutConfirmationStatus.RETURNED_TO_RANGE, True),
    ([(101, 102, 98, 98), (98, 106, 97, 105)], BreakoutDirection.DOWNWARD, BreakoutConfirmationStatus.FALSE_BREAKOUT, True),
    ([(109, 110.3, 108, 110.2)], BreakoutDirection.UPWARD, BreakoutConfirmationStatus.ATTEMPT, False),
])
def test_breakout_states(tail: list[tuple[float, float, float, float]], direction: BreakoutDirection, status: BreakoutConfirmationStatus, returned: bool) -> None:
    candles = range_candles() + [candle(f"x{index}", *item) for index, item in enumerate(tail)]
    result = analyze_breakout_context(candles, found_range())
    assert (result.direction, result.status, result.returned_to_range) == (direction, status, returned)
    assert result.breakout_index is not None


@pytest.mark.parametrize("tail,expected", [
    ([(109, 112, 108, 111), (111, 112, 109.9, 110.4)], PolarityFlipStatus.RESISTANCE_TO_SUPPORT),
    ([(101, 102, 97, 98), (98, 100, 97, 99.5)], PolarityFlipStatus.SUPPORT_TO_RESISTANCE),
    ([(109, 112, 108, 111), (111, 112, 105, 106)], PolarityFlipStatus.FAILED),
])
def test_polarity_flip_states(tail: list[tuple[float, float, float, float]], expected: PolarityFlipStatus) -> None:
    candles = range_candles() + [candle(f"p{index}", *item) for index, item in enumerate(tail)]
    breakout = analyze_breakout_context(candles, found_range())
    result = analyze_polarity_flip_context(candles, found_range(), breakout)
    assert result.status is expected
    assert result.held is (expected is not PolarityFlipStatus.FAILED)


def test_breakout_analysis_starts_after_range_formation() -> None:
    candles = [candle("0", 109, 112, 108, 111)] + range_candles()
    result = analyze_breakout_context(candles, TradingRange(
        zone(ZoneType.SUPPORT, 99.8, 100.2), zone(ZoneType.RESISTANCE, 109.8, 110.0),
        True, 99.8, 110.0, 104.9, 10.2, 10.2 / 104.9, 4, 1.0, 9, 1, 9, 3,
    ))
    assert result.direction is BreakoutDirection.NONE
    assert result.analysis_start_index == 10


def test_zone_cluster_accepts_both_swing_point_types() -> None:
    swings = (
        SwingPoint(1, "1", 100.0, SwingPointType.LOW),
        SwingPoint(3, "3", 100.1, SwingPointType.HIGH),
    )
    zones = build_support_resistance_zones(range_candles(), swings)
    assert len(zones) == 1
    assert set(zones[0].source_point_types) == {SwingPointType.LOW, SwingPointType.HIGH}


def test_significant_previous_extreme_can_form_single_touch_zone() -> None:
    candles = range_candles()
    zones = build_support_resistance_zones(
        candles, (SwingPoint(6, "6", min(item.low for item in candles), SwingPointType.LOW),),
    )
    assert len(zones) == 1
    assert zones[0].is_significant_single_extreme


def test_range_requires_duration_and_boundary_alternation() -> None:
    support = SupportResistanceZone(ZoneType.SUPPORT, 99.8, 100.2, 100.0, 2, (0, 1), 0.4, 0.004, 1)
    resistance = SupportResistanceZone(ZoneType.RESISTANCE, 109.8, 110.0, 109.9, 2, (2, 3), 0.2, 0.002, 3)
    rejected = detect_trading_range(range_candles(), [support, resistance])
    assert not rejected.is_detected
    assert rejected.duration_candles == 4
    assert rejected.boundary_alternation_count == 1
    accepted = detect_trading_range(range_candles(), [zone(ZoneType.SUPPORT, 99.8, 100.2), zone(ZoneType.RESISTANCE, 109.8, 110.0)])
    assert accepted.is_detected
    assert accepted.boundary_alternation_count >= 2


def test_breakout_confirmation_supports_close_count_and_distance() -> None:
    by_closes = range_candles() + [
        candle("a", 109, 110.3, 108, 110.2),
        candle("b", 110.2, 110.35, 110.1, 110.25),
        candle("c", 110.25, 110.4, 110.2, 110.3),
    ]
    close_result = analyze_breakout_context(by_closes, found_range())
    assert close_result.confirmation_method is BreakoutConfirmationMethod.CLOSE_COUNT
    by_distance = range_candles() + [candle("a", 109, 112, 108, 111)]
    distance_result = analyze_breakout_context(by_distance, found_range())
    assert distance_result.confirmation_method is BreakoutConfirmationMethod.DISTANCE


def test_shallow_return_is_not_yet_false_breakout() -> None:
    candles = range_candles() + [candle("a", 109, 112, 108, 111), candle("b", 111, 112, 109, 109.8)]
    result = analyze_breakout_context(candles, found_range())
    assert result.status is BreakoutConfirmationStatus.RETURNED_TO_RANGE
    assert result.false_breakout_confirmation is FalseBreakoutConfirmationStatus.RETURNED_INSIDE
    assert "SCHWAGER_FALSE_BREAKOUT_UP" not in {item.code for item in result.evidence}


@pytest.mark.parametrize("return_close,expected", [
    (104.8, FalseBreakoutConfirmationStatus.INITIAL_PRICE_CONFIRMATION),
    (99.8, FalseBreakoutConfirmationStatus.STRONG_PRICE_CONFIRMATION),
])
def test_false_breakout_price_confirmation_depth(return_close: float, expected: FalseBreakoutConfirmationStatus) -> None:
    candles = range_candles() + [
        candle("a", 109, 112, 108, 111),
        candle("b", 111, 111.5, min(99.5, return_close), return_close),
    ]
    result = analyze_breakout_context(candles, found_range())
    assert result.status is BreakoutConfirmationStatus.FALSE_BREAKOUT
    assert result.false_breakout_confirmation is expected


def test_false_breakout_time_confirmation_and_invalidation() -> None:
    base = range_candles() + [candle("a", 109, 112, 108, 111), candle("b", 111, 111.5, 109, 109.8)]
    stable = base + [candle(str(index), 108, 109, 106, 108) for index in range(4)]
    time_result = analyze_breakout_context(stable, found_range())
    assert time_result.false_breakout_confirmation is FalseBreakoutConfirmationStatus.TIME_CONFIRMATION
    assert time_result.status is BreakoutConfirmationStatus.FALSE_BREAKOUT
    revisited = base + [candle("c", 109, 112.2, 108, 109)]
    invalidated = analyze_breakout_context(revisited, found_range())
    assert invalidated.false_breakout_confirmation is FalseBreakoutConfirmationStatus.INVALIDATED
    assert invalidated.false_breakout_invalidated


def test_polarity_requires_confirmed_departure_and_separate_test() -> None:
    attempt_candles = range_candles() + [candle("a", 109, 110.3, 108, 110.2)]
    attempt = analyze_breakout_context(attempt_candles, found_range())
    assert analyze_polarity_flip_context(attempt_candles, found_range(), attempt).status is PolarityFlipStatus.NONE
    confirmed_candles = range_candles() + [
        candle("a", 109, 112, 108, 111),
        candle("b", 111, 112, 110.5, 111.5),
        candle("c", 111.5, 112, 109.9, 110.4),
    ]
    confirmed = analyze_breakout_context(confirmed_candles, found_range())
    polarity = analyze_polarity_flip_context(confirmed_candles, found_range(), confirmed)
    assert polarity.status is PolarityFlipStatus.RESISTANCE_TO_SUPPORT
    assert polarity.departure_index is not None
    assert polarity.test_index > polarity.departure_index


def test_zone_tracks_original_and_current_role() -> None:
    candles = range_candles() + [candle("a", 109, 112, 108, 111)]
    swings = (
        SwingPoint(1, "1", 110.0, SwingPointType.HIGH),
        SwingPoint(4, "4", 109.9, SwingPointType.HIGH),
    )
    resistance = build_support_resistance_zones(candles, swings)[0]
    assert resistance.original_zone_type is ZoneType.RESISTANCE
    assert resistance.positional_zone_type is ZoneType.SUPPORT
    assert resistance.current_zone_type is ZoneType.RESISTANCE
    assert resistance.role_changed_at_index is None

    context = analyze_schwager_range_context(range_candles() + [
        candle("a", 109, 112, 108, 111),
        candle("b", 111, 112, 110.5, 111.5),
        candle("c", 111.5, 112, 110.0, 110.5),
    ])
    changed = next(item for item in context.zones if item.original_zone_type is ZoneType.RESISTANCE)
    assert changed.current_zone_type is ZoneType.SUPPORT
    assert changed.role_changed_at_index == len(range_candles()) + 2


def test_main_context_uses_schwager_and_has_no_final_state() -> None:
    context = analyze_schwager_range_context(range_candles())
    assert isinstance(context, SchwagerRangeContext)
    assert context.evidence and all(item.source is BookSource.SCHWAGER for item in context.evidence)
    assert context.reason_codes
    assert set(context.to_dict()) == {"candle_count", "zones", "trading_range", "breakout_context", "polarity_flip_context", "evidence", "reason_codes", "summary"}
    assert not hasattr(context, "market_regime")


def test_stage_source_safety() -> None:
    paths = [Path("app/market_reader/engine_trend/schwager_range_context.py"), Path("tests/test_engine_trend_04_schwager_range_context.py")]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    blocked = ("BU" + "Y", "SE" + "LL", "LO" + "NG", "SH" + "ORT", "EN" + "TRY", "EX" + "IT")
    legacy = ("market_regime_" + "composer", "trend_" + "structure", "range_" + "structure", "breakout_" + "retest", "technical_" + "context")
    assert all(word not in text for word in blocked)
    assert all(name not in text for name in legacy)
