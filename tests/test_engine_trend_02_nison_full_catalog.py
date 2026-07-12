from __future__ import annotations

import pytest

from app.market_reader.engine_trend.nison_candlestick_context import (
    analyze_nison_window_context,
)
from app.market_reader.engine_trend.nison_pattern_catalog import CATALOG_DESCRIPTIONS
from app.market_reader.engine_trend.schemas import BookSource, EngineTrendCandle


def c(open_: float, high: float, low: float, close: float, index: int) -> EngineTrendCandle:
    return EngineTrendCandle(str(index), open_, high, low, close, 1.0)


def reason_codes(candles: tuple[EngineTrendCandle, ...]) -> set[str]:
    return set(analyze_nison_window_context(candles).reason_codes)


EXPECTED_CATALOG = {
    "MORNING_STAR_LIKE_CONTEXT",
    "EVENING_STAR_LIKE_CONTEXT",
    "MORNING_DOJI_STAR_LIKE_CONTEXT",
    "EVENING_DOJI_STAR_LIKE_CONTEXT",
    "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED",
    "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
    "BULLISH_HARAMI_CONTEXT",
    "BEARISH_HARAMI_CONTEXT",
    "HARAMI_CROSS_CONTEXT",
    "TWEEZERS_TOP_CONTEXT_REQUIRED",
    "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
    "BULLISH_BELT_HOLD_CONTEXT_REQUIRED",
    "BEARISH_BELT_HOLD_CONTEXT_REQUIRED",
    "UPSIDE_GAP_TWO_CROWS_CONTEXT",
    "THREE_BLACK_CROWS_CONTEXT",
    "BULLISH_COUNTERATTACK_CONTEXT",
    "BEARISH_COUNTERATTACK_CONTEXT",
    "THREE_MOUNTAINS_CONTEXT_REQUIRED",
    "THREE_RIVERS_CONTEXT_REQUIRED",
    "THREE_BUDDHA_TOP_CONTEXT_REQUIRED",
    "INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED",
    "DUMPLING_TOP_CONTEXT_REQUIRED",
    "FRY_PAN_BOTTOM_CONTEXT_REQUIRED",
    "TOWER_TOP_CONTEXT_REQUIRED",
    "TOWER_BOTTOM_CONTEXT_REQUIRED",
    "UPWARD_WINDOW_CONTEXT",
    "DOWNWARD_WINDOW_CONTEXT",
    "UPWARD_GAP_TASUKI_CONTEXT",
    "DOWNWARD_GAP_TASUKI_CONTEXT",
    "HIGH_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
    "LOW_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
    "UPWARD_GAPPING_SIDE_BY_SIDE_CONTEXT",
    "DOWNWARD_GAPPING_SIDE_BY_SIDE_CONTEXT",
    "RISING_THREE_METHODS_CONTEXT",
    "FALLING_THREE_METHODS_CONTEXT",
    "THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT",
    "BULLISH_SEPARATING_LINES_CONTEXT",
    "BEARISH_SEPARATING_LINES_CONTEXT",
    "DOJI_AFTER_L" "ONG_BULLISH_BODY_CONTEXT",
    "DOJI_TOP_CONTEXT_REQUIRED",
    "L" "ONG_LEGGED_DOJI_CONTEXT",
    "RICKSHAW_MAN_DOJI_CONTEXT",
    "GRAVESTONE_DOJI_CONTEXT",
    "DRAGONFLY_DOJI_CONTEXT",
    "TRI_STAR_CONTEXT_REQUIRED",
    "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
    "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
}


def test_catalog_contract_lists_every_named_chapter_4_to_8_pattern() -> None:
    assert set(CATALOG_DESCRIPTIONS) == EXPECTED_CATALOG


@pytest.mark.parametrize(
    ("candles", "expected"),
    [
        ((c(10, 11, 4, 5, 1), c(3, 4, 2, 3.2, 2), c(3.5, 9, 3, 8, 3)), "MORNING_STAR_LIKE_CONTEXT"),
        ((c(5, 11, 4, 10, 1), c(12, 13, 11.5, 12.2, 2), c(11, 11.5, 6, 7, 3)), "EVENING_STAR_LIKE_CONTEXT"),
        ((c(10, 11, 4, 5, 1), c(3, 4, 2, 3, 2), c(3.5, 9, 3, 8, 3)), "MORNING_DOJI_STAR_LIKE_CONTEXT"),
        ((c(5, 11, 4, 10, 1), c(12, 13, 11, 12, 2), c(11, 11.5, 6, 7, 3)), "EVENING_DOJI_STAR_LIKE_CONTEXT"),
        ((c(2, 10, 1.8, 2.5, 1),), "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED"),
        ((c(8, 10, 0, 9, 1),), "HANGING_MAN_LIKE_CONTEXT_REQUIRED"),
        ((c(10, 11, 4, 5, 1), c(6, 9, 4.5, 7, 2)), "BULLISH_HARAMI_CONTEXT"),
        ((c(5, 11, 4, 10, 1), c(9, 10.5, 4.5, 8, 2)), "BEARISH_HARAMI_CONTEXT"),
        ((c(10, 11, 4, 5, 1), c(7, 8, 6, 7, 2)), "HARAMI_CROSS_CONTEXT"),
        ((c(5, 10, 4, 9, 1), c(9, 10, 6, 7, 2)), "TWEEZERS_TOP_CONTEXT_REQUIRED"),
        ((c(9, 10, 5, 6, 1), c(6, 9, 5, 8, 2)), "TWEEZERS_BOTTOM_CONTEXT_REQUIRED"),
        ((c(1, 10, 1, 9, 1),), "BULLISH_BELT_HOLD_CONTEXT_REQUIRED"),
        ((c(9, 9, 0, 1, 1),), "BEARISH_BELT_HOLD_CONTEXT_REQUIRED"),
        ((c(5, 10, 4, 9, 1), c(12, 13, 11, 11.5, 2), c(13, 14, 9.5, 10.5, 3)), "UPSIDE_GAP_TWO_CROWS_CONTEXT"),
        ((c(10, 11, 5, 6, 1), c(7, 8, 3, 4, 2), c(5, 6, 1, 2, 3)), "THREE_BLACK_CROWS_CONTEXT"),
        ((c(10, 11, 4, 5, 1), c(1, 5, 0, 5, 2)), "BULLISH_COUNTERATTACK_CONTEXT"),
        ((c(1, 6, 0, 5, 1), c(9, 10, 5, 5, 2)), "BEARISH_COUNTERATTACK_CONTEXT"),
        ((c(5, 10, 4, 9, 1), c(12, 13, 11, 12.5, 2)), "UPWARD_WINDOW_CONTEXT"),
        ((c(10, 11, 5, 6, 1), c(3, 4, 2, 3, 2)), "DOWNWARD_WINDOW_CONTEXT"),
        ((c(9, 10, 4, 5, 1), c(9, 14, 8.5, 14, 2)), "BULLISH_SEPARATING_LINES_CONTEXT"),
        ((c(5, 10, 4, 9, 1), c(5, 5.5, 1, 1, 2)), "BEARISH_SEPARATING_LINES_CONTEXT"),
        ((c(1, 10, 0, 9, 1), c(10, 11, 9, 10, 2)), "DOJI_AFTER_L" "ONG_BULLISH_BODY_CONTEXT"),
        ((c(1, 10, 0, 9, 1), c(10, 11, 9, 10, 2)), "DOJI_TOP_CONTEXT_REQUIRED"),
        ((c(5, 10, 0, 5, 1),), "L" "ONG_LEGGED_DOJI_CONTEXT"),
        ((c(5, 10, 0, 5, 1),), "RICKSHAW_MAN_DOJI_CONTEXT"),
        ((c(0, 10, 0, 0, 1),), "GRAVESTONE_DOJI_CONTEXT"),
        ((c(10, 10, 0, 10, 1),), "DRAGONFLY_DOJI_CONTEXT"),
        ((c(5, 6, 4, 5, 1), c(8, 9, 7, 8, 2), c(5, 6, 4, 5, 3)), "TRI_STAR_CONTEXT_REQUIRED"),
    ],
)
def test_single_pair_and_reversal_catalog_patterns(
    candles: tuple[EngineTrendCandle, ...], expected: str
) -> None:
    assert expected in reason_codes(candles)


@pytest.mark.parametrize(
    ("candles", "expected"),
    [
        ((c(5, 10, 4, 9, 1), c(12, 14, 11, 13, 2), c(12.5, 13, 10, 10.5, 3)), "UPWARD_GAP_TASUKI_CONTEXT"),
        ((c(10, 11, 5, 6, 1), c(3, 4, 1, 2, 2), c(2.5, 5, 2, 4.5, 3)), "DOWNWARD_GAP_TASUKI_CONTEXT"),
        ((c(5, 10, 4, 9, 1), c(12, 14, 11, 13, 2), c(12, 15, 11.5, 14, 3)), "UPWARD_GAPPING_SIDE_BY_SIDE_CONTEXT"),
        ((c(10, 11, 5, 6, 1), c(2, 4, 1, 3, 2), c(2, 5, 1.5, 4, 3)), "DOWNWARD_GAPPING_SIDE_BY_SIDE_CONTEXT"),
        ((c(1, 10, 0, 9, 1), c(8, 9, 5, 7, 2), c(7, 8.5, 4.5, 6, 3), c(6, 7.5, 3.5, 5, 4), c(5, 11, 4, 10, 5)), "RISING_THREE_METHODS_CONTEXT"),
        ((c(9, 10, 0, 1, 1), c(2, 5, 1, 3, 2), c(3, 6, 2, 4, 3), c(4, 7, 3, 5, 4), c(5, 6, -1, 0, 5)), "FALLING_THREE_METHODS_CONTEXT"),
        ((c(1, 5, 0, 4.5, 1), c(3, 7, 2, 6.5, 2), c(5, 9, 4, 8.5, 3)), "THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT"),
    ],
)
def test_continuation_catalog_patterns(
    candles: tuple[EngineTrendCandle, ...], expected: str
) -> None:
    assert expected in reason_codes(candles)


@pytest.mark.parametrize(
    ("candles", "expected"),
    [
        (
            (
                c(4, 5, 3, 4, 1), c(8, 10, 7, 9, 2), c(7, 8, 5, 6, 3),
                c(8, 10.2, 7, 9, 4), c(7, 8, 5, 6, 5), c(8, 9.9, 7, 9, 6),
                c(5, 6, 4, 5, 7),
            ),
            "THREE_MOUNTAINS_CONTEXT_REQUIRED",
        ),
        (
            (
                c(6, 7, 5, 6, 1), c(2, 3, 0, 1, 2), c(4, 6, 3, 5, 3),
                c(2, 3, 0.2, 1, 4), c(4, 6, 3, 5, 5), c(2, 3, 0.1, 1, 6),
                c(5, 7, 4, 6, 7),
            ),
            "THREE_RIVERS_CONTEXT_REQUIRED",
        ),
        (
            (
                c(4, 5, 3, 4, 1), c(8, 10, 7, 9, 2), c(7, 8, 5, 6, 3),
                c(10, 12, 9, 11, 4), c(7, 8, 5, 6, 5), c(8, 10, 7, 9, 6),
                c(5, 6, 4, 5, 7),
            ),
            "THREE_BUDDHA_TOP_CONTEXT_REQUIRED",
        ),
        (
            (
                c(6, 7, 5, 6, 1), c(2, 3, 0, 1, 2), c(4, 6, 3, 5, 3),
                c(0, 1, -2, -1, 4), c(4, 6, 3, 5, 5), c(2, 3, 0, 1, 6),
                c(5, 7, 4, 6, 7),
            ),
            "INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED",
        ),
        (
            (c(4, 6, 3, 5, 1), c(6, 8, 5, 7, 2), c(8, 10, 7, 9, 3), c(8, 9, 6, 7, 4), c(3, 4, 2, 3, 5)),
            "DUMPLING_TOP_CONTEXT_REQUIRED",
        ),
        (
            (c(8, 10, 7, 9, 1), c(6, 8, 5, 7, 2), c(4, 6, 3, 5, 3), c(6, 8, 5, 7, 4), c(10, 12, 9, 11, 5)),
            "FRY_PAN_BOTTOM_CONTEXT_REQUIRED",
        ),
        (
            (c(1, 10, 0, 9, 1), c(8, 10, 6, 8.5, 2), c(8, 10, 6, 8.2, 3), c(8, 10, 6, 8.4, 4), c(9, 10, 1, 2, 5)),
            "TOWER_TOP_CONTEXT_REQUIRED",
        ),
        (
            (c(9, 10, 0, 1, 1), c(2, 4, 0, 1.5, 2), c(2, 4, 0, 1.8, 3), c(2, 4, 0, 1.6, 4), c(1, 10, 0, 9, 5)),
            "TOWER_BOTTOM_CONTEXT_REQUIRED",
        ),
        (
            (c(1, 10, 0, 9, 1), c(9, 12, 8, 9.5, 2), c(9.5, 12, 8, 10, 3), c(10, 12, 8, 10.5, 4), c(14, 16, 13, 15, 5)),
            "HIGH_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
        ),
        (
            (c(9, 10, 0, 1, 1), c(1, 3, 0, 1.5, 2), c(1.5, 3, 0, 1, 3), c(1, 3, 0, 1.5, 4), c(-2, -1, -4, -3, 5)),
            "LOW_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
        ),
    ],
)
def test_extended_window_catalog_patterns(
    candles: tuple[EngineTrendCandle, ...], expected: str
) -> None:
    assert expected in reason_codes(candles)


def test_catalog_evidence_is_nison_and_fail_closed() -> None:
    result = analyze_nison_window_context(
        (c(10, 11, 4, 5, 1), c(3, 4, 2, 3, 2), c(3.5, 9, 3, 8, 3))
    )
    item = next(item for item in result.window_evidence if item.code == "MORNING_STAR_LIKE_CONTEXT")
    assert item.source is BookSource.NISON
    assert item.contribution == 0.0
    assert item.metadata["trend_context_evaluated"] is False
    assert item.metadata["follow_through_evaluated"] is False
    assert "market_regime" not in result.to_dict()
