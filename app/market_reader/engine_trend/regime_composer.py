"""Conservative final market-state composition from book evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.market_reader.engine_trend.book_evidence_matrix import (
    BookAgreementState,
    BookEvidenceMatrix,
    EvidenceConflictLevel,
    EvidenceCoverageLevel,
    analyze_book_evidence_matrix,
)
from app.market_reader.engine_trend.input_period import EngineTrendInputPeriod
from app.market_reader.engine_trend.market_hypothesis import (
    ContextualEventStatus,
    HypothesisDirection,
    HypothesisStatus,
    HypothesisType,
)
from app.market_reader.engine_trend.ohlc_integrity import OHLCIntegrityResult, validate_ohlc_integrity
from app.market_reader.engine_trend.analysis_contract import (
    AnalysisReadiness,
    AnalysisWindowConfig,
)
from app.market_reader.engine_trend.schemas import (
    BookEvidence,
    BookSource,
    ConfidenceDecomposition,
    EngineTrendCandle,
    EngineTrendEvidence,
    EngineTrendRegime,
    EngineTrendResult,
    EngineTrendSafety,
)


MIN_REGIME_SCORE = 0.30
MIN_SCORE_MARGIN = 0.08


class RegimeDecisionSource(str, Enum):
    DATA_QUALITY = "DATA_QUALITY"
    BOOK_MATRIX = "BOOK_MATRIX"
    CONFLUENCE = "CONFLUENCE"
    CONFLICT = "CONFLICT"
    RANGE_CONTEXT = "RANGE_CONTEXT"
    DIRECTIONAL_CONTEXT = "DIRECTIONAL_CONTEXT"
    COMPOSER_SAFETY = "COMPOSER_SAFETY"


class RegimeConfidenceLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RegimeComposerStatus(str, Enum):
    COMPOSED = "COMPOSED"
    FALLBACK_UNKNOWN = "FALLBACK_UNKNOWN"
    INPUT_INVALID = "INPUT_INVALID"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HIGH_CONFLICT = "HIGH_CONFLICT"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _level(confidence: float) -> RegimeConfidenceLevel:
    if confidence <= 0.0:
        return RegimeConfidenceLevel.NONE
    if confidence < 0.40:
        return RegimeConfidenceLevel.LOW
    if confidence < 0.70:
        return RegimeConfidenceLevel.MEDIUM
    return RegimeConfidenceLevel.HIGH


@dataclass(frozen=True)
class RegimeCandidateScores:
    up_score: float
    down_score: float
    flat_score: float
    unknown_score: float
    selected_regime: EngineTrendRegime
    confidence: float
    confidence_level: RegimeConfidenceLevel
    reason_codes: tuple[str, ...]
    raw_scores: tuple[float, float, float, float] | None = None
    ranking_before_clamp: tuple[tuple[str, float], ...] = ()
    ranking_after_clamp: tuple[tuple[str, float], ...] = ()
    selected_regime_before_fallback: str | None = None
    fallback_triggered: bool = False
    fallback_reason: str | None = None
    confidence_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if any(not 0.0 <= value <= 1.0 for value in (self.up_score, self.down_score, self.flat_score, self.unknown_score, self.confidence)):
            raise ValueError("scores and confidence must be within [0.0, 1.0]")

    def to_dict(self) -> dict[str, object]:
        value = {
            "up_score": self.up_score, "down_score": self.down_score,
            "flat_score": self.flat_score, "unknown_score": self.unknown_score,
            "selected_regime": self.selected_regime.value, "confidence": self.confidence,
            "confidence_level": self.confidence_level.value, "reason_codes": list(self.reason_codes),
        }
        if self.raw_scores is not None:
            value["composer_trace"] = {
                "raw_scores": dict(zip(("UP", "DOWN", "FLAT", "UNKNOWN"), self.raw_scores)),
                "clamped_scores": {"UP": self.up_score, "DOWN": self.down_score, "FLAT": self.flat_score, "UNKNOWN": self.unknown_score},
                "ranking_before_clamp": [{"regime": regime, "score": score} for regime, score in self.ranking_before_clamp],
                "ranking_after_clamp": [{"regime": regime, "score": score} for regime, score in self.ranking_after_clamp],
                "selected_regime_before_fallback": self.selected_regime_before_fallback,
                "selected_regime_after_fallback": self.selected_regime.value,
                "fallback_triggered": self.fallback_triggered,
                "fallback_reason": self.fallback_reason,
                "confidence_path": list(self.confidence_path),
                "confidence_final": self.confidence,
            }
        return value


@dataclass(frozen=True)
class RegimeDecisionTrace:
    status: RegimeComposerStatus
    decision_source: RegimeDecisionSource
    candidate_scores: RegimeCandidateScores
    matrix_summary: dict[str, object]
    data_quality_status: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    reason_codes: tuple[str, ...]
    selected_hypothesis: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value, "decision_source": self.decision_source.value,
            "candidate_scores": self.candidate_scores.to_dict(), "matrix_summary": dict(self.matrix_summary),
            "data_quality_status": self.data_quality_status, "warnings": list(self.warnings),
            "errors": list(self.errors), "reason_codes": list(self.reason_codes),
            "selected_hypothesis": self.selected_hypothesis,
        }


@dataclass(frozen=True)
class RegimeComposerOutput:
    input_period: EngineTrendInputPeriod | None
    ohlc_integrity: OHLCIntegrityResult
    matrix: BookEvidenceMatrix | None
    decision_trace: RegimeDecisionTrace
    result: EngineTrendResult

    def to_dict(self) -> dict[str, object]:
        return {
            "input_period": self.input_period.to_dict() if self.input_period else None,
            "ohlc_integrity": self.ohlc_integrity.to_dict(),
            "matrix": self.matrix.to_dict() if self.matrix else None,
            "decision_trace": self.decision_trace.to_dict(), "result": self.result.to_dict(),
        }


def score_regime_candidates(matrix: BookEvidenceMatrix, ohlc_integrity: OHLCIntegrityResult | None = None) -> RegimeCandidateScores:
    """Select a regime from context-linked, confirmed market hypotheses."""
    summary = matrix.confluence_conflict
    hypothesis_result = matrix.hypothesis_result
    confirmed = tuple(
        item
        for item in hypothesis_result.hypotheses
        if item.status is HypothesisStatus.CONFIRMED
    )
    confirmed_directions = {item.direction for item in confirmed}
    unresolved_hypothesis_conflict = (
        len(confirmed_directions) >= 2
        and hypothesis_result.dominant_hypothesis is None
    )

    def directional_score(direction: HypothesisDirection) -> float:
        values = sorted(
            (item.score for item in confirmed if item.direction is direction),
            reverse=True,
        )
        if not values:
            return 0.0
        # The strongest causal hypothesis drives the regime. Additional
        # hypotheses provide bounded confluence instead of independent votes.
        return values[0] + min(0.15, sum(values[1:]) * 0.20)

    up = directional_score(HypothesisDirection.BULLISH)
    down = directional_score(HypothesisDirection.BEARISH)
    flat = directional_score(HypothesisDirection.FLAT)
    pending_count = sum(
        item.status is HypothesisStatus.PENDING
        for item in hypothesis_result.hypotheses
    )
    unknown = min(0.30, pending_count * 0.10)
    codes: list[str] = []
    # Compatibility path for callers that explicitly replace legacy matrix
    # aggregates or contexts. The normal engine pipeline never enters it;
    # production composition is hypothesis-driven.
    legacy_overridden = (
        matrix.altunina_context != matrix.unified_context.altunina_context
        or matrix.directional_balance.bullish_score
        != matrix.summary.get("legacy_bullish_score")
        or matrix.directional_balance.bearish_score
        != matrix.summary.get("legacy_bearish_score")
    )
    if legacy_overridden:
        up = matrix.directional_balance.bullish_score
        down = matrix.directional_balance.bearish_score
        flat = 0.0
        unknown = 0.0
        if matrix.confluence_conflict.agreement_state is BookAgreementState.ALIGNED_BULLISH:
            up += 0.20
        elif matrix.confluence_conflict.agreement_state is BookAgreementState.ALIGNED_BEARISH:
            down += 0.20
        elif matrix.confluence_conflict.agreement_state is BookAgreementState.ALIGNED_NEUTRAL:
            flat += 0.20
        elif matrix.confluence_conflict.agreement_state is BookAgreementState.MIXED_WITH_CONFLICT:
            unknown += 0.25
        elif matrix.confluence_conflict.agreement_state is BookAgreementState.MIXED_LOW_CONFLICT:
            unknown += 0.10
        if (
            matrix.altunina_context.structure_direction
            is matrix.altunina_context.structure_direction.SIDEWAYS_STRUCTURE
        ):
            flat += 0.20
        codes.append("COMPOSER_LEGACY_PRECOMPUTED_MATRIX_COMPATIBILITY")
    if confirmed:
        codes.append("COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY")
    else:
        unknown = max(unknown, 0.25)
        codes.append("COMPOSER_NO_CONFIRMED_HYPOTHESIS")
    dominant = hypothesis_result.dominant_hypothesis
    if dominant is not None:
        codes.append(f"COMPOSER_DOMINANT_{dominant.hypothesis_type.value}")
    if any(item.hypothesis_type is HypothesisType.BULL_TRAP for item in confirmed):
        codes.append("COMPOSER_CONFIRMED_BULL_TRAP")
    if any(item.hypothesis_type is HypothesisType.BEAR_TRAP for item in confirmed):
        codes.append("COMPOSER_CONFIRMED_BEAR_TRAP")

    raw_scores = (up, down, flat, unknown)
    raw_ranked = sorted(((EngineTrendRegime.UP, up), (EngineTrendRegime.DOWN, down), (EngineTrendRegime.FLAT, flat), (EngineTrendRegime.UNKNOWN, unknown)), key=lambda item: item[1], reverse=True)
    up, down, flat, unknown = map(_clamp, raw_scores)
    invalid = ohlc_integrity is not None and not ohlc_integrity.is_valid
    candidates = ((EngineTrendRegime.UP, up), (EngineTrendRegime.DOWN, down), (EngineTrendRegime.FLAT, flat))
    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
    selected, winning = ranked[0]
    selected_before_fallback = selected
    fallback_reason: str | None = None
    confidence_path: list[str] = [f"CLAMPED_WINNER:{selected.value}:{winning}"]
    clear_range = any(
        item.hypothesis_type is HypothesisType.CONFIRMED_RANGE
        and item.status is HypothesisStatus.CONFIRMED
        for item in hypothesis_result.hypotheses
    )
    if invalid:
        selected, confidence = EngineTrendRegime.UNKNOWN, 0.0
        codes.append("COMPOSER_OHLC_FAIL")
        fallback_reason = "COMPOSER_OHLC_FAIL"
    elif (
        ohlc_integrity is not None
        and ohlc_integrity.readiness is AnalysisReadiness.PARTIAL
    ):
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.25, unknown)
        codes.append("COMPOSER_PARTIAL_ANALYSIS_UNKNOWN")
        fallback_reason = "COMPOSER_PARTIAL_ANALYSIS_UNKNOWN"
    elif summary.coverage_level is EvidenceCoverageLevel.EMPTY:
        selected, confidence = EngineTrendRegime.UNKNOWN, 0.0
        codes.append("COMPOSER_LOW_COVERAGE_UNKNOWN")
        fallback_reason = "COMPOSER_LOW_COVERAGE_UNKNOWN"
    elif summary.coverage_level is EvidenceCoverageLevel.LOW:
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.25, unknown)
        codes.append("COMPOSER_LOW_COVERAGE_UNKNOWN")
        fallback_reason = "COMPOSER_LOW_COVERAGE_UNKNOWN"
    elif unresolved_hypothesis_conflict:
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.35, max(unknown, winning))
        codes.append("COMPOSER_UNRESOLVED_CONFIRMED_HYPOTHESIS_CONFLICT")
        fallback_reason = "COMPOSER_UNRESOLVED_CONFIRMED_HYPOTHESIS_CONFLICT"
    elif summary.conflict_level is EvidenceConflictLevel.HIGH and not clear_range:
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.35, unknown)
        codes.append("COMPOSER_HIGH_CONFLICT_UNKNOWN")
        fallback_reason = "COMPOSER_HIGH_CONFLICT_UNKNOWN"
    elif winning < MIN_REGIME_SCORE or (winning - ranked[1][1] < MIN_SCORE_MARGIN and not (selected is EngineTrendRegime.FLAT and clear_range)):
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.30, max(unknown, winning))
        codes.append("COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN")
        fallback_reason = "COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN"
    else:
        confidence = winning * (0.60 + 0.40 * summary.coverage_score) + min(0.10, summary.confluence_score * 0.10) - min(0.25, summary.conflict_score * 0.25)
        if ohlc_integrity and ohlc_integrity.warnings:
            confidence -= 0.20
        confidence = _clamp(confidence)
        confidence_path.append(f"WEIGHTED_CONFIDENCE:{confidence}")
        if summary.conflict_level is EvidenceConflictLevel.HIGH:
            confidence = min(confidence, 0.45 if selected is EngineTrendRegime.FLAT else 0.35)
        elif summary.conflict_level is EvidenceConflictLevel.MEDIUM:
            confidence = min(confidence, 0.60)
    if selected is EngineTrendRegime.UNKNOWN:
        confidence = min(confidence, 0.35)
        confidence_path.append(f"UNKNOWN_CAP:{confidence}")
    codes.append(f"COMPOSER_{selected.value}_REGIME_SELECTED")
    final_confidence = _clamp(confidence)
    confidence_path.append(f"FINAL:{final_confidence}")
    return RegimeCandidateScores(
        up, down, flat, unknown, selected, final_confidence, _level(final_confidence), tuple(dict.fromkeys(codes)),
        raw_scores,
        tuple((regime.value, score) for regime, score in raw_ranked),
        tuple((regime.value, score) for regime, score in sorted(((EngineTrendRegime.UP, up), (EngineTrendRegime.DOWN, down), (EngineTrendRegime.FLAT, flat), (EngineTrendRegime.UNKNOWN, unknown)), key=lambda item: item[1], reverse=True)),
        selected_before_fallback.value,
        selected is EngineTrendRegime.UNKNOWN and selected_before_fallback is not EngineTrendRegime.UNKNOWN,
        fallback_reason,
        tuple(confidence_path),
    )


def _composer_status(scores: RegimeCandidateScores, matrix: BookEvidenceMatrix, integrity: OHLCIntegrityResult) -> tuple[RegimeComposerStatus, RegimeDecisionSource]:
    if not integrity.is_valid:
        return RegimeComposerStatus.INPUT_INVALID, RegimeDecisionSource.DATA_QUALITY
    if matrix.confluence_conflict.coverage_level in (EvidenceCoverageLevel.EMPTY, EvidenceCoverageLevel.LOW):
        return RegimeComposerStatus.INSUFFICIENT_EVIDENCE, RegimeDecisionSource.COMPOSER_SAFETY
    if matrix.confluence_conflict.conflict_level is EvidenceConflictLevel.HIGH and scores.selected_regime is EngineTrendRegime.UNKNOWN:
        return RegimeComposerStatus.HIGH_CONFLICT, RegimeDecisionSource.CONFLICT
    if scores.selected_regime is EngineTrendRegime.UNKNOWN:
        return RegimeComposerStatus.FALLBACK_UNKNOWN, RegimeDecisionSource.COMPOSER_SAFETY
    if scores.selected_regime is EngineTrendRegime.FLAT:
        return RegimeComposerStatus.COMPOSED, RegimeDecisionSource.RANGE_CONTEXT
    return RegimeComposerStatus.COMPOSED, RegimeDecisionSource.DIRECTIONAL_CONTEXT


def _decomposition(matrix: BookEvidenceMatrix, integrity: OHLCIntegrityResult) -> ConfidenceDecomposition:
    hypotheses = matrix.hypothesis_result.hypotheses
    events = matrix.hypothesis_result.contextual_events
    summary = matrix.confluence_conflict
    confirmed = tuple(item for item in hypotheses if item.status is HypothesisStatus.CONFIRMED)
    trend_score = max(
        (
            item.score
            for item in confirmed
            if item.hypothesis_type
            in {HypothesisType.UP_CONTINUATION, HypothesisType.DOWN_CONTINUATION}
        ),
        default=0.0,
    )
    range_score = max(
        (
            item.score
            for item in confirmed
            if item.hypothesis_type is HypothesisType.CONFIRMED_RANGE
        ),
        default=0.0,
    )
    confirmed_pattern_count = sum(
        item.status is ContextualEventStatus.CONFIRMED for item in events
    )
    level_context_count = sum(
        item.zone_relation in {"AT_SUPPORT", "AT_RESISTANCE"} for item in events
    )
    breakout_confirmed = any(
        "HYPOTHESIS_BREAKOUT_CONFIRMED" in item.reason_codes for item in confirmed
    )
    return ConfidenceDecomposition(
        trend_score=min(0.40, trend_score * 0.40),
        range_score=min(0.40, range_score * 0.40),
        candlestick_score=min(0.15, confirmed_pattern_count * 0.05),
        level_score=min(0.10, level_context_count * 0.02),
        breakout_score=0.15 if breakout_confirmed else 0.0,
        false_breakout_penalty=0.0,
        confluence_score=min(0.15, summary.confluence_score * 0.15),
        conflict_penalty=-min(0.35, summary.conflict_score * 0.35),
        data_quality_penalty=-0.20 if integrity.warnings or integrity.errors else 0.0,
    )


def compose_regime_from_matrix(symbol: str, interval: str, candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle], matrix: BookEvidenceMatrix, ohlc_integrity: OHLCIntegrityResult | None = None, *, config: AnalysisWindowConfig | None = None, strict_timestamps: bool = False) -> RegimeComposerOutput:
    """Build the final result from a precomputed matrix."""
    items = tuple(candles)
    integrity = ohlc_integrity or validate_ohlc_integrity(
        items,
        interval=interval,
        config=config,
        strict_timestamps=strict_timestamps,
    )
    try:
        period = EngineTrendInputPeriod(symbol, interval, items)
        input_errors: tuple[str, ...] = ()
    except (TypeError, ValueError) as exc:
        period, input_errors = None, (f"INPUT_PERIOD_INVALID:{exc}",)
        integrity = OHLCIntegrityResult(False, integrity.warnings, tuple(dict.fromkeys(integrity.errors + input_errors)))
    scores = score_regime_candidates(matrix, integrity)
    status, source = _composer_status(scores, matrix, integrity)
    composer_codes = ["COMPOSER_MATRIX_READY", "COMPOSER_INPUT_VALID" if integrity.is_valid else "COMPOSER_INPUT_INVALID", *scores.reason_codes, "COMPOSER_NO_TRADING_ACTION"]
    if integrity.warnings:
        composer_codes.append("COMPOSER_OHLC_WARNING")
    composer_evidence = tuple(EngineTrendEvidence(BookSource.ENGINE_TREND, code, "Regime composer market-reading context") for code in dict.fromkeys(composer_codes))
    matrix_engine = tuple(item for item in matrix.all_evidence if item.source is BookSource.ENGINE_TREND)
    evidence = BookEvidence(
        tuple(
            item
            for item in matrix.nison_context.all_evidence
            if item.source is BookSource.NISON
        ),
        matrix.altunina_context.evidence,
        matrix.schwager_context.evidence,
        matrix_engine + composer_evidence,
    )
    warnings, errors = integrity.warnings, tuple(dict.fromkeys(integrity.errors + input_errors))
    result = EngineTrendResult(symbol or "UNKNOWN_SYMBOL", interval or "UNKNOWN_INTERVAL", items[0].timestamp if items else None, items[-1].timestamp if items else None, len(items), scores.selected_regime, scores.confidence, evidence, _decomposition(matrix, integrity), warnings, errors, EngineTrendSafety())
    selected_direction = {
        EngineTrendRegime.UP: HypothesisDirection.BULLISH,
        EngineTrendRegime.DOWN: HypothesisDirection.BEARISH,
        EngineTrendRegime.FLAT: HypothesisDirection.FLAT,
    }.get(scores.selected_regime)
    eligible = [
        item
        for item in matrix.hypothesis_result.hypotheses
        if item.status is HypothesisStatus.CONFIRMED
        and item.direction is selected_direction
    ]
    selected_hypothesis = (
        max(eligible, key=lambda item: item.score).to_dict() if eligible else None
    )
    trace = RegimeDecisionTrace(
        status,
        source,
        scores,
        matrix.summary,
        integrity.status,
        warnings,
        errors,
        tuple(dict.fromkeys(composer_codes)),
        selected_hypothesis,
    )
    return RegimeComposerOutput(period, integrity, matrix, trace, result)


def _invalid_output(symbol: str, interval: str, candles: tuple[EngineTrendCandle, ...], integrity: OHLCIntegrityResult, error: str | None = None) -> RegimeComposerOutput:
    errors = tuple(dict.fromkeys(integrity.errors + ((error,) if error else ())))
    integrity = OHLCIntegrityResult(False, integrity.warnings, errors)
    codes = ("COMPOSER_INPUT_INVALID", "COMPOSER_MATRIX_NOT_READY", "COMPOSER_OHLC_FAIL", "COMPOSER_UNKNOWN_REGIME_SELECTED", "COMPOSER_NO_TRADING_ACTION")
    scores = RegimeCandidateScores(0.0, 0.0, 0.0, 1.0, EngineTrendRegime.UNKNOWN, 0.0, RegimeConfidenceLevel.NONE, codes)
    evidence = BookEvidence(engine_trend=tuple(EngineTrendEvidence(BookSource.ENGINE_TREND, code, "Fail-closed composer context") for code in codes))
    result = EngineTrendResult(symbol or "UNKNOWN_SYMBOL", interval or "UNKNOWN_INTERVAL", candles[0].timestamp if candles else None, candles[-1].timestamp if candles else None, len(candles), EngineTrendRegime.UNKNOWN, 0.0, evidence, warnings=integrity.warnings, errors=errors)
    trace = RegimeDecisionTrace(RegimeComposerStatus.INPUT_INVALID, RegimeDecisionSource.DATA_QUALITY, scores, {}, integrity.status, integrity.warnings, errors, codes)
    return RegimeComposerOutput(None, integrity, None, trace, result)


def compose_engine_trend_result(symbol: str, interval: str, candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle], *, config: AnalysisWindowConfig | None = None, strict_timestamps: bool = False) -> RegimeComposerOutput:
    """Validate input, build the book matrix, and compose its market state."""
    try:
        items = tuple(candles)
        integrity = validate_ohlc_integrity(
            items,
            interval=interval,
            config=config,
            strict_timestamps=strict_timestamps,
        )
    except (TypeError, ValueError, AttributeError) as exc:
        return _invalid_output(symbol, interval, (), OHLCIntegrityResult(False), f"INPUT_PERIOD_INVALID:{exc}")
    if not integrity.is_valid:
        return _invalid_output(symbol, interval, items, integrity)
    try:
        EngineTrendInputPeriod(symbol, interval, items)
    except (TypeError, ValueError) as exc:
        return _invalid_output(symbol, interval, items, integrity, f"INPUT_PERIOD_INVALID:{exc}")
    return compose_regime_from_matrix(
        symbol,
        interval,
        items,
        analyze_book_evidence_matrix(items, config),
        integrity,
        config=config,
        strict_timestamps=strict_timestamps,
    )
