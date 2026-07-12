from __future__ import annotations

import inspect

import pytest

from app.market_reader.engine_trend.altunina_trend_context import (
    ALTUNINA_CORRECTION_LIMIT,
    DERIVED_HEURISTIC,
    FIBONACCI_PULLBACK_LEVELS,
    AltuninaStructureDirection,
    AltuninaTrendContext,
    PriceLegDirection,
    SwingPoint,
    SwingPointType,
    TrendDurationClass,
    TrendHierarchyRole,
    analyze_altunina_trend_context,
    analyze_impulse_correction,
    build_trend_line,
    build_price_legs,
    classify_trend_duration,
    classify_structure_direction,
    detect_swing_points,
    normalize_swing_points,
)
from app.market_reader.engine_trend.schemas import BookSource, EngineTrendCandle, EngineTrendResult


def candle(index: int, high: float, low: float, close: float | None = None) -> EngineTrendCandle:
    value = (high + low) / 2 if close is None else close
    return EngineTrendCandle(str(index), value, high, low, value, 1.0)


def point(index: int, price: float, kind: SwingPointType) -> SwingPoint:
    return SwingPoint(index, str(index), price, kind)


def bullish_points() -> tuple[SwingPoint, ...]:
    return (
        point(1, 105, SwingPointType.HIGH), point(2, 101, SwingPointType.LOW),
        point(3, 110, SwingPointType.HIGH), point(4, 104, SwingPointType.LOW),
    )


def bearish_points() -> tuple[SwingPoint, ...]:
    return (
        point(1, 110, SwingPointType.HIGH), point(2, 104, SwingPointType.LOW),
        point(3, 106, SwingPointType.HIGH), point(4, 99, SwingPointType.LOW),
    )


def bullish_candles() -> tuple[EngineTrendCandle, ...]:
    return (
        candle(0, 102, 99, 100), candle(1, 105, 98, 104),
        candle(2, 103, 96, 102), candle(3, 110, 102, 109),
        candle(4, 107, 100, 105), candle(5, 112, 106, 111),
    )


def bearish_candles() -> tuple[EngineTrendCandle, ...]:
    return (
        candle(0, 111, 107, 110), candle(1, 112, 105, 106),
        candle(2, 107, 104, 105), candle(3, 108, 106, 107),
        candle(4, 106, 101, 105), candle(5, 103, 102, 102),
    )


def test_detects_swing_high_and_low_and_stable_order() -> None:
    result = detect_swing_points((candle(0, 10, 4), candle(1, 12, 2), candle(2, 9, 5)))
    assert [(item.point_type, item.price) for item in result] == [
        (SwingPointType.LOW, 2), (SwingPointType.HIGH, 12)
    ]


def test_swing_detection_requires_complete_neighborhood() -> None:
    assert detect_swing_points((candle(0, 10, 4), candle(1, 11, 3))) == ()
    with pytest.raises(ValueError):
        detect_swing_points(bullish_candles(), lookback=0)


def test_builds_upward_and_downward_legs() -> None:
    legs = build_price_legs(bullish_points())
    assert [item.direction for item in legs] == [
        PriceLegDirection.DOWN, PriceLegDirection.UP, PriceLegDirection.DOWN
    ]
    assert legs[0].absolute_change == 4
    assert legs[0].relative_change == pytest.approx(4 / 105)
    assert legs[0].candle_span == 1


def test_price_legs_sort_input_and_handle_small_input_and_zero_price() -> None:
    zero = point(0, 0, SwingPointType.LOW)
    higher = point(1, 5, SwingPointType.HIGH)
    assert build_price_legs((higher, zero))[0].relative_change == 0.0
    assert build_price_legs((zero,)) == ()


def test_normalizes_consecutive_same_type_swings_to_more_extreme_point() -> None:
    raw = (
        point(1, 100, SwingPointType.LOW),
        point(2, 99, SwingPointType.LOW),
        point(3, 110, SwingPointType.HIGH),
        point(4, 108, SwingPointType.HIGH),
        point(5, 102, SwingPointType.LOW),
    )
    normalized = normalize_swing_points(raw)
    assert [(item.index, item.point_type) for item in normalized] == [
        (2, SwingPointType.LOW),
        (3, SwingPointType.HIGH),
        (5, SwingPointType.LOW),
    ]


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (bullish_points(), AltuninaStructureDirection.BULLISH_STRUCTURE),
        (bearish_points(), AltuninaStructureDirection.BEARISH_STRUCTURE),
        ((point(1, 105, SwingPointType.HIGH), point(2, 100, SwingPointType.LOW), point(3, 104, SwingPointType.HIGH), point(4, 102, SwingPointType.LOW)), AltuninaStructureDirection.SIDEWAYS_STRUCTURE),
        ((point(1, 105, SwingPointType.HIGH), point(2, 100, SwingPointType.LOW)), AltuninaStructureDirection.UNCLEAR_STRUCTURE),
    ],
)
def test_classifies_structure(points: tuple[SwingPoint, ...], expected: AltuninaStructureDirection) -> None:
    assert classify_structure_direction(points) is expected


def test_tolerance_keeps_micro_change_sideways() -> None:
    points = (
        point(1, 100, SwingPointType.HIGH), point(2, 90, SwingPointType.LOW),
        point(3, 100.05, SwingPointType.HIGH), point(4, 90.05, SwingPointType.LOW),
    )
    assert classify_structure_direction(points) is AltuninaStructureDirection.SIDEWAYS_STRUCTURE


def test_structure_requires_every_high_and_low_to_progress() -> None:
    conflicting = (
        point(1, 105, SwingPointType.HIGH), point(2, 95, SwingPointType.LOW),
        point(3, 103, SwingPointType.HIGH), point(4, 97, SwingPointType.LOW),
        point(5, 110, SwingPointType.HIGH), point(6, 101, SwingPointType.LOW),
    )
    assert classify_structure_direction(conflicting) is AltuninaStructureDirection.SIDEWAYS_STRUCTURE


def test_bullish_impulses_corrections_and_pullback_depth() -> None:
    summary = analyze_impulse_correction(build_price_legs(bullish_points()), AltuninaStructureDirection.BULLISH_STRUCTURE)
    assert summary.bullish_impulse_total == 9
    assert summary.bullish_correction_total == 10
    assert summary.bearish_impulse_total == summary.bearish_correction_total == 0
    assert summary.dominant_impulse_direction is PriceLegDirection.UP
    assert summary.correction_count == 2
    assert summary.max_pullback_depth == pytest.approx(6 / 9)


def test_bearish_impulses_corrections_and_safe_initial_depth() -> None:
    summary = analyze_impulse_correction(build_price_legs(bearish_points()), AltuninaStructureDirection.BEARISH_STRUCTURE)
    assert summary.bearish_impulse_total == 13
    assert summary.bearish_correction_total == 2
    assert summary.dominant_impulse_direction is PriceLegDirection.DOWN
    assert summary.correction_count == 1
    assert summary.max_pullback_depth == pytest.approx(2 / 6)


def test_non_directional_structure_does_not_force_leg_roles() -> None:
    summary = analyze_impulse_correction(build_price_legs(bullish_points()), AltuninaStructureDirection.SIDEWAYS_STRUCTURE)
    assert summary.dominant_impulse_direction is PriceLegDirection.FLAT
    assert summary.correction_count == 0


@pytest.mark.parametrize(
    ("depth", "breached", "nearest"),
    [
        (0.38, False, 0.38),
        (0.50, False, 0.50),
        (0.62, False, 0.62),
        (0.63, True, 0.62),
    ],
)
def test_book_pullback_levels_and_limit(
    depth: float, breached: bool, nearest: float
) -> None:
    low = point(0, 100, SwingPointType.LOW)
    high = point(1, 110, SwingPointType.HIGH)
    correction = point(2, 110 - 10 * depth, SwingPointType.LOW)
    summary = analyze_impulse_correction(
        build_price_legs((low, high, correction)),
        AltuninaStructureDirection.BULLISH_STRUCTURE,
    )
    assert summary.max_pullback_depth == pytest.approx(depth)
    assert summary.correction_limit == ALTUNINA_CORRECTION_LIMIT
    assert summary.correction_limit_breached is breached
    assert summary.nearest_fibonacci_level == nearest


def test_structural_pivot_break_is_independent_from_ratio_label() -> None:
    low = point(0, 100, SwingPointType.LOW)
    high = point(1, 110, SwingPointType.HIGH)
    broken_low = point(2, 99, SwingPointType.LOW)
    summary = analyze_impulse_correction(
        build_price_legs((low, high, broken_low)),
        AltuninaStructureDirection.BULLISH_STRUCTURE,
    )
    assert summary.structural_pivot_breached


def test_trend_line_uses_structural_anchors() -> None:
    bullish = build_trend_line(
        bullish_points(), AltuninaStructureDirection.BULLISH_STRUCTURE
    )
    bearish = build_trend_line(
        bearish_points(), AltuninaStructureDirection.BEARISH_STRUCTURE
    )
    assert bullish.available and bullish.direction is PriceLegDirection.UP
    assert bullish.start and bullish.start.point_type is SwingPointType.LOW
    assert bearish.available and bearish.direction is PriceLegDirection.DOWN
    assert bearish.start and bearish.start.point_type is SwingPointType.HIGH


def test_duration_hierarchy_is_calendar_based_and_fail_closed() -> None:
    dated = (
        EngineTrendCandle("2025-01-01", 1, 2, 0, 1),
        EngineTrendCandle("2025-03-01", 1, 2, 0, 1),
    )
    result = classify_trend_duration(dated)
    assert result.duration_class is TrendDurationClass.MONTHLY_SCALE
    assert result.hierarchy_role is TrendHierarchyRole.INTERMEDIATE
    assert classify_trend_duration(bullish_candles()).duration_class is TrendDurationClass.UNKNOWN
    mixed_timezone = (
        EngineTrendCandle("2025-01-01", 1, 2, 0, 1),
        EngineTrendCandle("2025-02-01T00:00:00Z", 1, 2, 0, 1),
    )
    assert classify_trend_duration(mixed_timezone).duration_class is TrendDurationClass.UNKNOWN


@pytest.mark.parametrize(
    ("candles", "structure_code"),
    [(bullish_candles(), "ALTUNINA_BULLISH_STRUCTURE"), (bearish_candles(), "ALTUNINA_BEARISH_STRUCTURE")],
)
def test_main_context_has_altunina_evidence_and_directional_code(
    candles: tuple[EngineTrendCandle, ...], structure_code: str
) -> None:
    result = analyze_altunina_trend_context(candles)
    assert isinstance(result, AltuninaTrendContext)
    assert structure_code in result.reason_codes
    assert result.reason_codes == tuple(dict.fromkeys(item.code for item in result.evidence))
    assert all(item.source is BookSource.ALTUNINA for item in result.evidence)
    assert all("method_origin" in item.metadata for item in result.evidence)
    assert all(item.metadata["contribution_origin"] == DERIVED_HEURISTIC for item in result.evidence)
    assert result.trend_line.available
    if structure_code == "ALTUNINA_BULLISH_STRUCTURE":
        assert "ALTUNINA_PULLBACK_BREAKS_STRUCTURE" in result.reason_codes
    assert 0 <= result.trend_strength_score <= 1
    assert 0 <= result.trend_consistency_score <= 1
    assert 0 <= result.trend_progress_score <= 1


def test_main_context_sideways_and_insufficient_evidence() -> None:
    sideways = (
        candle(0, 103, 98), candle(1, 105, 99), candle(2, 102, 97),
        candle(3, 104, 99), candle(4, 103, 98), candle(5, 103, 100),
    )
    sideways_result = analyze_altunina_trend_context(sideways)
    assert "ALTUNINA_SIDEWAYS_STRUCTURE" in sideways_result.reason_codes
    insufficient = analyze_altunina_trend_context((candle(0, 2, 0), candle(1, 3, 1)))
    assert "ALTUNINA_INSUFFICIENT_SWING_POINTS" in insufficient.reason_codes
    assert "ALTUNINA_STRUCTURE_UNCLEAR" in insufficient.reason_codes


def test_dictionary_contract_has_expected_keys() -> None:
    data = analyze_altunina_trend_context(bullish_candles()).to_dict()
    assert {
        "candle_count", "swing_points", "price_legs", "structure_direction",
        "trend_line", "trend_duration",
        "trend_strength_score", "trend_consistency_score", "trend_progress_score",
        "impulse_correction", "evidence", "reason_codes", "summary",
    } == set(data)
    assert data["summary"]["score_method_origin"] == DERIVED_HEURISTIC
    assert FIBONACCI_PULLBACK_LEVELS == (0.38, 0.50, 0.62)


def test_stage_is_structural_context_only() -> None:
    result = analyze_altunina_trend_context(bullish_candles())
    assert not isinstance(result, EngineTrendResult)
    assert not hasattr(result, "market_regime")
    source = inspect.getsource(inspect.getmodule(analyze_altunina_trend_context))
    forbidden = ("B" "UY", "S" "ELL", "L" "ONG", "S" "HORT", "E" "NTRY", "E" "XIT")
    assert not any(word in source for word in forbidden)
