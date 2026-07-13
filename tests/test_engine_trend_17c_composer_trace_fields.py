from app.market_reader.engine_trend.regime_composer import score_regime_candidates
from app.market_reader.engine_trend.schemas import EngineTrendRegime
from tests.test_engine_trend_06_book_based_regime_composer import candles
from app.market_reader.engine_trend.book_evidence_matrix import analyze_book_evidence_matrix


def test_trace_exposes_scores_rankings_fallback_without_decision_change():
    matrix = analyze_book_evidence_matrix(candles())
    baseline = score_regime_candidates(matrix)
    trace = baseline.to_dict()["composer_trace"]
    assert set(trace["raw_scores"]) == {"UP", "DOWN", "FLAT", "UNKNOWN"}
    assert set(trace["clamped_scores"]) == {"UP", "DOWN", "FLAT", "UNKNOWN"}
    assert len(trace["ranking_before_clamp"]) == 4
    assert len(trace["ranking_after_clamp"]) == 4
    assert "fallback_reason" in trace and trace["confidence_path"]
    repeated = score_regime_candidates(matrix)
    assert repeated.selected_regime is baseline.selected_regime
    assert repeated.confidence == baseline.confidence
    assert baseline.selected_regime in EngineTrendRegime
