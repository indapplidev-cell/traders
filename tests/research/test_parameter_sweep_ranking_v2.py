from traders_ml.parameter_sweep.ranking import (
    PERFORMANCE_CLASSES, pareto_frontier, rank_results, rank_stability,
    selection_bias_guard,
)


def _row(identity, expectancy, pf, drawdown, trades=30, status="ACCEPTED"):
    return {"config_id": identity, "evaluation_status": status, "expectancy_R": expectancy, "profit_factor": pf, "max_drawdown": drawdown, "trade_count": trades, "symbol_coverage": 4, "rank_stability": .8}


def test_positive_zero_loss_missing_pf_ranks_above_loss_making_finite_pf():
    zero_loss = _row("zero-loss", None, None, 0, trades=1) | {
        "wins": 1, "losses": 0, "net_pnl": 1.0,
    }
    loss_making = _row("loss-making", None, .95, 0, trades=3) | {
        "wins": 1, "losses": 2, "net_pnl": -.05,
    }
    assert [row["config_id"] for row in rank_results([loss_making, zero_loss])] == [
        "zero-loss", "loss-making",
    ]


def test_missing_pf_without_positive_zero_loss_evidence_keeps_zero_sentinel():
    no_trades = _row("no-trades", None, None, 0, trades=0) | {
        "wins": 0, "losses": 0, "net_pnl": 0,
    }
    finite = _row("finite", None, .5, 0, trades=1) | {
        "wins": 0, "losses": 1, "net_pnl": -1,
    }
    assert [row["config_id"] for row in rank_results([no_trades, finite])] == [
        "finite", "no-trades",
    ]


def test_multi_metric_ranking_and_pareto_are_deterministic():
    rows = [_row("stable", .2, 1.3, 2), _row("risky", .2, 1.3, 5), _row("negative", -.1, .8, 1)]
    assert [row["config_id"] for row in rank_results(rows)][:2] == ["stable", "risky"]
    assert "risky" not in pareto_frontier(rows)


def test_invalid_evaluation_is_never_ranked():
    assert rank_results([_row("bad", 10, 10, 0, status="INVALID")]) == []


def test_stability_and_selection_bias_guard():
    assert rank_stability([.1, .2, .15]) > rank_stability([.5, -.5, .5])
    assert selection_bias_guard(hypothesis_count=1000, independent_observations=10) == "PROMOTION_FORBIDDEN_SELECTION_BIAS_RISK"
    assert selection_bias_guard(hypothesis_count=10, independent_observations=10) == "PASS"
    assert PERFORMANCE_CLASSES == ("INVALID", "INSUFFICIENT_SAMPLE", "NEGATIVE_EXPECTANCY", "WEAK", "PROMISING_RESEARCH", "VALIDATION_CANDIDATE")
