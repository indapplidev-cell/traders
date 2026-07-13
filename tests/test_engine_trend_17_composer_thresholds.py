from dataclasses import replace

from app.market_reader.engine_trend.book_evidence_matrix import BookAgreementState, EvidenceConflictLevel, EvidenceCoverageLevel, analyze_book_evidence_matrix
from app.market_reader.engine_trend.regime_composer import compose_regime_from_matrix, score_regime_candidates
from app.market_reader.engine_trend.schemas import EngineTrendCandle, EngineTrendRegime, TradeSignal


def candles():
    closes = (100, 102, 101, 104, 103, 106, 105, 108, 107, 110, 109, 112)
    return tuple(EngineTrendCandle(f"2026-01-{i+1:02d}", c-.5, c+1, c-1, c) for i, c in enumerate(closes))


def matrix(**summary_changes):
    value = analyze_book_evidence_matrix(candles())
    return replace(value, confluence_conflict=replace(value.confluence_conflict, **summary_changes))


def scored(agreement, bullish, bearish):
    value = matrix(agreement_state=agreement, conflict_level=EvidenceConflictLevel.NONE)
    return score_regime_candidates(replace(value, directional_balance=replace(value.directional_balance, bullish_score=bullish, bearish_score=bearish)))


def test_strong_bullish_evidence_can_produce_up() -> None:
    assert scored(BookAgreementState.ALIGNED_BULLISH, .55, .05).selected_regime is EngineTrendRegime.UP


def test_strong_bearish_evidence_can_produce_down() -> None:
    assert scored(BookAgreementState.ALIGNED_BEARISH, .05, .55).selected_regime is EngineTrendRegime.DOWN


def test_strong_neutral_evidence_can_produce_flat() -> None:
    value = matrix(agreement_state=BookAgreementState.ALIGNED_NEUTRAL, conflict_level=EvidenceConflictLevel.NONE)
    value = replace(value, directional_balance=replace(value.directional_balance, bullish_score=0, bearish_score=0), altunina_context=replace(value.altunina_context, structure_direction=value.altunina_context.structure_direction.SIDEWAYS_STRUCTURE))
    assert score_regime_candidates(value).selected_regime is EngineTrendRegime.FLAT


def test_high_conflict_remains_unknown() -> None:
    value = matrix(agreement_state=BookAgreementState.MIXED_WITH_CONFLICT, conflict_level=EvidenceConflictLevel.HIGH, conflict_score=1)
    assert score_regime_candidates(value).selected_regime is EngineTrendRegime.UNKNOWN


def test_low_coverage_remains_unknown() -> None:
    assert score_regime_candidates(matrix(coverage_level=EvidenceCoverageLevel.LOW, coverage_score=1/3)).selected_regime is EngineTrendRegime.UNKNOWN


def test_composed_safety_contract_is_unchanged() -> None:
    value = matrix(agreement_state=BookAgreementState.ALIGNED_BULLISH, conflict_level=EvidenceConflictLevel.NONE)
    value = replace(value, directional_balance=replace(value.directional_balance, bullish_score=.55, bearish_score=.05))
    safety = compose_regime_from_matrix("TEST", "1h", candles(), value).result.safety
    assert safety.trade_signal is TradeSignal.NOT_EVALUATED
    assert safety.safe_for_runtime_trading is False
    assert safety.live_trading_connected is False
