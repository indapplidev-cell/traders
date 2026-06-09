from pathlib import Path

from app.evaluation.confidence_gate_evaluator import ConfidenceGateEvaluator


def test_confidence_eval_reduces_coverage_as_threshold_increases(tmp_path: Path) -> None:
    evaluator = ConfidenceGateEvaluator(reports_dir=tmp_path)
    predictions = [
        {"actual_label": "UP", "predicted_label": "UP", "confidence": 0.41},
        {"actual_label": "DOWN", "predicted_label": "DOWN", "confidence": 0.56},
        {"actual_label": "FLAT", "predicted_label": "FLAT", "confidence": 0.78},
    ]

    result = evaluator.evaluate("mv1", predictions, thresholds=[0.4, 0.6, 0.8])

    coverages = [row["coverage"] for row in result["thresholds"]]
    assert coverages == sorted(coverages, reverse=True)

