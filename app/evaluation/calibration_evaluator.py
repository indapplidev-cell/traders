from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


class CalibrationEvaluator:
    BIN_EDGES = [index / 10 for index in range(11)]

    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, model_version: str, predictions: list[dict[str, Any]], brier_score: float) -> dict[str, Any]:
        bins = [f"{self.BIN_EDGES[index]:.1f}-{self.BIN_EDGES[index + 1]:.1f}" for index in range(10)]
        confidence_bins = {label: [] for label in bins}
        for row in predictions:
            confidence = row["confidence"]
            index = min(int(confidence * 10), 9)
            label = bins[index]
            confidence_bins[label].append(row)

        avg_confidence_by_bin = []
        accuracy_by_bin = []
        count_by_bin = []
        ece = 0.0
        total = len(predictions)
        for label in bins:
            rows = confidence_bins[label]
            count = len(rows)
            count_by_bin.append(count)
            if count == 0:
                avg_confidence_by_bin.append(0.0)
                accuracy_by_bin.append(0.0)
                continue
            avg_confidence = sum(row["confidence"] for row in rows) / count
            accuracy = sum(int(row["predicted_label"] == row["actual_label"]) for row in rows) / count
            avg_confidence_by_bin.append(avg_confidence)
            accuracy_by_bin.append(accuracy)
            ece += abs(avg_confidence - accuracy) * (count / total)

        report = {
            "model_version": model_version,
            "brier_score": brier_score,
            "expected_calibration_error": ece,
            "confidence_bins": bins,
            "avg_confidence_by_bin": avg_confidence_by_bin,
            "accuracy_by_bin": accuracy_by_bin,
            "count_by_bin": count_by_bin,
        }
        output_path = self._reports_dir / f"calibration_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report
