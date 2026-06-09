from app.diagnostics.prediction_probability_diagnostics import PredictionProbabilityDiagnostics


def test_probability_diagnostics_computes_quantiles_and_threshold_breakdown() -> None:
    diagnostics = PredictionProbabilityDiagnostics()
    predictions = [
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.60,
            "prob_down": 0.30,
            "prob_flat": 0.10,
            "confidence": 0.60,
        },
        {
            "actual_label": "DOWN",
            "predicted_label": "DOWN",
            "prob_up": 0.20,
            "prob_down": 0.50,
            "prob_flat": 0.30,
            "confidence": 0.50,
        },
        {
            "actual_label": "FLAT",
            "predicted_label": "FLAT",
            "prob_up": 0.34,
            "prob_down": 0.33,
            "prob_flat": 0.33,
            "confidence": 0.34,
        },
    ]

    report = diagnostics.build_report(model_version="mv1", predictions=predictions)

    assert report["total_rows"] == 3
    assert report["predicted_direction_counts"] == {"UP": 1, "DOWN": 1, "FLAT": 1}
    assert report["max_prob_q00"] == 0.34
    assert report["max_prob_q50"] == 0.5
    assert report["max_prob_q100"] == 0.6
    assert round(report["margin_q50"], 2) == 0.20
    above_045 = next(row for row in report["top_class_by_threshold"] if row["threshold"] == 0.45)
    assert above_045["rows_above_threshold"] == 2
    assert above_045["predicted_direction_counts"] == {"UP": 1, "DOWN": 1, "FLAT": 0}
