from __future__ import annotations

from app.market_interpreter.context_quality import (
    ContextQualityGrade,
    ContextQualityScorer,
    rank_symbol_contexts,
    summarize_quality_distribution,
)


def test_clean_stable_high_confidence_scores_high() -> None:
    score = ContextQualityScorer().score(
        _row(bucket="CLEAN_TREND", stability="STABLE", current_regime="UP", confidence=0.82, trend_strength="STRONG")
    )

    assert score.grade == ContextQualityGrade.HIGH.value
    assert score.score >= 0.75


def test_transitioning_medium_confidence_scores_medium() -> None:
    score = ContextQualityScorer().score(
        _row(bucket="TRANSITIONING", stability="CHANGING", current_regime="UP", last_transition="FLAT_TO_UP", confidence=0.64)
    )

    assert score.grade == ContextQualityGrade.MEDIUM.value


def test_unstable_skip_candidate_scores_skip() -> None:
    score = ContextQualityScorer().score(
        _row(
            bucket="UNSTABLE",
            skip_candidate=True,
            stability="UNSTABLE",
            current_regime="FLAT",
            confidence=0.18,
        )
    )

    assert score.grade == ContextQualityGrade.SKIP.value
    assert score.score < 0.25


def test_unknown_current_regime_is_penalized() -> None:
    score = ContextQualityScorer().score(
        _row(bucket="UNKNOWN", skip_candidate=True, stability="UNSTABLE", current_regime="UNKNOWN", last_transition="TO_UNKNOWN")
    )

    assert "QUALITY_CURRENT_REGIME_UNKNOWN" in score.reason_codes
    assert "QUALITY_TRANSITION_TO_UNKNOWN" in score.reason_codes


def test_score_is_clamped_to_zero_to_one() -> None:
    high = ContextQualityScorer().score(
        _row(bucket="CLEAN_TREND", stability="STABLE", current_regime="UP", confidence=1.0, trend_strength="STRONG")
    )
    error = ContextQualityScorer().score(_row(status="ERROR", bucket="ERROR"))

    assert high.score == 1.0
    assert error.score == 0.0


def test_grade_thresholds_work() -> None:
    scorer = ContextQualityScorer()

    assert scorer.grade_for_score(0.75) == ContextQualityGrade.HIGH
    assert scorer.grade_for_score(0.50) == ContextQualityGrade.MEDIUM
    assert scorer.grade_for_score(0.25) == ContextQualityGrade.LOW
    assert scorer.grade_for_score(0.24) == ContextQualityGrade.SKIP


def test_reason_codes_include_scored_marker() -> None:
    score = ContextQualityScorer().score(_row())

    assert "CONTEXT_QUALITY_SCORED" in score.reason_codes


def test_positive_reason_codes_are_added() -> None:
    score = ContextQualityScorer().score(
        _row(bucket="CLEAN_TREND", stability="STABLE", current_regime="DOWN", confidence=0.9, trend_strength="MODERATE")
    )

    assert "QUALITY_BUCKET_CLEAN" in score.reason_codes
    assert "QUALITY_STABLE_CONTEXT" in score.reason_codes
    assert "QUALITY_CURRENT_CONFIDENCE_HIGH" in score.reason_codes
    assert "QUALITY_DIRECTIONAL_REGIME" in score.reason_codes
    assert "QUALITY_TREND_STRENGTH_SUPPORTED" in score.reason_codes


def test_negative_reason_codes_are_added() -> None:
    score = ContextQualityScorer().score(
        _row(
            bucket="UNSTABLE",
            skip_candidate=True,
            stability="UNSTABLE",
            current_regime="UNKNOWN",
            last_transition="TO_UNKNOWN",
            confidence=0.2,
        )
    )

    assert "QUALITY_SKIP_CANDIDATE_PENALTY" in score.reason_codes
    assert "QUALITY_BUCKET_UNSTABLE" in score.reason_codes
    assert "QUALITY_UNSTABLE_CONTEXT" in score.reason_codes
    assert "QUALITY_LOW_CONFIDENCE" in score.reason_codes


def test_rank_symbol_contexts_sorts_by_score_desc() -> None:
    scores = rank_symbol_contexts(
        (
            _row(symbol="LOW", bucket="TRANSITIONING", confidence=0.55),
            _row(symbol="HIGH", bucket="CLEAN_TREND", stability="STABLE", current_regime="UP", confidence=0.9),
        )
    )

    assert {score.symbol: score.rank for score in scores} == {"HIGH": 1, "LOW": 2}


def test_equal_scores_sort_by_symbol_ascending() -> None:
    scores = rank_symbol_contexts((_row(symbol="BBB"), _row(symbol="AAA")))

    assert {score.symbol: score.rank for score in scores} == {"AAA": 1, "BBB": 2}


def test_skip_candidate_gets_no_rank() -> None:
    scores = rank_symbol_contexts((_row(symbol="BTCUSDT"), _row(symbol="SOLUSDT", skip_candidate=True, bucket="UNKNOWN")))

    assert {score.symbol: score.rank for score in scores} == {"BTCUSDT": 1, "SOLUSDT": None}


def test_error_rows_get_error_grade_and_no_rank() -> None:
    score = rank_symbol_contexts((_row(symbol="ERR", status="ERROR", bucket="ERROR"),))[0]

    assert score.grade == ContextQualityGrade.ERROR.value
    assert score.score == 0.0
    assert score.rank is None


def test_summarize_quality_distribution_counts_all_grades() -> None:
    scores = (
        ContextQualityScorer().score(_row(symbol="HIGH", bucket="CLEAN_TREND", stability="STABLE", current_regime="UP", confidence=0.9)),
        ContextQualityScorer().score(_row(symbol="MEDIUM", bucket="TRANSITIONING", current_regime="UP", confidence=0.64)),
        ContextQualityScorer().score(
            _row(symbol="LOW", bucket="UNSTABLE", skip_candidate=False, stability="UNSTABLE", current_regime="UP", confidence=0.51)
        ),
        ContextQualityScorer().score(_row(symbol="SKIP", bucket="UNSTABLE", skip_candidate=True, stability="UNSTABLE", confidence=0.1)),
        ContextQualityScorer().score(_row(symbol="ERROR", status="ERROR", bucket="ERROR")),
    )

    assert summarize_quality_distribution(scores) == {"HIGH": 1, "MEDIUM": 1, "LOW": 1, "SKIP": 1, "ERROR": 1}


def test_top_ranked_symbols_are_only_ranked_symbols() -> None:
    scores = rank_symbol_contexts(
        (
            _row(symbol="BTCUSDT", bucket="CLEAN_TREND", stability="STABLE", current_regime="UP", confidence=0.9),
            _row(symbol="SOLUSDT", bucket="UNKNOWN", skip_candidate=True),
        )
    )
    top_ranked_symbols = [score.symbol for score in sorted(scores, key=lambda item: item.rank or 10**9) if score.rank is not None]

    assert top_ranked_symbols == ["BTCUSDT"]


def test_ranking_is_stable_and_deterministic() -> None:
    rows = (_row(symbol="BBB"), _row(symbol="AAA"), _row(symbol="CCC", bucket="UNKNOWN", skip_candidate=True))

    assert rank_symbol_contexts(rows) == rank_symbol_contexts(rows)


def _row(
    *,
    symbol: str = "BTCUSDT",
    status: str = "OK",
    bucket: str = "TRANSITIONING",
    skip_candidate: bool = False,
    stability: str = "CHANGING",
    current_regime: str = "UP",
    last_transition: str = "NO_CHANGE",
    confidence: float = 0.61,
    trend_strength: str = "UNKNOWN",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": status,
        "bucket": bucket,
        "skip_candidate": skip_candidate,
        "stability": stability,
        "current_regime": current_regime,
        "last_transition": last_transition,
        "current_confidence": confidence,
        "current_trend_strength": trend_strength,
    }
