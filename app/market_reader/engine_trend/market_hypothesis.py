"""Contextual market hypotheses built from the three book methodologies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.market_reader.engine_trend.altunina_trend_context import (
    AltuninaStructureDirection,
    classify_structure_direction,
)
from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendEvidence,
)
from app.market_reader.engine_trend.schwager_range_context import (
    BreakoutConfirmationStatus,
    BreakoutDirection,
    FalseBreakoutConfirmationStatus,
    PolarityFlipStatus,
    ZoneType,
)
from app.market_reader.engine_trend.unified_market_context import UnifiedMarketContext
from app.market_reader.engine_trend.technical_indicator_context import IndicatorDirection


class PatternDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class PatternRole(str, Enum):
    REVERSAL = "REVERSAL"
    CONTINUATION = "CONTINUATION"


class ContextualEventStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    CONTEXT_REJECTED = "CONTEXT_REJECTED"


class FollowThroughStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class HypothesisType(str, Enum):
    UP_CONTINUATION = "UP_CONTINUATION"
    DOWN_CONTINUATION = "DOWN_CONTINUATION"
    BULLISH_REVERSAL = "BULLISH_REVERSAL"
    BEARISH_REVERSAL = "BEARISH_REVERSAL"
    CONFIRMED_RANGE = "CONFIRMED_RANGE"
    BULL_TRAP = "BULL_TRAP"
    BEAR_TRAP = "BEAR_TRAP"


class HypothesisDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    FLAT = "FLAT"


class HypothesisStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CONFLICTED = "CONFLICTED"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class ContextualPatternEvent:
    event_id: str
    pattern_code: str
    direction: PatternDirection
    role: PatternRole
    start_index: int
    end_index: int
    prior_structure: AltuninaStructureDirection
    zone_relation: str
    related_zone_mid: float | None
    follow_through: FollowThroughStatus
    status: ContextualEventStatus
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "pattern_code": self.pattern_code,
            "direction": self.direction.value,
            "role": self.role.value,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "prior_structure": self.prior_structure.value,
            "zone_relation": self.zone_relation,
            "related_zone_mid": self.related_zone_mid,
            "follow_through": self.follow_through.value,
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class MarketHypothesis:
    hypothesis_id: str
    hypothesis_type: HypothesisType
    direction: HypothesisDirection
    status: HypothesisStatus
    score: float
    trigger_index: int | None
    confirmation_index: int | None
    supporting_event_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type.value,
            "direction": self.direction.value,
            "status": self.status.value,
            "score": self.score,
            "trigger_index": self.trigger_index,
            "confirmation_index": self.confirmation_index,
            "supporting_event_ids": list(self.supporting_event_ids),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class MarketHypothesisResult:
    contextual_events: tuple[ContextualPatternEvent, ...]
    hypotheses: tuple[MarketHypothesis, ...]
    dominant_hypothesis: MarketHypothesis | None
    evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    summary: dict[str, object]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contextual_events": [item.to_dict() for item in self.contextual_events],
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "dominant_hypothesis": (
                self.dominant_hypothesis.to_dict()
                if self.dominant_hypothesis
                else None
            ),
            "evidence": [item.to_dict() for item in self.evidence],
            "reason_codes": list(self.reason_codes),
            "summary": dict(self.summary),
        }


BULLISH_REVERSAL_CODES = {
    "HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED",
    "INVERTED_HAMMER_LIKE_CONTEXT_REQUIRED",
    "BULLISH_ENGULFING_CONTEXT",
    "PIERCING_BULLISH_CONTEXT",
    "MORNING_STAR_LIKE_CONTEXT",
    "MORNING_DOJI_STAR_LIKE_CONTEXT",
    "BULLISH_HARAMI_CONTEXT",
    "TWEEZERS_BOTTOM_CONTEXT_REQUIRED",
    "BULLISH_COUNTERATTACK_CONTEXT",
    "THREE_RIVERS_CONTEXT_REQUIRED",
    "INVERTED_THREE_BUDDHA_BOTTOM_CONTEXT_REQUIRED",
    "FRY_PAN_BOTTOM_CONTEXT_REQUIRED",
    "TOWER_BOTTOM_CONTEXT_REQUIRED",
    "DRAGONFLY_DOJI_CONTEXT",
}

BEARISH_REVERSAL_CODES = {
    "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
    "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
    "BEARISH_ENGULFING_CONTEXT",
    "DARK_CLOUD_BEARISH_CONTEXT",
    "EVENING_STAR_LIKE_CONTEXT",
    "EVENING_DOJI_STAR_LIKE_CONTEXT",
    "BEARISH_HARAMI_CONTEXT",
    "TWEEZERS_TOP_CONTEXT_REQUIRED",
    "BEARISH_COUNTERATTACK_CONTEXT",
    "THREE_BLACK_CROWS_CONTEXT",
    "THREE_MOUNTAINS_CONTEXT_REQUIRED",
    "THREE_BUDDHA_TOP_CONTEXT_REQUIRED",
    "DUMPLING_TOP_CONTEXT_REQUIRED",
    "TOWER_TOP_CONTEXT_REQUIRED",
    "GRAVESTONE_DOJI_CONTEXT",
    "DOJI_TOP_CONTEXT_REQUIRED",
}

BULLISH_CONTINUATION_CODES = {
    "UPWARD_WINDOW_CONTEXT",
    "UPWARD_GAP_TASUKI_CONTEXT",
    "UPWARD_GAPPING_SIDE_BY_SIDE_CONTEXT",
    "RISING_THREE_METHODS_CONTEXT",
    "THREE_ADVANCING_WHITE_SOLDIERS_CONTEXT",
    "BULLISH_SEPARATING_LINES_CONTEXT",
    "HIGH_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
}

BEARISH_CONTINUATION_CODES = {
    "DOWNWARD_WINDOW_CONTEXT",
    "DOWNWARD_GAP_TASUKI_CONTEXT",
    "DOWNWARD_GAPPING_SIDE_BY_SIDE_CONTEXT",
    "FALLING_THREE_METHODS_CONTEXT",
    "BEARISH_SEPARATING_LINES_CONTEXT",
    "LOW_PRICE_GAPPING_PLAY_CONTEXT_REQUIRED",
}


def _pattern_semantics(code: str) -> tuple[PatternDirection, PatternRole] | None:
    if code in BULLISH_REVERSAL_CODES:
        return PatternDirection.BULLISH, PatternRole.REVERSAL
    if code in BEARISH_REVERSAL_CODES:
        return PatternDirection.BEARISH, PatternRole.REVERSAL
    if code in BULLISH_CONTINUATION_CODES:
        return PatternDirection.BULLISH, PatternRole.CONTINUATION
    if code in BEARISH_CONTINUATION_CODES:
        return PatternDirection.BEARISH, PatternRole.CONTINUATION
    return None


def _event_indexes(
    context: UnifiedMarketContext,
    evidence: EngineTrendEvidence,
) -> tuple[int, int] | None:
    timestamps: list[str] = []
    values = evidence.metadata.get("timestamps")
    if isinstance(values, list | tuple):
        timestamps.extend(str(item) for item in values)
    for key in ("previous_timestamp", "timestamp"):
        value = evidence.metadata.get(key)
        if value is not None:
            timestamps.append(str(value))
    indexes = sorted(
        {
            context.timestamp_to_index[value]
            for value in timestamps
            if value in context.timestamp_to_index
        }
    )
    return (indexes[0], indexes[-1]) if indexes else None


def _prior_structure(
    context: UnifiedMarketContext,
    start_index: int,
) -> AltuninaStructureDirection:
    prior_points = tuple(
        item for item in context.structural_swing_points if item.index < start_index
    )
    structural = classify_structure_direction(prior_points)
    if structural is not AltuninaStructureDirection.UNCLEAR_STRUCTURE:
        return structural
    start = max(0, start_index - 6)
    closes = [item.close for item in context.candles[start:start_index]]
    if len(closes) < 2:
        return structural
    scale = max(abs(closes[0]), abs(closes[-1]), 1.0)
    change = (closes[-1] - closes[0]) / scale
    if change >= 0.005:
        return AltuninaStructureDirection.BULLISH_STRUCTURE
    if change <= -0.005:
        return AltuninaStructureDirection.BEARISH_STRUCTURE
    return AltuninaStructureDirection.SIDEWAYS_STRUCTURE


def _zone_relation(
    context: UnifiedMarketContext,
    start_index: int,
    end_index: int,
) -> tuple[str, float | None]:
    event_candles = context.candles[start_index:end_index + 1]
    event_low = min(item.low for item in event_candles)
    event_high = max(item.high for item in event_candles)
    candidates: list[tuple[float, str, float]] = []
    for zone in context.schwager_context.zones:
        if zone.formed_at_index > start_index:
            continue
        tolerance = max(abs(zone.mid_price), 1.0) * 0.003
        if event_low <= zone.upper_price + tolerance and event_high >= zone.lower_price - tolerance:
            causal_zone_type = (
                zone.current_zone_type
                if zone.role_changed_at_index is not None
                and zone.role_changed_at_index <= start_index
                else zone.original_zone_type or zone.zone_type
            )
            relation = (
                "AT_SUPPORT"
                if causal_zone_type is ZoneType.SUPPORT
                else "AT_RESISTANCE"
            )
            event_mid = (event_low + event_high) / 2.0
            candidates.append((abs(event_mid - zone.mid_price), relation, zone.mid_price))
    if not candidates:
        return "NO_CAUSAL_ZONE", None
    _, relation, mid = min(candidates, key=lambda item: item[0])
    return relation, mid


def _follow_through(
    context: UnifiedMarketContext,
    direction: PatternDirection,
    start_index: int,
    end_index: int,
) -> tuple[FollowThroughStatus, int | None]:
    event = context.candles[start_index:end_index + 1]
    event_high = max(item.high for item in event)
    event_low = min(item.low for item in event)
    lookahead = context.analysis_window.confirmation_lookahead
    later = context.candles[
        end_index + 1:min(len(context.candles), end_index + 1 + lookahead)
    ]
    if not later:
        return FollowThroughStatus.NOT_AVAILABLE, None
    for offset, candle in enumerate(later, start=end_index + 1):
        if direction is PatternDirection.BULLISH:
            if candle.close < event_low:
                return FollowThroughStatus.INVALIDATED, offset
            if candle.close > event_high:
                return FollowThroughStatus.CONFIRMED, offset
        else:
            if candle.close > event_high:
                return FollowThroughStatus.INVALIDATED, offset
            if candle.close < event_low:
                return FollowThroughStatus.CONFIRMED, offset
    return FollowThroughStatus.PENDING, None


def _contextualize_patterns(
    context: UnifiedMarketContext,
) -> tuple[ContextualPatternEvent, ...]:
    events: list[ContextualPatternEvent] = []
    seen: set[tuple[str, int, int]] = set()
    for evidence in context.nison_context.all_evidence:
        semantics = _pattern_semantics(evidence.code)
        indexes = _event_indexes(context, evidence)
        if semantics is None or indexes is None:
            continue
        direction, role = semantics
        start_index, end_index = indexes
        if not context.analysis_window.contains_decision_event(end_index):
            continue
        key = (evidence.code, start_index, end_index)
        if key in seen:
            continue
        seen.add(key)
        prior = _prior_structure(context, start_index)
        zone_relation, zone_mid = _zone_relation(context, start_index, end_index)
        follow, _ = _follow_through(context, direction, start_index, end_index)
        expected_prior = (
            AltuninaStructureDirection.BEARISH_STRUCTURE
            if direction is PatternDirection.BULLISH and role is PatternRole.REVERSAL
            else AltuninaStructureDirection.BULLISH_STRUCTURE
            if direction is PatternDirection.BEARISH and role is PatternRole.REVERSAL
            else AltuninaStructureDirection.BULLISH_STRUCTURE
            if direction is PatternDirection.BULLISH
            else AltuninaStructureDirection.BEARISH_STRUCTURE
        )
        correct_zone = (
            zone_relation == "AT_SUPPORT"
            if direction is PatternDirection.BULLISH
            else zone_relation == "AT_RESISTANCE"
        )
        codes = [evidence.code, f"PATTERN_PRIOR_{prior.value}", zone_relation]
        if prior is not expected_prior:
            status = ContextualEventStatus.CONTEXT_REJECTED
            codes.append("PATTERN_TREND_CONTEXT_REJECTED")
        elif follow is FollowThroughStatus.INVALIDATED:
            status = ContextualEventStatus.INVALIDATED
            codes.append("PATTERN_FOLLOW_THROUGH_INVALIDATED")
        elif correct_zone and follow is FollowThroughStatus.CONFIRMED:
            status = ContextualEventStatus.CONFIRMED
            codes.extend(("PATTERN_LEVEL_CONTEXT_CONFIRMED", "PATTERN_FOLLOW_THROUGH_CONFIRMED"))
        elif correct_zone:
            status = ContextualEventStatus.AWAITING_CONFIRMATION
            codes.extend(("PATTERN_LEVEL_CONTEXT_CONFIRMED", "PATTERN_AWAITING_FOLLOW_THROUGH"))
        else:
            status = ContextualEventStatus.CANDIDATE
            codes.append("PATTERN_LEVEL_CONTEXT_MISSING")
        events.append(
            ContextualPatternEvent(
                event_id=f"pattern:{start_index}:{end_index}:{evidence.code}",
                pattern_code=evidence.code,
                direction=direction,
                role=role,
                start_index=start_index,
                end_index=end_index,
                prior_structure=prior,
                zone_relation=zone_relation,
                related_zone_mid=zone_mid,
                follow_through=follow,
                status=status,
                reason_codes=tuple(codes),
            )
        )
    return tuple(events)


def _continuation_hypothesis(
    context: UnifiedMarketContext,
    direction: HypothesisDirection,
    events: tuple[ContextualPatternEvent, ...],
) -> MarketHypothesis | None:
    alt = context.altunina_context
    schwager = context.schwager_context
    upward = direction is HypothesisDirection.BULLISH
    structure_matches = alt.structure_direction is (
        AltuninaStructureDirection.BULLISH_STRUCTURE
        if upward
        else AltuninaStructureDirection.BEARISH_STRUCTURE
    )
    breakout_matches = (
        schwager.breakout_context.status is BreakoutConfirmationStatus.CONFIRMED
        and schwager.breakout_context.direction
        is (BreakoutDirection.UPWARD if upward else BreakoutDirection.DOWNWARD)
        and context.analysis_window.contains_decision_event(
            schwager.breakout_context.breakout_index
        )
    )
    relevant_events = tuple(
        item
        for item in events
        if item.role is PatternRole.CONTINUATION
        and item.direction
        is (PatternDirection.BULLISH if upward else PatternDirection.BEARISH)
        and item.status is ContextualEventStatus.CONFIRMED
    )
    indicator_matches = context.indicator_context.confirms(
        IndicatorDirection.BULLISH if upward else IndicatorDirection.BEARISH
    )
    decision_start = context.analysis_window.decision_start_index
    decision_start_close = context.candles[decision_start].close
    decision_change = (
        (context.candles[-1].close - decision_start_close) / decision_start_close
        if decision_start_close > 0
        else 0.0
    )
    atr_ratio = context.indicator_context.atr_ratio or 0.0
    progress_threshold = max(0.01, atr_ratio * 2.0)
    progress_matches = (
        decision_change >= progress_threshold
        if upward
        else decision_change <= -progress_threshold
    )
    if (
        not structure_matches
        and not breakout_matches
        and not relevant_events
        and not progress_matches
    ):
        return None
    score = 0.0
    codes: list[str] = []
    if structure_matches:
        score += 0.25 + 0.20 * alt.trend_strength_score
        score += 0.10 * alt.trend_consistency_score + 0.10 * alt.trend_progress_score
        codes.append("HYPOTHESIS_STRUCTURE_ALIGNED")
    if breakout_matches:
        score += 0.20
        codes.append("HYPOTHESIS_BREAKOUT_CONFIRMED")
    polarity = schwager.polarity_flip_context.status
    polarity_matches = polarity is (
        PolarityFlipStatus.RESISTANCE_TO_SUPPORT
        if upward
        else PolarityFlipStatus.SUPPORT_TO_RESISTANCE
    )
    if polarity_matches:
        score += 0.15
        codes.append("HYPOTHESIS_POLARITY_FLIP_CONFIRMED")
    if relevant_events:
        score += 0.10
        codes.append("HYPOTHESIS_CANDLE_CONTINUATION_CONFIRMED")
    if indicator_matches:
        score += 0.10
        codes.append("HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED")
    if progress_matches:
        score += 0.20
        codes.append("HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED")
    breakout_volume = context.volume_context.breakout_volume_ratio
    if breakout_matches and breakout_volume is not None and breakout_volume >= 1.20:
        score += 0.05
        codes.append("HYPOTHESIS_BREAKOUT_VOLUME_CONFIRMED")
    invalid = alt.impulse_correction.structural_pivot_breached
    unresolved_range_attempt = (
        schwager.trading_range.is_detected
        and schwager.breakout_context.status is BreakoutConfirmationStatus.ATTEMPT
        and not structure_matches
        and not relevant_events
    )
    method_count = sum(
        (
            structure_matches,
            breakout_matches,
            bool(relevant_events),
            indicator_matches,
            progress_matches,
        )
    )
    cross_method_confirmation = method_count >= 2
    status = (
        HypothesisStatus.INVALIDATED
        if invalid
        else HypothesisStatus.PENDING
        if unresolved_range_attempt
        else HypothesisStatus.CONFIRMED
        if cross_method_confirmation
        else HypothesisStatus.PENDING
    )
    if invalid:
        codes.append("HYPOTHESIS_STRUCTURAL_PIVOT_BREACHED")
    elif unresolved_range_attempt:
        codes.append("HYPOTHESIS_RANGE_BREAKOUT_ATTEMPT_PENDING")
    elif not cross_method_confirmation:
        codes.append("HYPOTHESIS_CROSS_METHOD_CONFIRMATION_PENDING")
    htype = HypothesisType.UP_CONTINUATION if upward else HypothesisType.DOWN_CONTINUATION
    return MarketHypothesis(
        hypothesis_id=f"hypothesis:{htype.value.lower()}",
        hypothesis_type=htype,
        direction=direction,
        status=status,
        score=max(0.0, min(1.0, score)),
        trigger_index=(
            schwager.breakout_context.breakout_index
            if breakout_matches
            else relevant_events[-1].end_index
            if relevant_events
            else context.analysis_window.decision_start_index
        ),
        confirmation_index=schwager.polarity_flip_context.test_index,
        supporting_event_ids=tuple(item.event_id for item in relevant_events),
        reason_codes=tuple(codes),
    )


def _reversal_hypothesis(
    context: UnifiedMarketContext,
    direction: HypothesisDirection,
    events: tuple[ContextualPatternEvent, ...],
) -> MarketHypothesis | None:
    upward = direction is HypothesisDirection.BULLISH
    relevant = tuple(
        item
        for item in events
        if item.role is PatternRole.REVERSAL
        and item.direction
        is (PatternDirection.BULLISH if upward else PatternDirection.BEARISH)
        and item.status
        in {
            ContextualEventStatus.CONFIRMED,
            ContextualEventStatus.AWAITING_CONFIRMATION,
        }
    )
    if not relevant:
        return None
    confirmed = tuple(item for item in relevant if item.status is ContextualEventStatus.CONFIRMED)
    selected = confirmed[-1] if confirmed else relevant[-1]
    indicator_direction = (
        IndicatorDirection.BULLISH
        if upward
        else IndicatorDirection.BEARISH
    )
    opposite_indicator = (
        context.indicator_context.direction
        is (
            IndicatorDirection.BEARISH
            if upward
            else IndicatorDirection.BULLISH
        )
    )
    status = (
        HypothesisStatus.PENDING
        if opposite_indicator
        else HypothesisStatus.CONFIRMED
        if confirmed
        else HypothesisStatus.PENDING
    )
    score = 0.65 if confirmed and not opposite_indicator else 0.40 if confirmed else 0.35
    htype = HypothesisType.BULLISH_REVERSAL if upward else HypothesisType.BEARISH_REVERSAL
    codes = ["HYPOTHESIS_PATTERN_TREND_LEVEL_ALIGNED"]
    codes.append(
        "HYPOTHESIS_PATTERN_FOLLOW_THROUGH_CONFIRMED"
        if confirmed
        else "HYPOTHESIS_PATTERN_FOLLOW_THROUGH_PENDING"
    )
    if opposite_indicator:
        codes.append("HYPOTHESIS_INDICATOR_CONFLICT_REQUIRES_MORE_CONFIRMATION")
    elif context.indicator_context.direction is indicator_direction:
        codes.append("HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED")
    return MarketHypothesis(
        hypothesis_id=f"hypothesis:{htype.value.lower()}:{selected.end_index}",
        hypothesis_type=htype,
        direction=direction,
        status=status,
        score=score,
        trigger_index=selected.end_index,
        confirmation_index=None,
        supporting_event_ids=tuple(item.event_id for item in relevant),
        reason_codes=tuple(codes),
    )


def _range_hypothesis(context: UnifiedMarketContext) -> MarketHypothesis | None:
    schwager = context.schwager_context
    trading_range = schwager.trading_range
    if not trading_range.is_detected:
        return None
    breakout = schwager.breakout_context
    nison_codes = set(context.nison_context.reason_codes)
    secondary_flat_context = (
        context.altunina_context.structure_direction
        is AltuninaStructureDirection.SIDEWAYS_STRUCTURE
        or bool(
            nison_codes
            & {
                "DOJI_CLUSTER_FLAT_CONTEXT",
                "SMALL_BODY_CLUSTER",
                "LOW_DIRECTIONAL_PROGRESS",
            }
        )
        or context.indicator_context.direction is IndicatorDirection.NEUTRAL
    )
    if breakout.status is BreakoutConfirmationStatus.CONFIRMED:
        status = HypothesisStatus.CONFLICTED
    elif breakout.status is BreakoutConfirmationStatus.ATTEMPT or not secondary_flat_context:
        status = HypothesisStatus.PENDING
    else:
        status = HypothesisStatus.CONFIRMED
    score = 0.40 + min(0.25, trading_range.inside_close_ratio * 0.25)
    if breakout.returned_to_range:
        score += 0.15
    return MarketHypothesis(
        hypothesis_id="hypothesis:confirmed_range",
        hypothesis_type=HypothesisType.CONFIRMED_RANGE,
        direction=HypothesisDirection.FLAT,
        status=status,
        score=min(1.0, score),
        trigger_index=trading_range.formed_at_index,
        confirmation_index=breakout.return_index,
        supporting_event_ids=(),
        reason_codes=(
            "HYPOTHESIS_RANGE_STRUCTURE_CONFIRMED",
            "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_CONFIRMED"
            if secondary_flat_context
            else "HYPOTHESIS_SECONDARY_FLAT_CONTEXT_PENDING",
            "HYPOTHESIS_RANGE_BREAKOUT_RETURNED"
            if breakout.returned_to_range
            else "HYPOTHESIS_RANGE_BOUNDARIES_HELD",
        ),
    )


def _trap_hypothesis(context: UnifiedMarketContext) -> MarketHypothesis | None:
    breakout = context.schwager_context.breakout_context
    if (
        not breakout.returned_to_range
        or not context.analysis_window.contains_decision_event(breakout.breakout_index)
        or not context.analysis_window.contains_decision_event(breakout.return_index)
    ):
        return None
    confirmed_states = {
        FalseBreakoutConfirmationStatus.INITIAL_PRICE_CONFIRMATION,
        FalseBreakoutConfirmationStatus.STRONG_PRICE_CONFIRMATION,
        FalseBreakoutConfirmationStatus.TIME_CONFIRMATION,
    }
    if breakout.false_breakout_confirmation is FalseBreakoutConfirmationStatus.INVALIDATED:
        status = HypothesisStatus.INVALIDATED
    elif breakout.false_breakout_confirmation in confirmed_states:
        status = HypothesisStatus.CONFIRMED
    else:
        status = HypothesisStatus.PENDING
    upward_break = breakout.direction is BreakoutDirection.UPWARD
    htype = HypothesisType.BULL_TRAP if upward_break else HypothesisType.BEAR_TRAP
    direction = HypothesisDirection.BEARISH if upward_break else HypothesisDirection.BULLISH
    score = 0.70 if status is HypothesisStatus.CONFIRMED else 0.35
    return MarketHypothesis(
        hypothesis_id=f"hypothesis:{htype.value.lower()}",
        hypothesis_type=htype,
        direction=direction,
        status=status,
        score=score,
        trigger_index=breakout.breakout_index,
        confirmation_index=breakout.return_index,
        supporting_event_ids=(),
        reason_codes=(
            "HYPOTHESIS_FALSE_BREAKOUT_RETURNED_TO_RANGE",
            f"HYPOTHESIS_{breakout.false_breakout_confirmation.value}",
        ),
    )


def analyze_market_hypotheses(
    context: UnifiedMarketContext,
) -> MarketHypothesisResult:
    """Build event-linked hypotheses instead of treating books as independent votes."""

    events = _contextualize_patterns(context)
    hypotheses = tuple(
        item
        for item in (
            _continuation_hypothesis(context, HypothesisDirection.BULLISH, events),
            _continuation_hypothesis(context, HypothesisDirection.BEARISH, events),
            _reversal_hypothesis(context, HypothesisDirection.BULLISH, events),
            _reversal_hypothesis(context, HypothesisDirection.BEARISH, events),
            _range_hypothesis(context),
            _trap_hypothesis(context),
        )
        if item is not None
    )
    confirmed = sorted(
        (item for item in hypotheses if item.status is HypothesisStatus.CONFIRMED),
        key=lambda item: item.score,
        reverse=True,
    )
    dominant: MarketHypothesis | None = confirmed[0] if confirmed else None
    if len(confirmed) >= 2 and confirmed[0].direction is not confirmed[1].direction:
        if confirmed[0].score - confirmed[1].score < 0.10:
            dominant = None

    evidence: list[EngineTrendEvidence] = []
    for item in hypotheses:
        contribution = 0.0
        if item.status is HypothesisStatus.CONFIRMED:
            if item.direction is HypothesisDirection.BULLISH:
                contribution = item.score
            elif item.direction is HypothesisDirection.BEARISH:
                contribution = -item.score
        evidence.append(
            EngineTrendEvidence(
                BookSource.ENGINE_TREND,
                f"MARKET_HYPOTHESIS_{item.hypothesis_type.value}_{item.status.value}",
                "Context-linked market hypothesis",
                contribution,
                {
                    "hypothesis_id": item.hypothesis_id,
                    "direction": item.direction.value,
                    "score": item.score,
                    "trigger_index": item.trigger_index,
                },
            )
        )
    codes = tuple(dict.fromkeys(item.code for item in evidence))
    summary = {
        "event_count": len(events),
        "confirmed_event_count": sum(
            item.status is ContextualEventStatus.CONFIRMED for item in events
        ),
        "hypothesis_count": len(hypotheses),
        "confirmed_hypothesis_count": len(confirmed),
        "dominant_hypothesis": dominant.hypothesis_type.value if dominant else None,
        "dominant_direction": dominant.direction.value if dominant else None,
    }
    return MarketHypothesisResult(events, hypotheses, dominant, tuple(evidence), codes, summary)
