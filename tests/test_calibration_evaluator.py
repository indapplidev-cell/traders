from pathlib import Path

from app.evaluation.calibration_evaluator import CalibrationEvaluator


def test_calibration_eval_builds_bins(tmp_path: Path) -> None:
    evaluator = CalibrationEvaluator(reports_dir=tmp_path)
    predictions = [
        {"actual_label": "UP", "predicted_label": "UP", "confidence": 0.15},
        {"actual_label": "DOWN", "predicted_label": "UP", "confidence": 0.35},
        {"actual_label": "FLAT", "predicted_label": "FLAT", "confidence": 0.95},
    ]

    result = evaluator.evaluate("mv1", predictions, brier_score=0.5)

    assert len(result["confidence_bins"]) == 10
    assert sum(result["count_by_bin"]) == 3

