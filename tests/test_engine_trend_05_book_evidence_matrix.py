from pathlib import Path

import pytest

from app.market_reader.engine_trend.book_evidence_matrix import (
    BookAgreementState,
    BookEvidenceMatrix,
    EvidenceConflictLevel,
    EvidenceCoverageLevel,
    EvidenceDirection,
    analyze_book_evidence_matrix,
    build_book_evidence_bucket,
    build_confluence_conflict_summary,
    build_directional_evidence_balance,
)
from app.market_reader.engine_trend.schemas import BookSource, EngineTrendCandle, EngineTrendEvidence


def evidence(source: BookSource, code: str, contribution: float) -> EngineTrendEvidence:
    return EngineTrendEvidence(source, code, code, contribution)


def bucket(source: BookSource, contribution: float):
    return build_book_evidence_bucket(source, [evidence(source, f"{source.value}_CONTEXT", contribution)])


def summary(*buckets):
    items = [item for current in buckets for item in current.evidence]
    return build_confluence_conflict_summary(buckets, build_directional_evidence_balance(items))


def candles() -> tuple[EngineTrendCandle, ...]:
    closes = (100, 102, 101, 104, 103, 106, 105, 108, 107, 110, 109, 112)
    return tuple(EngineTrendCandle(str(index), close - 0.5, close + 1, close - 1, close) for index, close in enumerate(closes))


@pytest.mark.parametrize(
    ("values", "expected"),
    [((0.2,), EvidenceDirection.BULLISH), ((-0.2,), EvidenceDirection.BEARISH), ((0.0,), EvidenceDirection.NEUTRAL), ((0.2, -0.2), EvidenceDirection.MIXED)],
)
def test_bucket_metrics(values: tuple[float, ...], expected: EvidenceDirection) -> None:
    items = [evidence(BookSource.NISON, f"NISON_{index}", value) for index, value in enumerate(values)]
    result = build_book_evidence_bucket(BookSource.NISON, items)
    assert result.direction is expected
    assert result.evidence_count == len(values)
    assert result.neutral_count == values.count(0.0)
    assert result.reason_codes == tuple(item.code for item in items)
    assert {"source", "evidence", "direction", "reason_codes"} <= result.to_dict().keys()


@pytest.mark.parametrize(
    ("values", "direction"),
    [((0.2, 0.0), EvidenceDirection.BULLISH), ((-0.2, 0.0), EvidenceDirection.BEARISH), ((0.2, -0.2), EvidenceDirection.MIXED), ((0.0,), EvidenceDirection.NEUTRAL)],
)
def test_directional_balance(values: tuple[float, ...], direction: EvidenceDirection) -> None:
    result = build_directional_evidence_balance([evidence(BookSource.NISON, str(index), value) for index, value in enumerate(values)])
    assert result.bullish_score == sum(value for value in values if value > 0)
    assert result.bearish_score == abs(sum(value for value in values if value < 0))
    assert result.neutral_evidence_count == values.count(0.0)
    assert result.net_score == pytest.approx(result.bullish_score - result.bearish_score)
    assert result.dominant_direction is direction


@pytest.mark.parametrize(
    ("sources", "level"),
    [((), EvidenceCoverageLevel.EMPTY), ((BookSource.NISON,), EvidenceCoverageLevel.LOW), ((BookSource.NISON, BookSource.ALTUNINA), EvidenceCoverageLevel.MEDIUM), ((BookSource.NISON, BookSource.ALTUNINA, BookSource.SCHWAGER), EvidenceCoverageLevel.HIGH)],
)
def test_coverage(sources: tuple[BookSource, ...], level: EvidenceCoverageLevel) -> None:
    buckets = [bucket(source, 0.0) for source in sources]
    result = summary(*buckets)
    assert result.coverage_level is level
    assert result.coverage_score == pytest.approx(len(sources) / 3)


@pytest.mark.parametrize("value", [0.2, -0.2, 0.0])
def test_pair_confluence_is_complementary(value: float) -> None:
    result = summary(bucket(BookSource.NISON, value), bucket(BookSource.ALTUNINA, value), bucket(BookSource.SCHWAGER, 0.1 if value == 0 else 0.0))
    assert BookSource.NISON in result.aligned_sources
    assert BookSource.ALTUNINA in result.aligned_sources
    assert result.confluence_score > 0
    assert "MATRIX_NISON_ALTUNINA_ALIGNED" in result.reason_codes


def test_three_book_neutral_alignment() -> None:
    result = summary(*(bucket(source, 0.0) for source in (BookSource.NISON, BookSource.ALTUNINA, BookSource.SCHWAGER)))
    assert result.agreement_state is BookAgreementState.ALIGNED_NEUTRAL
    assert "MATRIX_THREE_BOOKS_ALIGNED" in result.reason_codes
    assert "MATRIX_NEUTRAL_CONFLUENCE" in result.reason_codes
    assert "MATRIX_NISON_ALTUNINA_ALIGNED" in result.reason_codes
    assert "MATRIX_NISON_SCHWAGER_ALIGNED" in result.reason_codes
    assert "MATRIX_ALTUNINA_SCHWAGER_ALIGNED" in result.reason_codes


@pytest.mark.parametrize(
    ("first", "second", "code"),
    [(BookSource.NISON, BookSource.ALTUNINA, "MATRIX_NISON_ALTUNINA_CONFLICT"), (BookSource.NISON, BookSource.SCHWAGER, "MATRIX_NISON_SCHWAGER_CONFLICT"), (BookSource.ALTUNINA, BookSource.SCHWAGER, "MATRIX_ALTUNINA_SCHWAGER_CONFLICT")],
)
def test_pair_conflict(first: BookSource, second: BookSource, code: str) -> None:
    result = summary(bucket(first, 0.2), bucket(second, -0.2))
    assert result.conflict_level is EvidenceConflictLevel.MEDIUM
    assert result.agreement_state is BookAgreementState.MIXED_WITH_CONFLICT
    assert code in result.reason_codes
    assert "MATRIX_DIRECTIONAL_CONFLICT_MEDIUM" in result.reason_codes


def test_multiple_sources_raise_conflict_level() -> None:
    result = summary(bucket(BookSource.NISON, 0.2), bucket(BookSource.ALTUNINA, 0.2), bucket(BookSource.SCHWAGER, -0.2))
    assert result.conflict_level is EvidenceConflictLevel.HIGH
    assert "MATRIX_DIRECTIONAL_CONFLICT_HIGH" in result.reason_codes


def test_main_matrix_preserves_all_three_book_contexts() -> None:
    result = analyze_book_evidence_matrix(candles())
    assert isinstance(result, BookEvidenceMatrix)
    assert len(result.buckets) == 3
    assert result.nison_context.candle_count == len(candles())
    assert result.altunina_context.candle_count == len(candles())
    assert result.schwager_context.candle_count == len(candles())
    assert result.all_evidence
    assert any(item.source is BookSource.ENGINE_TREND for item in result.all_evidence)
    assert set(result.nison_context.reason_codes) <= set(result.reason_codes)
    assert set(result.altunina_context.reason_codes) <= set(result.reason_codes)
    assert set(result.schwager_context.reason_codes) <= set(result.reason_codes)
    assert "ready_for_composer" in result.summary
    assert {"candle_count", "buckets", "directional_balance", "confluence_conflict", "nison_context", "altunina_context", "schwager_context"} <= result.to_dict().keys()


def test_stage_has_no_old_module_dependency_or_final_result() -> None:
    source = Path("app/market_reader/engine_trend/book_evidence_matrix.py").read_text(encoding="utf-8")
    assert "EngineTrendResult" not in source
    assert "market_regime" not in source
    for old_name in ("market_regime_composer", "trend_structure", "range_structure", "breakout_retest", "technical_context"):
        assert old_name not in source
