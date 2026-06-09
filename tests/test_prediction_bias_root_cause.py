from types import SimpleNamespace

from app.diagnostics.prediction_bias_root_cause import PredictionBiasRootCause


def test_prediction_bias_root_cause_detects_training_bias_and_no_down_predictions() -> None:
    analyzer = PredictionBiasRootCause()
    split_payloads = {
        "train": {
            "split_name": "train",
            "rows": [_row("UP"), _row("DOWN"), _row("FLAT")],
            "predictions": [_prediction("UP"), _prediction("UP"), _prediction("UP")],
        },
        "validation": {
            "split_name": "validation",
            "rows": [_row("UP"), _row("DOWN"), _row("FLAT")],
            "predictions": [_prediction("UP"), _prediction("UP"), _prediction("UP")],
        },
        "test": {
            "split_name": "test",
            "rows": [_row("UP"), _row("DOWN"), _row("FLAT")],
            "predictions": [_prediction("UP"), _prediction("UP"), _prediction("UP")],
        },
    }

    report = analyzer.build_report(model_version="mv1", label_version="lv1", split_payloads=split_payloads)

    assert "predicts_no_down" in report["splits"]["test"]["warnings"]
    assert "predicts_up_but_labels_balanced" in report["splits"]["test"]["warnings"]
    assert "likely_training_bias" in report["warnings"]
    assert "down_recall_zero" in report["splits"]["test"]["warnings"]


def _row(direction_label: str) -> SimpleNamespace:
    return SimpleNamespace(direction_label=direction_label)


def _prediction(predicted_label: str) -> dict[str, float | str]:
    if predicted_label == "UP":
        return {"predicted_label": "UP", "prob_up": 0.8, "prob_down": 0.1, "prob_flat": 0.1}
    if predicted_label == "DOWN":
        return {"predicted_label": "DOWN", "prob_up": 0.1, "prob_down": 0.8, "prob_flat": 0.1}
    return {"predicted_label": "FLAT", "prob_up": 0.1, "prob_down": 0.1, "prob_flat": 0.8}
