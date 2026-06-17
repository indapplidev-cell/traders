from app.diagnostics.confidence_profitability_diagnostics import ConfidenceProfitabilityDiagnostics


def test_confidence_profitability_exposes_probability_metadata() -> None:
    result = ConfidenceProfitabilityDiagnostics().build(
        symbol="BTCUSDT",
        config_id="cfg1",
        probability_diagnostics={
            "probability_source": "temperature_scaled",
            "direction_temperature": 0.5,
            "margin_q50": 0.04,
            "margin_q90": 0.08,
            "max_prob_q90": 0.47,
            "rows_above_thresholds": {"0.45": 100},
        },
        collapse_diagnostics_v2={"collapse_detected": False},
        profit_aware_diagnostics={"profit_factor": 1.2, "total_r": 5.0},
        walk_forward_profit_diagnostics={"global_profit_factor": 1.1, "global_total_r": 4.0},
        anti_collapse_diagnostics={"anti_collapse_score": 4.0, "anti_collapse_status": "GOOD"},
    )

    payload = result.to_dict()

    assert payload["probability_source"] == "temperature_scaled"
    assert payload["direction_temperature"] == 0.5
    assert payload["confidence_profitability_status"] in {"GOOD", "WATCH", "WEAK"}
