"""Aggregate complementary Nison, Altunina, and Schwager evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.market_reader.engine_trend.altunina_trend_context import (
    AltuninaTrendContext,
    analyze_altunina_trend_context,
)
from app.market_reader.engine_trend.nison_candlestick_context import (
    NisonWindowContext,
    analyze_nison_window_context,
)
from app.market_reader.engine_trend.schemas import (
    BookSource,
    EngineTrendCandle,
    EngineTrendEvidence,
)
from app.market_reader.engine_trend.schwager_range_context import (
    SchwagerRangeContext,
    analyze_schwager_range_context,
)


DIRECTION_MATERIALITY_THRESHOLD = 0.05
DIRECTION_BALANCE_TOLERANCE = 0.03
BOOK_SOURCES = (BookSource.NISON, BookSource.ALTUNINA, BookSource.SCHWAGER)


class EvidenceDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class EvidenceConflictLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceCoverageLevel(str, Enum):
    EMPTY = "EMPTY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BookAgreementState(str, Enum):
    NO_EVIDENCE = "NO_EVIDENCE"
    ALIGNED_BULLISH = "ALIGNED_BULLISH"
    ALIGNED_BEARISH = "ALIGNED_BEARISH"
    ALIGNED_NEUTRAL = "ALIGNED_NEUTRAL"
    MIXED_WITH_CONFLICT = "MIXED_WITH_CONFLICT"
    MIXED_LOW_CONFLICT = "MIXED_LOW_CONFLICT"


def _direction(positive: float, negative: float) -> EvidenceDirection:
    negative = abs(negative)
    positive_meaningful = positive >= DIRECTION_MATERIALITY_THRESHOLD
    negative_meaningful = negative >= DIRECTION_MATERIALITY_THRESHOLD
    if positive_meaningful and negative_meaningful and abs(positive - negative) <= DIRECTION_BALANCE_TOLERANCE:
        return EvidenceDirection.MIXED
    if positive_meaningful and positive - negative > DIRECTION_BALANCE_TOLERANCE:
        return EvidenceDirection.BULLISH
    if negative_meaningful and negative - positive > DIRECTION_BALANCE_TOLERANCE:
        return EvidenceDirection.BEARISH
    if positive_meaningful and negative_meaningful:
        return EvidenceDirection.MIXED
    return EvidenceDirection.NEUTRAL


@dataclass(frozen=True)
class BookEvidenceBucket:
    source: BookSource
    evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    positive_contribution: float
    negative_contribution: float
    neutral_count: int
    evidence_count: int
    direction: EvidenceDirection

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "reason_codes": list(self.reason_codes),
            "positive_contribution": self.positive_contribution,
            "negative_contribution": self.negative_contribution,
            "neutral_count": self.neutral_count,
            "evidence_count": self.evidence_count,
            "direction": self.direction.value,
        }


@dataclass(frozen=True)
class DirectionalEvidenceBalance:
    bullish_score: float
    bearish_score: float
    neutral_evidence_count: int
    total_evidence_count: int
    net_score: float
    dominant_direction: EvidenceDirection

    def to_dict(self) -> dict[str, object]:
        return {
            "bullish_score": self.bullish_score,
            "bearish_score": self.bearish_score,
            "neutral_evidence_count": self.neutral_evidence_count,
            "total_evidence_count": self.total_evidence_count,
            "net_score": self.net_score,
            "dominant_direction": self.dominant_direction.value,
        }


@dataclass(frozen=True)
class ConfluenceConflictSummary:
    agreement_state: BookAgreementState
    conflict_level: EvidenceConflictLevel
    coverage_level: EvidenceCoverageLevel
    aligned_sources: tuple[BookSource, ...]
    conflicting_sources: tuple[BookSource, ...]
    missing_sources: tuple[BookSource, ...]
    confluence_score: float
    conflict_score: float
    coverage_score: float
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "agreement_state": self.agreement_state.value,
            "conflict_level": self.conflict_level.value,
            "coverage_level": self.coverage_level.value,
            "aligned_sources": [item.value for item in self.aligned_sources],
            "conflicting_sources": [item.value for item in self.conflicting_sources],
            "missing_sources": [item.value for item in self.missing_sources],
            "confluence_score": self.confluence_score,
            "conflict_score": self.conflict_score,
            "coverage_score": self.coverage_score,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class BookEvidenceMatrix:
    candle_count: int
    nison_context: NisonWindowContext
    altunina_context: AltuninaTrendContext
    schwager_context: SchwagerRangeContext
    buckets: tuple[BookEvidenceBucket, ...]
    directional_balance: DirectionalEvidenceBalance
    confluence_conflict: ConfluenceConflictSummary
    all_evidence: tuple[EngineTrendEvidence, ...]
    reason_codes: tuple[str, ...]
    summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "candle_count": self.candle_count,
            "buckets": [item.to_dict() for item in self.buckets],
            "directional_balance": self.directional_balance.to_dict(),
            "confluence_conflict": self.confluence_conflict.to_dict(),
            "reason_codes": list(self.reason_codes),
            "summary": dict(self.summary),
            "nison_context": self.nison_context.to_dict(),
            "altunina_context": self.altunina_context.to_dict(),
            "schwager_context": self.schwager_context.to_dict(),
        }


def build_book_evidence_bucket(
    source: BookSource,
    evidence: tuple[EngineTrendEvidence, ...] | list[EngineTrendEvidence],
) -> BookEvidenceBucket:
    items = tuple(evidence)
    positive = sum(item.contribution for item in items if item.contribution > 0)
    negative = sum(item.contribution for item in items if item.contribution < 0)
    return BookEvidenceBucket(
        source=source,
        evidence=items,
        reason_codes=tuple(dict.fromkeys(item.code for item in items)),
        positive_contribution=positive,
        negative_contribution=negative,
        neutral_count=sum(item.contribution == 0 for item in items),
        evidence_count=len(items),
        direction=_direction(positive, negative),
    )


def build_directional_evidence_balance(
    evidence: tuple[EngineTrendEvidence, ...] | list[EngineTrendEvidence],
) -> DirectionalEvidenceBalance:
    items = tuple(evidence)
    bullish = sum(item.contribution for item in items if item.contribution > 0)
    bearish = abs(sum(item.contribution for item in items if item.contribution < 0))
    return DirectionalEvidenceBalance(
        bullish_score=bullish,
        bearish_score=bearish,
        neutral_evidence_count=sum(item.contribution == 0 for item in items),
        total_evidence_count=len(items),
        net_score=bullish - bearish,
        dominant_direction=_direction(bullish, bearish),
    )


def _pair_code(first: BookSource, second: BookSource, suffix: str) -> str:
    names = {first, second}
    if names == {BookSource.NISON, BookSource.ALTUNINA}:
        return f"MATRIX_NISON_ALTUNINA_{suffix}"
    if names == {BookSource.NISON, BookSource.SCHWAGER}:
        return f"MATRIX_NISON_SCHWAGER_{suffix}"
    return f"MATRIX_ALTUNINA_SCHWAGER_{suffix}"


def build_confluence_conflict_summary(
    buckets: tuple[BookEvidenceBucket, ...] | list[BookEvidenceBucket],
    directional_balance: DirectionalEvidenceBalance,
) -> ConfluenceConflictSummary:
    by_source = {item.source: item for item in buckets if item.source in BOOK_SOURCES}
    active = tuple(source for source in BOOK_SOURCES if source in by_source and by_source[source].evidence_count)
    missing = tuple(source for source in BOOK_SOURCES if source not in active)
    coverage_levels = (EvidenceCoverageLevel.EMPTY, EvidenceCoverageLevel.LOW, EvidenceCoverageLevel.MEDIUM, EvidenceCoverageLevel.HIGH)
    coverage = coverage_levels[len(active)]
    groups = {
        direction: tuple(source for source in active if by_source[source].direction is direction)
        for direction in (EvidenceDirection.BULLISH, EvidenceDirection.BEARISH, EvidenceDirection.NEUTRAL)
    }
    bullish, bearish = groups[EvidenceDirection.BULLISH], groups[EvidenceDirection.BEARISH]
    mixed = tuple(source for source in active if by_source[source].direction is EvidenceDirection.MIXED)
    if bullish and bearish:
        conflict = EvidenceConflictLevel.HIGH if max(len(bullish), len(bearish)) >= 2 else EvidenceConflictLevel.MEDIUM
        conflicting = tuple(source for source in active if source in bullish + bearish)
    elif mixed:
        conflict, conflicting = EvidenceConflictLevel.LOW, mixed
    else:
        conflict, conflicting = EvidenceConflictLevel.NONE, ()

    aligned = max(groups.values(), key=len) if groups else ()
    if len(aligned) < 2:
        aligned = ()
    codes: list[str] = [f"MATRIX_{coverage.value}_EVIDENCE_COVERAGE"]
    if aligned:
        direction = by_source[aligned[0]].direction
        codes.append(f"MATRIX_{direction.value}_CONFLUENCE")
        if len(aligned) == 3:
            codes.append("MATRIX_THREE_BOOKS_ALIGNED")
        for index, first in enumerate(aligned):
            for second in aligned[index + 1:]:
                codes.append(_pair_code(first, second, "ALIGNED"))
    for first in bullish:
        for second in bearish:
            codes.append(_pair_code(first, second, "CONFLICT"))
    if conflict is not EvidenceConflictLevel.NONE:
        codes.append(f"MATRIX_DIRECTIONAL_CONFLICT_{conflict.value}")
        codes.append("MATRIX_MIXED_BOOK_CONTEXT")
    if len(active) >= 2:
        codes.append("MATRIX_READY_FOR_REGIME_COMPOSER")
    if not active:
        codes = ["MATRIX_NO_BOOK_EVIDENCE"]

    if not active:
        agreement = BookAgreementState.NO_EVIDENCE
    elif conflict in (EvidenceConflictLevel.MEDIUM, EvidenceConflictLevel.HIGH):
        agreement = BookAgreementState.MIXED_WITH_CONFLICT
    elif conflict is EvidenceConflictLevel.LOW:
        agreement = BookAgreementState.MIXED_LOW_CONFLICT
    elif directional_balance.dominant_direction is EvidenceDirection.BULLISH and not bearish:
        agreement = BookAgreementState.ALIGNED_BULLISH
    elif directional_balance.dominant_direction is EvidenceDirection.BEARISH and not bullish:
        agreement = BookAgreementState.ALIGNED_BEARISH
    elif directional_balance.dominant_direction is EvidenceDirection.NEUTRAL:
        agreement = BookAgreementState.ALIGNED_NEUTRAL
    else:
        agreement = BookAgreementState.MIXED_LOW_CONFLICT
    directional_count = len(bullish) + len(bearish)
    return ConfluenceConflictSummary(
        agreement, conflict, coverage, aligned, conflicting, missing,
        len(aligned) / len(active) if active and aligned else 0.0,
        len(conflicting) / directional_count if directional_count else (1.0 if mixed else 0.0),
        len(active) / len(BOOK_SOURCES), tuple(dict.fromkeys(codes)),
    )


def _matrix_evidence(summary: ConfluenceConflictSummary) -> tuple[EngineTrendEvidence, ...]:
    contributions = {"MATRIX_BULLISH_CONFLUENCE": 0.10, "MATRIX_BEARISH_CONFLUENCE": -0.10}
    return tuple(
        EngineTrendEvidence(
            BookSource.ENGINE_TREND,
            code,
            "Book evidence matrix context",
            contributions.get(code, 0.0),
        )
        for code in summary.reason_codes
    )


def analyze_book_evidence_matrix(
    candles: tuple[EngineTrendCandle, ...] | list[EngineTrendCandle],
) -> BookEvidenceMatrix:
    items = tuple(candles)
    nison = analyze_nison_window_context(items)
    altunina = analyze_altunina_trend_context(items)
    schwager = analyze_schwager_range_context(items)
    buckets = (
        build_book_evidence_bucket(BookSource.NISON, nison.all_evidence),
        build_book_evidence_bucket(BookSource.ALTUNINA, altunina.evidence),
        build_book_evidence_bucket(BookSource.SCHWAGER, schwager.evidence),
    )
    book_evidence = tuple(item for bucket in buckets for item in bucket.evidence)
    balance = build_directional_evidence_balance(book_evidence)
    confluence = build_confluence_conflict_summary(buckets, balance)
    matrix_evidence = _matrix_evidence(confluence)
    all_evidence = book_evidence + matrix_evidence
    reason_codes = tuple(dict.fromkeys(item.code for item in all_evidence))
    summary = {
        "active_source_count": len(BOOK_SOURCES) - len(confluence.missing_sources),
        "total_evidence_count": balance.total_evidence_count,
        "dominant_direction": balance.dominant_direction.value,
        "agreement_state": confluence.agreement_state.value,
        "conflict_level": confluence.conflict_level.value,
        "coverage_level": confluence.coverage_level.value,
        "confluence_score": confluence.confluence_score,
        "conflict_score": confluence.conflict_score,
        "coverage_score": confluence.coverage_score,
        "ready_for_composer": confluence.coverage_level in (EvidenceCoverageLevel.MEDIUM, EvidenceCoverageLevel.HIGH),
    }
    return BookEvidenceMatrix(
        len(items), nison, altunina, schwager, buckets, balance,
        confluence, all_evidence, reason_codes, summary,
    )
