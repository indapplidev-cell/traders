"""Conservative final market-state composition from book evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.market_reader.engine_trend.altunina_trend_context import AltuninaStructureDirection
from app.market_reader.engine_trend.book_evidence_matrix import (
    BookAgreementState,
    BookEvidenceMatrix,
    EvidenceConflictLevel,
    EvidenceCoverageLevel,
    analyze_book_evidence_matrix,
)
from app.market_reader.engine_trend.input_period import EngineTrendInputPeriod
from app.market_reader.engine_trend.ohlc_integrity import OHLCIntegrityResult, validate_ohlc_integrity
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
from app.market_reader.engine_trend.schwager_range_context import (
    BreakoutConfirmationStatus,
    BreakoutDirection,
    PolarityFlipStatus,
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

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value, "decision_source": self.decision_source.value,
            "candidate_scores": self.candidate_scores.to_dict(), "matrix_summary": dict(self.matrix_summary),
            "data_quality_status": self.data_quality_status, "warnings": list(self.warnings),
            "errors": list(self.errors), "reason_codes": list(self.reason_codes),
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
    """Score and conservatively select one market state."""
    balance, summary = matrix.directional_balance, matrix.confluence_conflict
    up, down, flat, unknown = balance.bullish_score, balance.bearish_score, 0.0, 0.0
    codes: list[str] = []
    bonuses = {
        BookAgreementState.ALIGNED_BULLISH: (0.20, 0.0, 0.0, 0.0),
        BookAgreementState.ALIGNED_BEARISH: (0.0, 0.20, 0.0, 0.0),
        BookAgreementState.ALIGNED_NEUTRAL: (0.0, 0.0, 0.20, 0.0),
        BookAgreementState.MIXED_WITH_CONFLICT: (0.0, 0.0, 0.0, 0.25),
        BookAgreementState.MIXED_LOW_CONFLICT: (0.0, 0.0, 0.0, 0.10),
    }
    delta = bonuses.get(summary.agreement_state, (0.0, 0.0, 0.0, 0.0))
    up, down, flat, unknown = up + delta[0], down + delta[1], flat + delta[2], unknown + delta[3]

    alt = matrix.altunina_context
    trend_weight = 0.20 * alt.trend_strength_score + 0.10 * alt.trend_consistency_score + 0.10 * alt.trend_progress_score
    if alt.structure_direction is AltuninaStructureDirection.BULLISH_STRUCTURE:
        up += trend_weight
    elif alt.structure_direction is AltuninaStructureDirection.BEARISH_STRUCTURE:
        down += trend_weight
    elif alt.structure_direction is AltuninaStructureDirection.SIDEWAYS_STRUCTURE:
        flat += 0.20
        codes.append("COMPOSER_SIDEWAYS_STRUCTURE_FLAT_CONTEXT")
    else:
        unknown += 0.10

    schwager = matrix.schwager_context
    trading_range, breakout, polarity = schwager.trading_range, schwager.breakout_context, schwager.polarity_flip_context
    if trading_range.is_detected:
        flat += 0.20 + min(0.20, trading_range.inside_close_ratio * 0.20)
        codes.append("COMPOSER_RANGE_FLAT_CONTEXT")
    if breakout.status is BreakoutConfirmationStatus.CONFIRMED:
        if breakout.direction is BreakoutDirection.UPWARD:
            up += 0.15
        elif breakout.direction is BreakoutDirection.DOWNWARD:
            down += 0.15
        codes.append("COMPOSER_BREAKOUT_WITH_CONFIRMATION_CONTEXT")
    if breakout.status is BreakoutConfirmationStatus.NO_FOLLOW_THROUGH:
        flat, unknown = flat + 0.15, unknown + 0.05
    if breakout.status is BreakoutConfirmationStatus.FALSE_BREAKOUT:
        flat, unknown = flat + 0.20, unknown + 0.05
        codes.append("COMPOSER_FALSE_BREAKOUT_FLAT_CONTEXT")
    if breakout.returned_to_range:
        flat += 0.15
    if polarity.held:
        if polarity.status is PolarityFlipStatus.RESISTANCE_TO_SUPPORT:
            up += 0.10
        elif polarity.status is PolarityFlipStatus.SUPPORT_TO_RESISTANCE:
            down += 0.10

    nison_codes = set(matrix.nison_context.reason_codes)
    if nison_codes & {"DOJI_CLUSTER_FLAT_CONTEXT", "SMALL_BODY_CLUSTER", "LOW_DIRECTIONAL_PROGRESS"}:
        flat += 0.10
    if "BULLISH_BODY_DOMINANCE" in nison_codes:
        up += 0.05
    if "BEARISH_BODY_DOMINANCE" in nison_codes:
        down += 0.05

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
    clear_range = trading_range.is_detected and flat >= max(up, down) and (breakout.returned_to_range or breakout.status is BreakoutConfirmationStatus.FALSE_BREAKOUT)
    if invalid:
        selected, confidence = EngineTrendRegime.UNKNOWN, 0.0
        codes.append("COMPOSER_OHLC_FAIL")
        fallback_reason = "COMPOSER_OHLC_FAIL"
    elif summary.coverage_level is EvidenceCoverageLevel.EMPTY:
        selected, confidence = EngineTrendRegime.UNKNOWN, 0.0
        codes.append("COMPOSER_LOW_COVERAGE_UNKNOWN")
        fallback_reason = "COMPOSER_LOW_COVERAGE_UNKNOWN"
    elif summary.coverage_level is EvidenceCoverageLevel.LOW:
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.25, unknown)
        codes.append("COMPOSER_LOW_COVERAGE_UNKNOWN")
        fallback_reason = "COMPOSER_LOW_COVERAGE_UNKNOWN"
    elif summary.conflict_level is EvidenceConflictLevel.HIGH and not clear_range:
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.35, unknown)
        codes.append("COMPOSER_HIGH_CONFLICT_UNKNOWN")
        fallback_reason = "COMPOSER_HIGH_CONFLICT_UNKNOWN"
    elif winning < MIN_REGIME_SCORE or (winning - ranked[1][1] < MIN_SCORE_MARGIN and not (selected is EngineTrendRegime.FLAT and trading_range.is_detected)):
        selected, confidence = EngineTrendRegime.UNKNOWN, min(0.30, max(unknown, winning))
        codes.append("COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN")
        fallback_reason = "COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN"
    else:
        confidence = winning * (0.50 + 0.50 * summary.coverage_score) + min(0.15, summary.confluence_score * 0.15) - min(0.35, summary.conflict_score * 0.35)
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
    alt, schwager, summary = matrix.altunina_context, matrix.schwager_context, matrix.confluence_conflict
    breakout = schwager.breakout_context
    return ConfidenceDecomposition(
        trend_score=0.20 * alt.trend_strength_score + 0.10 * alt.trend_consistency_score + 0.10 * alt.trend_progress_score,
        range_score=(0.20 + min(0.20, schwager.trading_range.inside_close_ratio * 0.20)) if schwager.trading_range.is_detected else 0.0,
        candlestick_score=0.10 if set(matrix.nison_context.reason_codes) & {"DOJI_CLUSTER_FLAT_CONTEXT", "SMALL_BODY_CLUSTER", "LOW_DIRECTIONAL_PROGRESS"} else 0.05,
        level_score=min(0.10, len(schwager.zones) * 0.02),
        breakout_score=0.15 if breakout.status is BreakoutConfirmationStatus.CONFIRMED else 0.0,
        false_breakout_penalty=-0.10 if breakout.status in (BreakoutConfirmationStatus.FALSE_BREAKOUT, BreakoutConfirmationStatus.NO_FOLLOW_THROUGH) else 0.0,
        confluence_score=min(0.15, summary.confluence_score * 0.15),
        conflict_penalty=-min(0.35, summary.conflict_score * 0.35),
        data_quality_penalty=-0.20 if integrity.warnings or integrity.errors else 0.0,
    )


def compose_regime_from_matrix(symbol: str, interval: str, candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle], matrix: BookEvidenceMatrix, ohlc_integrity: OHLCIntegrityResult | None = None) -> RegimeComposerOutput:
    """Build the final result from a precomputed matrix."""
    items = tuple(candles)
    integrity = ohlc_integrity or validate_ohlc_integrity(items)
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
    evidence = BookEvidence(matrix.nison_context.all_evidence, matrix.altunina_context.evidence, matrix.schwager_context.evidence, matrix_engine + composer_evidence)
    warnings, errors = integrity.warnings, tuple(dict.fromkeys(integrity.errors + input_errors))
    result = EngineTrendResult(symbol or "UNKNOWN_SYMBOL", interval or "UNKNOWN_INTERVAL", items[0].timestamp if items else None, items[-1].timestamp if items else None, len(items), scores.selected_regime, scores.confidence, evidence, _decomposition(matrix, integrity), warnings, errors, EngineTrendSafety())
    trace = RegimeDecisionTrace(status, source, scores, matrix.summary, integrity.status, warnings, errors, tuple(dict.fromkeys(composer_codes)))
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


def compose_engine_trend_result(symbol: str, interval: str, candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle]) -> RegimeComposerOutput:
    """Validate input, build the book matrix, and compose its market state."""
    try:
        items = tuple(candles)
        integrity = validate_ohlc_integrity(items)
    except (TypeError, ValueError, AttributeError) as exc:
        return _invalid_output(symbol, interval, (), OHLCIntegrityResult(False), f"INPUT_PERIOD_INVALID:{exc}")
    if not integrity.is_valid:
        return _invalid_output(symbol, interval, items, integrity)
    try:
        EngineTrendInputPeriod(symbol, interval, items)
    except (TypeError, ValueError) as exc:
        return _invalid_output(symbol, interval, items, integrity, f"INPUT_PERIOD_INVALID:{exc}")
    return compose_regime_from_matrix(symbol, interval, items, analyze_book_evidence_matrix(items), integrity)
