from pathlib import Path

from app.evaluation.signal_gate_evaluator import SignalGateEvaluator


def test_signal_gate_evaluator_skips_flat_and_generates_directional_signals(tmp_path: Path) -> None:
    evaluator = SignalGateEvaluator(reports_dir=tmp_path)
    predictions = [
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.60,
            "prob_down": 0.20,
            "prob_flat": 0.20,
            "confidence": 0.60,
        },
        {
            "actual_label": "FLAT",
            "predicted_label": "FLAT",
            "prob_up": 0.10,
            "prob_down": 0.10,
            "prob_flat": 0.80,
            "confidence": 0.80,
        },
        {
            "actual_label": "DOWN",
            "predicted_label": "DOWN",
            "prob_up": 0.25,
            "prob_down": 0.55,
            "prob_flat": 0.20,
            "confidence": 0.55,
        },
    ]

    report = evaluator.evaluate("mv1", predictions, gate_types=["max_prob", "directional_edge", "margin"])

    max_prob_row = next(row for row in report["gate_results"] if row["gate_type"] == "max_prob" and row["threshold"] == 0.5)
    directional_edge_row = next(
        row for row in report["gate_results"] if row["gate_type"] == "directional_edge" and row["threshold"] == 0.2
    )
    margin_row = next(row for row in report["gate_results"] if row["gate_type"] == "margin" and row["threshold"] == 0.2)

    assert max_prob_row["signal_count"] == 2
    assert max_prob_row["skipped_flat_count"] == 1
    assert directional_edge_row["long_count"] == 1
    assert directional_edge_row["short_count"] == 1
    assert margin_row["signal_count"] == 2
