from app.diagnostics.confidence_profitability_diagnostics import (
    ConfidenceProfitabilityDiagnostics,
)


def test_ml38_6_confidence_profitability_diagnostics_scores_good_candidate() -> None:
    result = ConfidenceProfitabilityDiagnostics().build(
        symbol="BTCUSDT",
        config_id="lv4_h06_thr035_tp12_sl08_cp",
        probability_diagnostics={
            "margin_q50": 0.04,
            "margin_q90": 0.08,
            "max_prob_q90": 0.48,
            "rows_above_thresholds": {"0.45": 120},
        },
        collapse_diagnostics_v2={
            "collapse_detected": False,
            "collapse_type": None,
            "probability_margin_distribution": {"margin_q50": 0.04, "margin_q90": 0.08},
            "confidence_distribution": {
                "max_prob_q90": 0.48,
                "rows_above_thresholds": {"0.45": 120},
            },
        },
        profit_aware_diagnostics={
            "profit_aware_profit_factor": 1.08,
            "profit_aware_total_r": 12.5,
        },
        walk_forward_profit_diagnostics={
            "walk_forward_profit_factor": 1.04,
            "walk_forward_total_r": 42.0,
        },
        anti_collapse_diagnostics={
            "anti_collapse_score": 4.5,
            "anti_collapse_status": "GOOD",
        },
    ).to_dict()

    assert result["diagnostic_version"] == "ml38_6"
    assert result["confidence_profitability_status"] == "GOOD"
    assert result["confidence_profitability_score"] > 5.0
    assert result["safety"]["accepts_candidate"] is False
    assert result["safety"]["softens_gates"] is False


def test_ml38_6_confidence_profitability_diagnostics_penalizes_collapse() -> None:
    result = ConfidenceProfitabilityDiagnostics().build(
        symbol="ETHUSDT",
        config_id="weak",
        probability_diagnostics={"margin_q50": 0.01, "margin_q90": 0.03},
        collapse_diagnostics_v2={
            "collapse_detected": True,
            "collapse_type": "LOW_MARGIN",
            "probability_margin_distribution": {"margin_q50": 0.01, "margin_q90": 0.03},
            "confidence_distribution": {
                "max_prob_q90": 0.37,
                "rows_above_thresholds": {"0.45": 0},
            },
        },
        profit_aware_diagnostics={"profit_aware_profit_factor": 0.9, "profit_aware_total_r": -4.0},
        walk_forward_profit_diagnostics={"walk_forward_profit_factor": 0.95, "walk_forward_total_r": -20.0},
        anti_collapse_diagnostics={"anti_collapse_score": 0.0, "anti_collapse_status": "WEAK"},
    ).to_dict()

    assert result["confidence_profitability_status"] == "WEAK"
    assert result["collapse_detected"] is True
    assert result["confidence_profitability_score"] < 0.0
