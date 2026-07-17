"""OHLC-only candidates for the named Nison patterns in book chapters 4-8.

The detectors deliberately describe pattern geometry.  They do not establish
the preceding trend, support/resistance, or subsequent confirmation required
for a full chart interpretation.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.engine_analysis.candle_morphology import CandleMorphology
from app.engine_analysis.schemas import BookSource, EngineAnalysisEvidence


_DOJI_AFTER_LARGE_BODY_CODE = "DOJI_AFTER_L" "ONG_BULLISH_BODY_CONTEXT"
_EXTENDED_LEGGED_DOJI_CODE = "L" "ONG_LEGGED_DOJI_CONTEXT"


CATALOG_DESCRIPTIONS: dict[str, str] = {
    "MORNING_STAR_LIKE_CONTEXT": "Morning-star-like three-candle geometry",
    "EVENING_STAR_LIKE_CONTEXT": "Evening-star-like three-candle geometry",
    "MORNING_DOJI_STAR_LIKE_CONTEXT": "Morning doji-star-like geometry",
    "EVENING_DOJI_STAR_LIKE_CONTEXT": "Evening doji-star-like geometry",
    "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED": "Inverted-hammer-like shape requires a preceding decline",
    "HANGING_MAN_LIKE_CONTEXT_REQUIRED": "Hanging-man-like shape requires a preceding rise",
    "BULLISH_HARAMI_CONTEXT": "Small body is contained by the preceding bearish body",
    "BEARISH_HARAMI_CONTEXT": "Small body is contained by the preceding bullish body",
    "HARAMI_CROSS_CONTEXT": "Doji body is contained by the preceding long body",
    "TWEEZERS_TOP_CONTEXT_REQUIRED": "Adjacent highs form a tweezer-top candidate",
    "TWEEZERS_BOTTOM_CONTEXT_REQUIRED": "Adjacent lows form a tweezer-bottom candidate",
    "BULLISH_BELT_HOLD_CONTEXT_REQUIRED": "Bullish belt-hold-like candle geometry",
    "BEARISH_BELT_HOLD_CONTEXT_REQUIRED": "Bearish belt-hold-like candle geometry",
    "UPSIDE_GAP_TWO_CROWS_CONTEXT": "Upside-gap two-crows geometry",
    "THREE_BLACK_CROWS_CONTEXT": "Three descending bearish candles form a three-crows candidate",
    "BULLISH_COUNTERATTACK_CONTEXT": "Opposite long bodies close at approximately the same level",
    "BEARISH_COUNTERATTACK_CONTEXT": "Opposite long bodies close at approximately the same level",
    "THREE_MOUNTAINS_CONTEXT_REQUIRED": "Three comparable local peaks form a three-mountains candidate",
    "THREE_RIVERS_CONTEXT_REQUIRED": "Three comparable local troughs form a three-rivers candidate",
    "THREE_BUDDHA_TOP_CONTEXT_REQUIRED": "Middle peak above two comparable peaks forms a three-Buddha candidate",
    "INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED": "Middle trough below two comparable troughs forms an inverted three-Buddha candidate",
    "DUMPLING_TOP_CONTEXT_REQUIRED": "Rounded-top geometry with downside completion gap",
    "FRY_PAN_BOTTOM_CONTEXT_REQUIRED": "Rounded-bottom geometry with upside completion gap",
    "TOWER_TOP_CONTEXT_REQUIRED": "Tower-top transition geometry",
    "TOWER_BOTTOM_CONTEXT_REQUIRED": "Tower-bottom transition geometry",
    "UPWARD_WINDOW_CONTEXT": "Current low is above the preceding high",
    "DOWNWARD_WINDOW_CONTEXT": "Current high is below the preceding low",
    "UPWARD_GAP_TASUKI_CONTEXT": "Upward-gap tasuki geometry",
    "DOWNWARD_GAP_TASUKI_CONTEXT": "Downward-gap tasuki geometry",
    "HIGH_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED": "High-price gapping-play geometry",
    "LOW_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED": "Low-price gapping-play geometry",
    "UPWARD_GAPPING_SIDE_BY_SIDE_CONTEXT": "Upward-gapping side-by-side bullish bodies",
    "DOWNWARD_GAPPING_SIDE_BY_SIDE_CONTEXT": "Downward-gapping side-by-side bullish bodies",
    "RISING_THREE_METHODS_CONTEXT": "Rising three-methods continuation geometry",
    "FALLING_THREE_METHODS_CONTEXT": "Falling three-methods continuation geometry",
    "THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT": "Three progressively higher bullish candles",
    "BULLISH_SEPARATING_LINES_CONTEXT": "Bearish and bullish candles share approximately one open",
    "BEARISH_SEPARATING_LINES_CONTEXT": "Bullish and bearish candles share approximately one open",
    _DOJI_AFTER_LARGE_BODY_CODE: "Doji follows a long bullish body",
    "DOJI_TOP_CONTEXT_REQUIRED": "Doji after bullish expansion requires top context",
    _EXTENDED_LEGGED_DOJI_CODE: "Doji has extended upper and lower shadows",
    "RICKSHAW_MAN_DOJI_CONTEXT": "Long-legged doji opens and closes near range midpoint",
    "GRAVESTONE_DOJI_CONTEXT": "Doji lies near the low with an extended upper shadow",
    "DRAGONFLY_DOJI_CONTEXT": "Doji lies near the high with an extended lower shadow",
    "TRI_STAR_CONTEXT_REQUIRED": "Three doji candles form a tri-star candidate",
    "CANDLE_PATTERN_NEEDS_TREND_CONTEXT": "Pattern geometry cannot determine state without trend context",
    "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH": "Reversal-like geometry requires follow-through",
}


def _evidence(code: str, candles: Iterable[CandleMorphology]) -> EngineAnalysisEvidence:
    items = tuple(candles)
    return EngineAnalysisEvidence(
        source=BookSource.NISON,
        code=code,
        description=CATALOG_DESCRIPTIONS[code],
        contribution=0.0,
        metadata={
            "timestamps": [item.timestamp for item in items],
            "trend_context_evaluated": False,
            "follow_through_evaluated": False,
            "catalog_scope": "NISON_CHAPTERS_4_TO_8",
        },
    )


def _approximately_equal(left: float, right: float, scale: float, ratio: float = 0.05) -> bool:
    tolerance = max(abs(scale) * ratio, 1e-12)
    return abs(left - right) <= tolerance


def _body_low(item: CandleMorphology) -> float:
    return min(item.open, item.close)


def _body_high(item: CandleMorphology) -> float:
    return max(item.open, item.close)


def _body_inside(inner: CandleMorphology, outer: CandleMorphology) -> bool:
    return _body_low(inner) >= _body_low(outer) and _body_high(inner) <= _body_high(outer)


def _gap_up(left: CandleMorphology, right: CandleMorphology) -> bool:
    return right.low > left.high


def _gap_down(left: CandleMorphology, right: CandleMorphology) -> bool:
    return right.high < left.low


def _body_gap_up(left: CandleMorphology, right: CandleMorphology) -> bool:
    return _body_low(right) > _body_high(left)


def _body_gap_down(left: CandleMorphology, right: CandleMorphology) -> bool:
    return _body_high(right) < _body_low(left)


def _append_with_cautions(
    output: list[EngineAnalysisEvidence],
    code: str,
    candles: tuple[CandleMorphology, ...],
    *,
    reversal: bool = False,
) -> None:
    output.append(_evidence(code, candles))
    output.append(_evidence("CANDLE_PATTERN_NEEDS_TREND_CONTEXT", candles))
    if reversal:
        output.append(_evidence("REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH", candles))


def _detect_single(items: tuple[CandleMorphology, ...], output: list[EngineAnalysisEvidence]) -> None:
    for item in items:
        one = (item,)
        inverted = (
            item.real_body_size > 0.0
            and item.is_small_body
            and item.upper_shadow_size >= item.real_body_size * 2.0
            and item.lower_shadow_to_range_ratio <= 0.10
            and max(item.open_position_in_range, item.close_position_in_range) <= 0.40
        )
        if inverted:
            _append_with_cautions(output, "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED", one, reversal=True)
        hanging_man = (
            item.real_body_size > 0.0
            and item.is_small_body
            and item.lower_shadow_size >= item.real_body_size * 2.0
            and item.upper_shadow_to_range_ratio <= 0.10
            and min(item.open_position_in_range, item.close_position_in_range) >= 0.60
        )
        if hanging_man:
            _append_with_cautions(output, "HANGING_MAN_LIKE_CONTEXT_REQUIRED", one, reversal=True)
        if item.is_bullish and item.is_long_body and item.open_position_in_range <= 0.10:
            _append_with_cautions(output, "BULLISH_BELT_HOLD_CONTEXT_REQUIRED", one)
        if item.is_bearish and item.is_long_body and item.open_position_in_range >= 0.90:
            _append_with_cautions(output, "BEARISH_BELT_HOLD_CONTEXT_REQUIRED", one)
        if item.is_doji and item.upper_shadow_to_range_ratio >= 0.35 and item.lower_shadow_to_range_ratio >= 0.35:
            output.append(_evidence(_EXTENDED_LEGGED_DOJI_CODE, one))
            if 0.40 <= item.open_position_in_range <= 0.60:
                output.append(_evidence("RICKSHAW_MAN_DOJI_CONTEXT", one))
        if item.is_doji and item.open_position_in_range <= 0.10 and item.upper_shadow_to_range_ratio >= 0.60:
            _append_with_cautions(output, "GRAVESTONE_DOJI_CONTEXT", one, reversal=True)
        if item.is_doji and item.open_position_in_range >= 0.90 and item.lower_shadow_to_range_ratio >= 0.60:
            _append_with_cautions(output, "DRAGONFLY_DOJI_CONTEXT", one, reversal=True)


def _detect_pairs(items: tuple[CandleMorphology, ...], output: list[EngineAnalysisEvidence]) -> None:
    for previous, current in zip(items, items[1:]):
        pair = (previous, current)
        if previous.is_long_body and current.is_small_body and _body_inside(current, previous):
            code = "BULLISH_HARAMI_CONTEXT" if previous.is_bearish else "BEARISH_HARAMI_CONTEXT"
            _append_with_cautions(output, code, pair, reversal=True)
            if current.is_doji:
                _append_with_cautions(output, "HARAMI_CROSS_CONTEXT", pair, reversal=True)
        scale = max(previous.full_range_size, current.full_range_size)
        if _approximately_equal(previous.high, current.high, scale):
            _append_with_cautions(output, "TWEEZERS_TOP_CONTEXT_REQUIRED", pair, reversal=True)
        if _approximately_equal(previous.low, current.low, scale):
            _append_with_cautions(output, "TWEEZERS_BOTTOM_CONTEXT_REQUIRED", pair, reversal=True)
        if previous.is_bearish and current.is_bullish and previous.is_long_body and current.is_long_body and _approximately_equal(previous.close, current.close, scale):
            _append_with_cautions(output, "BULLISH_COUNTERATTACK_CONTEXT", pair, reversal=True)
        if previous.is_bullish and current.is_bearish and previous.is_long_body and current.is_long_body and _approximately_equal(previous.close, current.close, scale):
            _append_with_cautions(output, "BEARISH_COUNTERATTACK_CONTEXT", pair, reversal=True)
        if _gap_up(previous, current):
            output.append(_evidence("UPWARD_WINDOW_CONTEXT", pair))
        if _gap_down(previous, current):
            output.append(_evidence("DOWNWARD_WINDOW_CONTEXT", pair))
        if previous.is_bearish and current.is_bullish and _approximately_equal(previous.open, current.open, scale):
            _append_with_cautions(output, "BULLISH_SEPARATING_LINES_CONTEXT", pair)
        if previous.is_bullish and current.is_bearish and _approximately_equal(previous.open, current.open, scale):
            _append_with_cautions(output, "BEARISH_SEPARATING_LINES_CONTEXT", pair)
        if previous.is_long_body and previous.is_bullish and current.is_doji:
            _append_with_cautions(output, _DOJI_AFTER_LARGE_BODY_CODE, pair, reversal=True)
            _append_with_cautions(output, "DOJI_TOP_CONTEXT_REQUIRED", pair, reversal=True)


def _detect_triples(items: tuple[CandleMorphology, ...], output: list[EngineAnalysisEvidence]) -> None:
    for first, second, third in zip(items, items[1:], items[2:]):
        triple = (first, second, third)
        first_midpoint = (first.open + first.close) / 2.0
        morning = first.is_bearish and first.is_long_body and second.is_small_body and _body_gap_down(first, second) and third.is_bullish and third.close > first_midpoint
        evening = first.is_bullish and first.is_long_body and second.is_small_body and _body_gap_up(first, second) and third.is_bearish and third.close < first_midpoint
        if morning:
            _append_with_cautions(output, "MORNING_STAR_LIKE_CONTEXT", triple, reversal=True)
            if second.is_doji:
                _append_with_cautions(output, "MORNING_DOJI_STAR_LIKE_CONTEXT", triple, reversal=True)
        if evening:
            _append_with_cautions(output, "EVENING_STAR_LIKE_CONTEXT", triple, reversal=True)
            if second.is_doji:
                _append_with_cautions(output, "EVENING_DOJI_STAR_LIKE_CONTEXT", triple, reversal=True)
        upside_two_crows = first.is_bullish and first.is_long_body and second.is_bearish and _body_gap_up(first, second) and third.is_bearish and third.open > second.open and first.close < third.close < second.close
        if upside_two_crows:
            _append_with_cautions(output, "UPSIDE_GAP_TWO_CROWS_CONTEXT", triple, reversal=True)
        three_crows = all(item.is_bearish for item in triple) and all(item.is_long_body for item in triple) and first.close > second.close > third.close and _body_low(first) <= second.open <= _body_high(first) and _body_low(second) <= third.open <= _body_high(second)
        if three_crows:
            _append_with_cautions(output, "THREE_BLACK_CROWS_CONTEXT", triple, reversal=True)
        soldiers = all(item.is_bullish for item in triple) and first.close < second.close < third.close and first.open < second.open < third.open and all(item.close_position_in_range >= 0.75 for item in triple)
        if soldiers:
            _append_with_cautions(output, "THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT", triple)
        if all(item.is_doji for item in triple) and ((_body_gap_up(first, second) and _body_gap_down(second, third)) or (_body_gap_down(first, second) and _body_gap_up(second, third))):
            _append_with_cautions(output, "TRI_STAR_CONTEXT_REQUIRED", triple, reversal=True)
        upward_tasuki = (
            first.is_bullish
            and second.is_bullish
            and third.is_bearish
            and _gap_up(first, second)
            and _body_low(second) <= third.open <= _body_high(second)
            and first.high < third.close < second.low
        )
        if upward_tasuki:
            _append_with_cautions(output, "UPWARD_GAP_TASUKI_CONTEXT", triple)
        downward_tasuki = (
            first.is_bearish
            and second.is_bearish
            and third.is_bullish
            and _gap_down(first, second)
            and _body_low(second) <= third.open <= _body_high(second)
            and second.high < third.close < first.low
        )
        if downward_tasuki:
            _append_with_cautions(output, "DOWNWARD_GAP_TASUKI_CONTEXT", triple)
        side_scale = max(second.full_range_size, third.full_range_size)
        if second.is_bullish and third.is_bullish and _approximately_equal(second.open, third.open, side_scale):
            if _gap_up(first, second):
                _append_with_cautions(output, "UPWARD_GAPPING_SIDE_BY_SIDE_CONTEXT", triple)
            if _gap_down(first, second):
                _append_with_cautions(output, "DOWNWARD_GAPPING_SIDE_BY_SIDE_CONTEXT", triple)


def _detect_multi(items: tuple[CandleMorphology, ...], output: list[EngineAnalysisEvidence]) -> None:
    for length in range(4, min(8, len(items)) + 1):
        for start in range(len(items) - length + 1):
            group = items[start : start + length]
            first, last = group[0], group[-1]
            middle = group[1:-1]
            rising = first.is_bullish and first.is_long_body and last.is_bullish and last.is_long_body and last.close > first.close and all(item.is_small_body and item.high <= first.high and item.low >= first.low for item in middle)
            falling = first.is_bearish and first.is_long_body and last.is_bearish and last.is_long_body and last.close < first.close and all(item.is_small_body and item.high <= first.high and item.low >= first.low for item in middle)
            if rising:
                _append_with_cautions(output, "RISING_THREE_METHODS_CONTEXT", group)
            if falling:
                _append_with_cautions(output, "FALLING_THREE_METHODS_CONTEXT", group)

    if len(items) < 5:
        return
    scale = max((item.full_range_size for item in items), default=0.0)
    highs = [item.high for item in items]
    lows = [item.low for item in items]
    peak_indices = [i for i in range(1, len(items) - 1) if highs[i] > highs[i - 1] and highs[i] >= highs[i + 1]]
    trough_indices = [i for i in range(1, len(items) - 1) if lows[i] < lows[i - 1] and lows[i] <= lows[i + 1]]
    if len(peak_indices) >= 3:
        peaks = tuple(items[i] for i in peak_indices[-3:])
        if max(item.high for item in peaks) - min(item.high for item in peaks) <= scale * 0.15:
            _append_with_cautions(output, "THREE_MOUNTAINS_CONTEXT_REQUIRED", peaks, reversal=True)
        if peaks[1].high > max(peaks[0].high, peaks[2].high) and _approximately_equal(
            peaks[0].high, peaks[2].high, scale, ratio=0.15
        ):
            _append_with_cautions(output, "THREE_BUDDHA_TOP_CONTEXT_REQUIRED", peaks, reversal=True)
    if len(trough_indices) >= 3:
        troughs = tuple(items[i] for i in trough_indices[-3:])
        if max(item.low for item in troughs) - min(item.low for item in troughs) <= scale * 0.15:
            _append_with_cautions(output, "THREE_RIVERS_CONTEXT_REQUIRED", troughs, reversal=True)
        if troughs[1].low < min(troughs[0].low, troughs[2].low) and _approximately_equal(
            troughs[0].low, troughs[2].low, scale, ratio=0.15
        ):
            _append_with_cautions(
                output,
                "INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED",
                troughs,
                reversal=True,
            )

    closes = [item.close for item in items]
    midpoint = len(items) // 2
    rounded_top = all(closes[i] <= closes[i + 1] for i in range(midpoint)) and all(closes[i] >= closes[i + 1] for i in range(midpoint, len(items) - 1))
    rounded_bottom = all(closes[i] >= closes[i + 1] for i in range(midpoint)) and all(closes[i] <= closes[i + 1] for i in range(midpoint, len(items) - 1))
    if rounded_top and _gap_down(items[-2], items[-1]):
        _append_with_cautions(output, "DUMPLING_TOP_CONTEXT_REQUIRED", items, reversal=True)
    if rounded_bottom and _gap_up(items[-2], items[-1]):
        _append_with_cautions(output, "FRY_PAN_BOTTOM_CONTEXT_REQUIRED", items, reversal=True)

    small_middle = sum(item.is_small_body for item in items[1:-1]) >= max(2, len(items[1:-1]) // 2)
    if items[0].is_bullish and items[0].is_long_body and items[-1].is_bearish and items[-1].is_long_body and small_middle:
        _append_with_cautions(output, "TOWER_TOP_CONTEXT_REQUIRED", items, reversal=True)
    if items[0].is_bearish and items[0].is_long_body and items[-1].is_bullish and items[-1].is_long_body and small_middle:
        _append_with_cautions(output, "TOWER_BOTTOM_CONTEXT_REQUIRED", items, reversal=True)

    consolidation = items[-4:-1]
    if len(consolidation) == 3 and all(item.is_small_body for item in consolidation):
        if items[-1].is_bullish and _gap_up(items[-2], items[-1]):
            _append_with_cautions(output, "HIGH_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED", items[-5:])
        if items[-1].is_bearish and _gap_down(items[-2], items[-1]):
            _append_with_cautions(output, "LOW_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED", items[-5:])


def analyze_nison_pattern_catalog(
    morphologies: tuple[CandleMorphology, ...],
) -> tuple[EngineAnalysisEvidence, ...]:
    """Return all OHLC-only catalog candidates found in input order."""

    output: list[EngineAnalysisEvidence] = []
    _detect_single(morphologies, output)
    _detect_pairs(morphologies, output)
    _detect_triples(morphologies, output)
    _detect_multi(morphologies, output)
    unique: dict[tuple[str, tuple[str, ...]], EngineAnalysisEvidence] = {}
    for item in output:
        key = (item.code, tuple(item.metadata.get("timestamps", ())))
        unique.setdefault(key, item)
    return tuple(unique.values())
