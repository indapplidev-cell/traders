from dataclasses import replace
from pathlib import Path

import pytest

from app.market_reader.engine_trend.book_evidence_matrix import (
    BookAgreementState,
    EvidenceConflictLevel,
    EvidenceCoverageLevel,
    analyze_book_evidence_matrix,
)
from app.market_reader.engine_trend.ohlc_integrity import OHLCIntegrityResult
from app.market_reader.engine_trend.regime_composer import (
    RegimeComposerOutput,
    RegimeComposerStatus,
    compose_engine_trend_result,
    score_regime_candidates,
)
from app.market_reader.engine_trend.schemas import EngineTrendCandle, EngineTrendRegime, EngineTrendResult, TradeSignal


def candles() -> tuple[EngineTrendCandle, ...]:
    closes = (100, 102, 101, 104, 103, 106, 105, 108, 107, 110, 109, 112)
    return tuple(EngineTrendCandle(f"2026-01-{index + 1:02d}", close - 0.5, close + 1, close - 1, close) for index, close in enumerate(closes))


def matrix_with(**changes):
    matrix = analyze_book_evidence_matrix(candles())
    summary = replace(matrix.confluence_conflict, **changes)
    return replace(matrix, confluence_conflict=summary)


@pytest.mark.parametrize(
    ("agreement", "bullish", "bearish", "expected"),
    [
        (BookAgreementState.ALIGNED_BULLISH, 0.55, 0.05, EngineTrendRegime.UP),
        (BookAgreementState.ALIGNED_BEARISH, 0.05, 0.55, EngineTrendRegime.DOWN),
        (BookAgreementState.ALIGNED_NEUTRAL, 0.0, 0.0, EngineTrendRegime.FLAT),
    ],
)
def test_scores_primary_candidates(agreement, bullish, bearish, expected) -> None:
    matrix = matrix_with(agreement_state=agreement, conflict_level=EvidenceConflictLevel.NONE)
    matrix = replace(matrix, directional_balance=replace(matrix.directional_balance, bullish_score=bullish, bearish_score=bearish))
    if expected is EngineTrendRegime.FLAT:
        matrix = replace(matrix, altunina_context=replace(matrix.altunina_context, structure_direction=matrix.altunina_context.structure_direction.SIDEWAYS_STRUCTURE))
    assert score_regime_candidates(matrix).selected_regime is expected


@pytest.mark.parametrize("coverage", [EvidenceCoverageLevel.EMPTY, EvidenceCoverageLevel.LOW])
def test_low_evidence_selects_unknown_and_caps_confidence(coverage) -> None:
    scores = score_regime_candidates(matrix_with(coverage_level=coverage, coverage_score=0.0 if coverage is EvidenceCoverageLevel.EMPTY else 1 / 3))
    assert scores.selected_regime is EngineTrendRegime.UNKNOWN
    assert scores.confidence <= 0.25


def test_high_conflict_selects_unknown_and_caps_confidence() -> None:
    scores = score_regime_candidates(matrix_with(conflict_level=EvidenceConflictLevel.HIGH, conflict_score=1.0, agreement_state=BookAgreementState.MIXED_WITH_CONFLICT))
    assert scores.selected_regime is EngineTrendRegime.UNKNOWN
    assert scores.confidence <= 0.35


def test_invalid_integrity_selects_unknown() -> None:
    scores = score_regime_candidates(matrix_with(), OHLCIntegrityResult(False, errors=("BROKEN_CANDLE",)))
    assert scores.selected_regime is EngineTrendRegime.UNKNOWN
    assert scores.confidence == 0.0


def test_small_scores_and_small_margin_are_conservative() -> None:
    matrix = matrix_with(agreement_state=BookAgreementState.MIXED_LOW_CONFLICT, confluence_score=0.0)
    balance = replace(matrix.directional_balance, bullish_score=0.20, bearish_score=0.19)
    altunina = replace(
        matrix.altunina_context,
        trend_strength_score=0.0,
        trend_consistency_score=0.0,
        trend_progress_score=0.0,
    )
    scores = score_regime_candidates(replace(matrix, directional_balance=balance, altunina_context=altunina))
    assert scores.selected_regime is EngineTrendRegime.UNKNOWN
    assert scores.confidence <= 0.35


def test_main_composer_returns_explainable_fail_closed_result() -> None:
    output = compose_engine_trend_result("TEST", "1h", candles())
    assert isinstance(output, RegimeComposerOutput)
    assert isinstance(output.result, EngineTrendResult)
    assert output.result.market_regime in set(EngineTrendRegime)
    assert output.result.safety.safe_for_runtime_trading is False
    assert output.result.safety.live_trading_connected is False
    assert output.result.safety.trade_signal is TradeSignal.NOT_EVALUATED
    exported = output.to_dict()
    assert {"decision_trace", "result"} <= exported.keys()
    assert set(output.result.book_evidence.to_dict()) == {"nison", "altunina", "schwager", "engine_trend"}
    assert any(code.startswith("COMPOSER_") for code in output.result.reason_codes)


@pytest.mark.parametrize(("symbol", "interval"), [("", "1h"), ("TEST", "")])
def test_invalid_input_does_not_crash(symbol: str, interval: str) -> None:
    output = compose_engine_trend_result(symbol, interval, candles())
    assert output.result.market_regime is EngineTrendRegime.UNKNOWN
    assert output.result.confidence == 0.0
    assert output.result.errors


def test_empty_candles_are_fail_closed() -> None:
    output = compose_engine_trend_result("TEST", "1h", ())
    assert output.result.market_regime is EngineTrendRegime.UNKNOWN
    assert output.result.candle_count == 0
    assert output.result.confidence == 0.0
    assert "NO_CANDLES_PROVIDED" in output.result.errors
    assert output.decision_trace.status is RegimeComposerStatus.INPUT_INVALID


def test_stack_has_no_legacy_dependency() -> None:
    source = Path("app/market_reader/engine_trend/regime_composer.py").read_text(encoding="utf-8")
    legacy_names = ("market_regime_composer", "trend_structure", "range_structure", "breakout_retest", "technical_context")
    assert all(name not in source for name in legacy_names)
