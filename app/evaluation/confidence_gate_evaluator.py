from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.training.metrics import LABEL_TO_INDEX


class ConfidenceGateEvaluator:
    DEFAULT_THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]

    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, model_version: str, predictions: list[dict[str, Any]], thresholds: list[float] | None = None) -> dict[str, Any]:
        thresholds = thresholds or list(self.DEFAULT_THRESHOLDS)
        rows = []
        total = len(predictions)
        for threshold in thresholds:
            selected = [row for row in predictions if row["confidence"] >= threshold]
            signal_count = len(selected)
            correct = sum(int(row["predicted_label"] == row["actual_label"]) for row in selected)
            confusion_matrix = [[0, 0, 0] for _ in range(3)]
            for row in selected:
                confusion_matrix[LABEL_TO_INDEX[row["actual_label"]]][LABEL_TO_INDEX[row["predicted_label"]]] += 1
            predicted_up = sum(confusion_matrix[source][LABEL_TO_INDEX["UP"]] for source in range(3))
            predicted_down = sum(confusion_matrix[source][LABEL_TO_INDEX["DOWN"]] for source in range(3))
            precision_up = (
                confusion_matrix[LABEL_TO_INDEX["UP"]][LABEL_TO_INDEX["UP"]] / predicted_up if predicted_up else 0.0
            )
            precision_down = (
                confusion_matrix[LABEL_TO_INDEX["DOWN"]][LABEL_TO_INDEX["DOWN"]] / predicted_down if predicted_down else 0.0
            )
            flat_predictions = sum(int(row["predicted_label"] == "FLAT") for row in selected)
            rows.append(
                {
                    "threshold": threshold,
                    "coverage": (signal_count / total) if total else 0.0,
                    "signal_count": signal_count,
                    "accuracy_on_signals": (correct / signal_count) if signal_count else 0.0,
                    "precision_up_on_signals": precision_up,
                    "precision_down_on_signals": precision_down,
                    "flat_prediction_ratio": (flat_predictions / signal_count) if signal_count else 0.0,
                    "avg_confidence": (sum(row["confidence"] for row in selected) / signal_count) if signal_count else 0.0,
                }
            )

        report = {"model_version": model_version, "thresholds": rows}
        output_path = self._reports_dir / f"confidence_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report
