from app.diagnostics.anti_collapse_diagnostics import AntiCollapseDiagnostics


def test_anti_collapse_diagnostics_scores_less_collapsed_candidate_higher() -> None:
    diagnostics = AntiCollapseDiagnostics()

    weak = diagnostics.build(
        symbol="BTCUSDT",
        config_id="weak",
        flat_bias_diagnostics={
            "flat_overprediction_ratio": 2.0,
            "down_underprediction_ratio": 0.25,
            "up_bias_ratio": 1.8,
        },
        collapse_diagnostics_v2={
            "probability_margin_distribution": {
                "margin_q50": 0.01,
                "margin_q90": 0.03,
            }
        },
    )

    better = diagnostics.build(
        symbol="BTCUSDT",
        config_id="better",
        flat_bias_diagnostics={
            "flat_overprediction_ratio": 1.1,
            "down_underprediction_ratio": 0.9,
            "up_bias_ratio": 1.0,
        },
        collapse_diagnostics_v2={
            "probability_margin_distribution": {
                "margin_q50": 0.035,
                "margin_q90": 0.07,
            }
        },
    )

    assert better.anti_collapse_score > weak.anti_collapse_score
    assert better.anti_collapse_status == "GOOD"
    assert weak.anti_collapse_status == "WEAK"
