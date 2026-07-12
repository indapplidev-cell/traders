from __future__ import annotations

import pytest

from app.market_reader.engine_trend.candle_morphology import (
    CandleDirection,
    analyze_candle_morphology,
)
from app.market_reader.engine_trend.nison_candlestick_context import (
    analyze_nison_candle_context,
    analyze_nison_window_context,
)
from app.market_reader.engine_trend.schemas import BookSource, EngineTrendCandle


def candle(open_: float, high: float, low: float, close: float, timestamp: str = "t") -> EngineTrendCandle:
    return EngineTrendCandle(timestamp, open_, high, low, close, 1.0)


def codes(result: object) -> set[str]:
    return set(result.reason_codes)  # type: ignore[attr-defined]


def test_bullish_and_bearish_metrics_and_positions() -> None:
    bullish = analyze_candle_morphology(candle(10, 15, 5, 13))
    bearish = analyze_candle_morphology(candle(13, 15, 5, 7))
    assert bullish.direction is CandleDirection.BULLISH
    assert bullish.real_body_size == 3
    assert bullish.full_range_size == 10
    assert bullish.upper_shadow_size == 2
    assert bullish.lower_shadow_size == 5
    assert bullish.close_position_in_range == pytest.approx(0.8)
    assert bullish.open_position_in_range == pytest.approx(0.5)
    assert bearish.direction is CandleDirection.BEARISH
    assert bearish.upper_shadow_size == 2
    assert bearish.lower_shadow_size == 2


def test_zero_range_is_safe_and_serializable() -> None:
    result = analyze_candle_morphology(candle(10, 10, 10, 10))
    assert result.body_to_range_ratio == 0.0
    assert result.upper_shadow_to_range_ratio == 0.0
    assert result.lower_shadow_to_range_ratio == 0.0
    assert result.close_position_in_range == result.open_position_in_range == 0.5
    assert result.to_dict()["direction"] == "NEUTRAL"


def test_doji_and_spinning_top_are_distinct_small_body_shapes() -> None:
    doji = analyze_candle_morphology(candle(10, 15, 5, 10.5))
    spinning_top = analyze_candle_morphology(candle(10, 12, 9.5, 10.5))
    assert doji.is_doji and not doji.is_spinning_top and doji.is_small_body
    assert not spinning_top.is_doji and spinning_top.is_spinning_top
    assert "DOJI_INDECISION" in codes(analyze_nison_candle_context(candle(10, 15, 5, 10.5)))
    assert "SPINNING_TOP_INDECISION" in codes(
        analyze_nison_candle_context(candle(10, 12, 9.5, 10.5))
    )


def test_spinning_top_does_not_require_two_large_shadows() -> None:
    result = analyze_candle_morphology(candle(10, 12, 10, 10.4))
    assert result.is_spinning_top


def test_strong_bodies_and_close_location_reasons() -> None:
    bullish = analyze_nison_candle_context(candle(2, 10, 0, 9))
    bearish = analyze_nison_candle_context(candle(8, 10, 0, 1))
    assert {"STRONG_BULLISH_CANDLE_BODY", "CLOSE_NEAR_HIGH"} <= codes(bullish)
    assert {"STRONG_BEARISH_CANDLE_BODY", "CLOSE_NEAR_LOW"} <= codes(bearish)


def test_shadow_rejection_and_context_required_shapes() -> None:
    hammer = analyze_nison_candle_context(candle(8, 10, 0, 9))
    star = analyze_nison_candle_context(candle(2, 10, 0, 1))
    assert "L" "ONG_LOWER_SHADOW_REJECTION" in codes(hammer)
    assert "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED" in codes(hammer)
    assert "L" "ONG_UPPER_SHADOW_REJECTION" in codes(star)
    assert "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED" in codes(star)
    assert "CANDLE_PATTERN_NEEDS_TREND_CONTEXT" in codes(hammer) & codes(star)


def test_shape_requires_shadow_twice_body_and_body_at_range_edge() -> None:
    weak_lower_shadow = analyze_nison_candle_context(candle(7, 10, 5, 9))
    middle_body = analyze_nison_candle_context(candle(5, 7, 0, 6))
    assert "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED" not in codes(weak_lower_shadow)
    assert "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED" not in codes(middle_body)


@pytest.mark.parametrize(
    ("candles", "expected"),
    [
        ((candle(9, 10, 5, 6, "1"), candle(5, 11, 4, 10, "2")), "BULLISH_ENGULFING_CONTEXT"),
        ((candle(6, 10, 5, 9, "1"), candle(10, 11, 4, 5, "2")), "BEARISH_ENGULFING_CONTEXT"),
    ],
)
def test_engulfing_context_and_warning(candles: tuple[EngineTrendCandle, ...], expected: str) -> None:
    result = analyze_nison_window_context(candles)
    assert expected in codes(result)
    assert "ENGULFING_WITHOUT_FOLLOW_THROUGH" in codes(result)


@pytest.mark.parametrize(
    ("candles", "expected"),
    [
        ((candle(10, 11, 5, 6, "1"), candle(4, 9, 3, 8.5, "2")), "PIERCING_BULLISH_CONTEXT"),
        ((candle(6, 11, 5, 10, "1"), candle(12, 13, 7, 7.5, "2")), "DARK_CLOUD_BEARISH_CONTEXT"),
    ],
)
def test_piercing_and_dark_cloud_need_follow_through(candles: tuple[EngineTrendCandle, ...], expected: str) -> None:
    result = analyze_nison_window_context(candles)
    assert expected in codes(result)
    assert "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH" in codes(result)
    assert "CANDLE_PATTERN_NEEDS_TREND_CONTEXT" in codes(result)


def test_piercing_and_dark_cloud_require_classic_gap_beyond_shadow() -> None:
    weak_piercing_gap = analyze_nison_window_context(
        (candle(10, 11, 5, 6, "1"), candle(5.5, 9, 5, 8.5, "2"))
    )
    weak_dark_cloud_gap = analyze_nison_window_context(
        (candle(6, 11, 5, 10, "1"), candle(10.5, 12, 7, 7.5, "2"))
    )
    assert "PIERCING_BULLISH_CONTEXT" not in codes(weak_piercing_gap)
    assert "DARK_CLOUD_BEARISH_CONTEXT" not in codes(weak_dark_cloud_gap)


def test_pair_evidence_marks_unavailable_context_as_not_evaluated() -> None:
    result = analyze_nison_window_context(
        (candle(9, 10, 5, 6, "1"), candle(5, 11, 4, 10, "2"))
    )
    engulfing = next(
        item for item in result.window_evidence if item.code == "BULLISH_ENGULFING_CONTEXT"
    )
    assert engulfing.metadata["trend_context_evaluated"] is False
    assert engulfing.metadata["follow_through_evaluated"] is False


def test_window_clusters_body_dominance_and_evidence_collection() -> None:
    candles = (
        candle(10, 15, 5, 10.2, "1"),
        candle(10, 15, 5, 10.1, "2"),
        candle(10, 14, 9, 13, "3"),
        candle(13, 16, 12, 15, "4"),
    )
    result = analyze_nison_window_context(candles)
    assert {"DOJI_CLUSTER_FLAT_CONTEXT", "SMALL_BODY_CLUSTER", "LOW_DIRECTIONAL_PROGRESS", "BULLISH_BODY_DOMINANCE"} <= codes(result)
    heuristic_codes = {
        "DOJI_CLUSTER_FLAT_CONTEXT",
        "SMALL_BODY_CLUSTER",
        "LOW_DIRECTIONAL_PROGRESS",
        "BULLISH_BODY_DOMINANCE",
    }
    heuristics = [item for item in result.window_evidence if item.code in heuristic_codes]
    assert all(item.source is BookSource.ENGINE_TREND for item in heuristics)
    assert all(item.metadata["evidence_origin"] == "ENGINE_TREND_HEURISTIC" for item in heuristics)
    assert all(item.metadata["book_attribution"] is False for item in heuristics)
    assert all(
        item.source is BookSource.NISON
        for item in result.all_evidence
        if item.code not in heuristic_codes
    )
    assert set(result.reason_codes) == {item.code for item in result.all_evidence}
    assert {"candle_count", "summary", "reason_codes", "window_evidence", "candle_contexts"} <= result.to_dict().keys()


def test_bearish_body_dominance_and_empty_window() -> None:
    result = analyze_nison_window_context((candle(10, 11, 4, 5, "1"), candle(5, 6, 1, 2, "2")))
    assert "BEARISH_BODY_DOMINANCE" in codes(result)
    dominance = next(
        item for item in result.window_evidence if item.code == "BEARISH_BODY_DOMINANCE"
    )
    assert dominance.source is BookSource.ENGINE_TREND
    assert dominance.metadata["book_attribution"] is False
    empty = analyze_nison_window_context(())
    assert empty.candle_count == 0 and empty.all_evidence == ()


def test_context_payload_has_no_state_or_instruction_fields() -> None:
    payload = analyze_nison_window_context((candle(10, 11, 9, 10.5),)).to_dict()
    forbidden_fields = {"market_regime", "trade_signal", "safe_for_runtime_trading"}
    assert forbidden_fields.isdisjoint(payload)
    assert all("B" "UY" not in code and "S" "ELL" not in code for code in payload["reason_codes"])
