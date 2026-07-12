"""Conservative Steve Nison candlestick evidence for engine_trend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.market_reader.engine_trend.candle_morphology import (
    CandleMorphology,
    analyze_candle_morphology,
    analyze_candle_window_morphology,
)
from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendCandle,
    EngineTrendEvidence,
)
from app.market_reader.engine_trend.nison_pattern_catalog import (
    analyze_nison_pattern_catalog,
)


_UPPER_SHADOW_CODE = "L" "ONG_UPPER_SHADOW_REJECTION"
_LOWER_SHADOW_CODE = "L" "ONG_LOWER_SHADOW_REJECTION"
SHADOW_TO_BODY_SHAPE_MIN = 2.0
OPPOSITE_SHADOW_TO_RANGE_MAX = 0.10
HAMMER_BODY_POSITION_MIN = 0.60
STAR_BODY_POSITION_MAX = 0.40

_EVIDENCE: dict[str, tuple[str, float]] = {
    "STRONG_BULLISH_CANDLE_BODY": ("Strong bullish real body", 0.10),
    "STRONG_BEARISH_CANDLE_BODY": ("Strong bearish real body", -0.10),
    _UPPER_SHADOW_CODE: ("Extended upper shadow provides rejection evidence", -0.05),
    _LOWER_SHADOW_CODE: ("Extended lower shadow provides rejection evidence", 0.05),
    "SMALL_BODY_INDECISION": ("Small real body provides indecision evidence", 0.0),
    "CLOSE_NEAR_HIGH": ("Close is near the candle high", 0.0),
    "CLOSE_NEAR_LOW": ("Close is near the candle low", 0.0),
    "DOJI_INDECISION": ("Doji morphology provides indecision evidence", 0.0),
    "SPINNING_TOP_INDECISION": ("Spinning-top morphology provides indecision evidence", 0.0),
    "DOJI_CLUSTER_FLAT_CONTEXT": ("Multiple doji candles form a flat-context clue", 0.0),
    "SMALL_BODY_CLUSTER": ("Small real bodies cluster in the selected window", 0.0),
    "LOW_DIRECTIONAL_PROGRESS": ("Body contraction suggests limited directional progress", 0.0),
    "BULLISH_BODY_DOMINANCE": ("Bullish real-body size dominates the window", 0.15),
    "BEARISH_BODY_DOMINANCE": ("Bearish real-body size dominates the window", -0.15),
    "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED": ("Hammer-like shape requires trend context", 0.0),
    "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED": ("Shooting-star-like shape requires trend context", 0.0),
    "CANDLE_PATTERN_NEEDS_TREND_CONTEXT": ("Candle shape cannot determine state without trend context", 0.0),
    "BULLISH_ENGULFING_CONTEXT": ("Bullish body engulfs the preceding bearish body", 0.10),
    "BEARISH_ENGULFING_CONTEXT": ("Bearish body engulfs the preceding bullish body", -0.10),
    "ENGULFING_WITHOUT_FOLLOW_THROUGH": ("Engulfing follow-through is not evaluated at this stage", 0.0),
    "DARK_CLOUD_BEARISH_CONTEXT": ("Dark-cloud body relationship provides bearish context", -0.08),
    "PIERCING_BULLISH_CONTEXT": ("Piercing body relationship provides bullish context", 0.08),
    "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH": ("Reversal-like relationship requires follow-through", 0.0),
}


def _evidence(code: str, **metadata: Any) -> EngineTrendEvidence:
    description, contribution = _EVIDENCE[code]
    return EngineTrendEvidence(BookSource.NISON, code, description, contribution, metadata)


def _engine_heuristic_evidence(code: str, **metadata: Any) -> EngineTrendEvidence:
    """Create derived window evidence without attributing it to Nison."""

    description, contribution = _EVIDENCE[code]
    heuristic_metadata = {
        "evidence_origin": "ENGINE_TREND_HEURISTIC",
        "book_attribution": False,
        **metadata,
    }
    return EngineTrendEvidence(
        BookSource.ENGINE_TREND,
        code,
        description,
        contribution,
        heuristic_metadata,
    )


def _unique_codes(items: tuple[EngineTrendEvidence, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.code for item in items))


@dataclass(frozen=True)
class NisonCandleContext:
    timestamp: str
    morphology: CandleMorphology
    evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "morphology": self.morphology.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class NisonWindowContext:
    candle_count: int
    candle_contexts: tuple[NisonCandleContext, ...]
    window_evidence: tuple[EngineTrendEvidence, ...]
    all_evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    summary: dict[str, float | int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candle_count": self.candle_count,
            "summary": dict(self.summary),
            "reason_codes": list(self.reason_codes),
            "window_evidence": [item.to_dict() for item in self.window_evidence],
            "all_evidence": [item.to_dict() for item in self.all_evidence],
            "candle_contexts": [item.to_dict() for item in self.candle_contexts],
        }


def _single_candle_evidence(morphology: CandleMorphology) -> tuple[EngineTrendEvidence, ...]:
    codes: list[str] = []
    if morphology.is_strong_bullish_body:
        codes.append("STRONG_BULLISH_CANDLE_BODY")
    if morphology.is_strong_bearish_body:
        codes.append("STRONG_BEARISH_CANDLE_BODY")
    if morphology.has_long_upper_shadow:
        codes.append(_UPPER_SHADOW_CODE)
    if morphology.has_long_lower_shadow:
        codes.append(_LOWER_SHADOW_CODE)
    if morphology.is_small_body:
        codes.append("SMALL_BODY_INDECISION")
    if morphology.close_near_high:
        codes.append("CLOSE_NEAR_HIGH")
    if morphology.close_near_low:
        codes.append("CLOSE_NEAR_LOW")
    if morphology.is_doji:
        codes.append("DOJI_INDECISION")
    if morphology.is_spinning_top:
        codes.append("SPINNING_TOP_INDECISION")

    hammer_like = (
        morphology.real_body_size > 0.0
        and morphology.lower_shadow_size
        >= morphology.real_body_size * SHADOW_TO_BODY_SHAPE_MIN
        and morphology.body_to_range_ratio <= 0.30
        and min(morphology.close_position_in_range, morphology.open_position_in_range)
        >= HAMMER_BODY_POSITION_MIN
        and morphology.upper_shadow_to_range_ratio <= OPPOSITE_SHADOW_TO_RANGE_MAX
    )
    shooting_star_like = (
        morphology.real_body_size > 0.0
        and morphology.upper_shadow_size
        >= morphology.real_body_size * SHADOW_TO_BODY_SHAPE_MIN
        and morphology.body_to_range_ratio <= 0.30
        and max(morphology.close_position_in_range, morphology.open_position_in_range)
        <= STAR_BODY_POSITION_MAX
        and morphology.lower_shadow_to_range_ratio <= OPPOSITE_SHADOW_TO_RANGE_MAX
    )
    if hammer_like:
        codes.extend(("HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED", "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"))
    if shooting_star_like:
        codes.extend(("SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED", "CANDLE_PATTERN_NEEDS_TREND_CONTEXT"))

    return tuple(_evidence(code, timestamp=morphology.timestamp) for code in dict.fromkeys(codes))


def analyze_nison_candle_context(candle: EngineTrendCandle) -> NisonCandleContext:
    morphology = analyze_candle_morphology(candle)
    evidence = _single_candle_evidence(morphology)
    return NisonCandleContext(candle.timestamp, morphology, evidence, _unique_codes(evidence))


def _pair_evidence(previous: CandleMorphology, current: CandleMorphology) -> tuple[EngineTrendEvidence, ...]:
    codes: list[str] = []
    bullish_engulfing = (
        previous.is_bearish and current.is_bullish
        and current.open <= previous.close and current.close >= previous.open
    )
    bearish_engulfing = (
        previous.is_bullish and current.is_bearish
        and current.open >= previous.close and current.close <= previous.open
    )
    midpoint = (previous.open + previous.close) / 2.0
    piercing = (
        previous.is_bearish and previous.is_long_body and current.is_bullish
        and current.open < previous.low
        and midpoint < current.close < previous.open
    )
    dark_cloud = (
        previous.is_bullish and previous.is_long_body and current.is_bearish
        and current.open > previous.high
        and previous.open < current.close < midpoint
    )
    if bullish_engulfing:
        codes.extend((
            "BULLISH_ENGULFING_CONTEXT",
            "ENGULFING_WITHOUT_FOLLOW_THROUGH",
            "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        ))
    if bearish_engulfing:
        codes.extend((
            "BEARISH_ENGULFING_CONTEXT",
            "ENGULFING_WITHOUT_FOLLOW_THROUGH",
            "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        ))
    if piercing:
        codes.extend((
            "PIERCING_BULLISH_CONTEXT",
            "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
            "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        ))
    if dark_cloud:
        codes.extend((
            "DARK_CLOUD_BEARISH_CONTEXT",
            "REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH",
            "CANDLE_PATTERN_NEEDS_TREND_CONTEXT",
        ))
    metadata = {
        "previous_timestamp": previous.timestamp,
        "timestamp": current.timestamp,
        "trend_context_evaluated": False,
        "follow_through_evaluated": False,
    }
    return tuple(_evidence(code, **metadata) for code in dict.fromkeys(codes))


def analyze_nison_window_context(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> NisonWindowContext:
    morphologies = analyze_candle_window_morphology(candles)
    candle_contexts = tuple(
        NisonCandleContext(
            morphology.timestamp,
            morphology,
            evidence := _single_candle_evidence(morphology),
            _unique_codes(evidence),
        )
        for morphology in morphologies
    )
    count = len(morphologies)
    doji_count = sum(item.is_doji for item in morphologies)
    small_body_count = sum(item.is_small_body for item in morphologies)
    bullish_body_total = sum(item.real_body_size for item in morphologies if item.is_bullish)
    bearish_body_total = sum(item.real_body_size for item in morphologies if item.is_bearish)
    doji_ratio = doji_count / count if count else 0.0
    small_body_ratio = small_body_count / count if count else 0.0

    window_items: list[EngineTrendEvidence] = []
    for index in range(1, count):
        window_items.extend(_pair_evidence(morphologies[index - 1], morphologies[index]))
    window_items.extend(analyze_nison_pattern_catalog(morphologies))
    if doji_count >= 2 and doji_ratio >= 0.25:
        window_items.append(
            _engine_heuristic_evidence(
                "DOJI_CLUSTER_FLAT_CONTEXT", count=doji_count, ratio=doji_ratio
            )
        )
    if small_body_count >= 2 and small_body_ratio >= 0.35:
        window_items.extend((
            _engine_heuristic_evidence(
                "SMALL_BODY_CLUSTER", count=small_body_count, ratio=small_body_ratio
            ),
            _engine_heuristic_evidence(
                "LOW_DIRECTIONAL_PROGRESS",
                count=small_body_count,
                ratio=small_body_ratio,
            ),
        ))
    if bullish_body_total > 0.0 and bullish_body_total >= bearish_body_total * 1.5:
        window_items.append(
            _engine_heuristic_evidence(
                "BULLISH_BODY_DOMINANCE",
                bullish_total=bullish_body_total,
                bearish_total=bearish_body_total,
            )
        )
    elif bearish_body_total > 0.0 and bearish_body_total >= bullish_body_total * 1.5:
        window_items.append(
            _engine_heuristic_evidence(
                "BEARISH_BODY_DOMINANCE",
                bullish_total=bullish_body_total,
                bearish_total=bearish_body_total,
            )
        )

    window_evidence = tuple(window_items)
    candle_evidence = tuple(item for context in candle_contexts for item in context.evidence)
    all_evidence = candle_evidence + window_evidence
    summary: dict[str, float | int] = {
        "doji_count": doji_count,
        "doji_ratio": doji_ratio,
        "small_body_count": small_body_count,
        "small_body_ratio": small_body_ratio,
        "bullish_body_total": bullish_body_total,
        "bearish_body_total": bearish_body_total,
    }
    return NisonWindowContext(count, candle_contexts, window_evidence, all_evidence, _unique_codes(all_evidence), summary)
