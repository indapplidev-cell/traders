from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


class SignalGateEvaluator:
    GATE_THRESHOLDS = {
        "max_prob": [0.34, 0.36, 0.38, 0.40, 0.42, 0.45, 0.50],
        "directional_max_prob": [0.34, 0.36, 0.38, 0.40, 0.42, 0.45, 0.50],
        "margin": [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20],
        "directional_edge": [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20],
        "entropy": [0.90, 1.00, 1.05, 1.08],
    }

    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(
        self,
        model_version: str,
        predictions: list[dict[str, Any]],
        gate_types: list[str] | None = None,
    ) -> dict[str, Any]:
        gate_types = gate_types or list(self.GATE_THRESHOLDS)
        gate_results: list[dict[str, Any]] = []
        for gate_type in gate_types:
            for threshold in self.GATE_THRESHOLDS[gate_type]:
                gate_results.append(self._evaluate_threshold(predictions, gate_type, threshold))

        report = {"model_version": model_version, "gate_results": gate_results}
        output_path = self._reports_dir / f"signal_gate_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def select_signals(self, predictions: list[dict[str, Any]], gate_type: str, threshold: float) -> dict[str, Any]:
        selected: list[dict[str, Any]] = []
        skipped_flat_count = 0
        for row in predictions:
            measured = self._measure(row)
            signal_direction, skipped_flat = self._gate_decision(gate_type, threshold, measured)
            if skipped_flat:
                skipped_flat_count += 1
                continue
            if signal_direction is None:
                continue
            enriched = dict(row)
            enriched["signal_direction"] = signal_direction
            enriched["margin"] = measured["margin"]
            enriched["directional_edge"] = measured["directional_edge"]
            enriched["entropy"] = measured["entropy"]
            enriched["directional_confidence"] = measured["directional_confidence"]
            selected.append(enriched)
        return {
            "gate_type": gate_type,
            "threshold": threshold,
            "total_rows": len(predictions),
            "signal_rows": selected,
            "signal_count": len(selected),
            "skipped_flat_count": skipped_flat_count,
        }

    def _evaluate_threshold(self, predictions: list[dict[str, Any]], gate_type: str, threshold: float) -> dict[str, Any]:
        selection = self.select_signals(predictions, gate_type, threshold)
        signal_rows = selection["signal_rows"]
        signal_count = selection["signal_count"]
        long_rows = [row for row in signal_rows if row["signal_direction"] == "LONG"]
        short_rows = [row for row in signal_rows if row["signal_direction"] == "SHORT"]
        correct = sum(int(self._is_correct_signal(row)) for row in signal_rows)
        return {
            "gate_type": gate_type,
            "threshold": threshold,
            "total_rows": selection["total_rows"],
            "signal_count": signal_count,
            "skipped_flat_count": selection["skipped_flat_count"],
            "long_count": len(long_rows),
            "short_count": len(short_rows),
            "coverage": (signal_count / selection["total_rows"]) if selection["total_rows"] else 0.0,
            "accuracy_on_signals": (correct / signal_count) if signal_count else 0.0,
            "long_accuracy": self._direction_accuracy(long_rows, "UP"),
            "short_accuracy": self._direction_accuracy(short_rows, "DOWN"),
            "avg_confidence_on_signals": self._mean([float(row["confidence"]) for row in signal_rows]),
            "avg_margin_on_signals": self._mean([float(row["margin"]) for row in signal_rows]),
            "avg_directional_edge_on_signals": self._mean([float(row["directional_edge"]) for row in signal_rows]),
        }

    def _gate_decision(self, gate_type: str, threshold: float, measured: dict[str, Any]) -> tuple[str | None, bool]:
        predicted_label = measured["predicted_label"]
        if gate_type == "max_prob":
            if measured["confidence"] < threshold:
                return None, False
            if predicted_label == "FLAT":
                return None, True
            return ("LONG" if predicted_label == "UP" else "SHORT"), False

        if gate_type == "directional_max_prob":
            if measured["directional_confidence"] < threshold:
                return None, False
            if measured["prob_up"] == measured["prob_down"]:
                return None, False
            return ("LONG" if measured["prob_up"] > measured["prob_down"] else "SHORT"), False

        if gate_type == "margin":
            if measured["margin"] < threshold:
                return None, False
            if predicted_label == "FLAT":
                return None, True
            return ("LONG" if predicted_label == "UP" else "SHORT"), False

        if gate_type == "directional_edge":
            if measured["directional_edge"] < threshold or measured["prob_up"] == measured["prob_down"]:
                return None, False
            return ("LONG" if measured["prob_up"] > measured["prob_down"] else "SHORT"), False

        if gate_type == "entropy":
            if measured["entropy"] > threshold:
                return None, False
            if predicted_label == "FLAT":
                return None, True
            return ("LONG" if predicted_label == "UP" else "SHORT"), False

        raise ValueError(f"Unsupported gate_type: {gate_type}")

    @staticmethod
    def _measure(row: dict[str, Any]) -> dict[str, Any]:
        prob_up = float(row["prob_up"])
        prob_down = float(row["prob_down"])
        prob_flat = float(row["prob_flat"])
        ordered = sorted([prob_up, prob_down, prob_flat], reverse=True)
        entropy = 0.0
        for probability in (prob_up, prob_down, prob_flat):
            if probability > 0:
                entropy -= probability * math.log(probability)
        return {
            "predicted_label": row["predicted_label"],
            "confidence": float(row["confidence"]),
            "prob_up": prob_up,
            "prob_down": prob_down,
            "prob_flat": prob_flat,
            "margin": ordered[0] - ordered[1],
            "directional_edge": abs(prob_up - prob_down),
            "entropy": entropy,
            "directional_confidence": max(prob_up, prob_down),
        }

    @staticmethod
    def _is_correct_signal(row: dict[str, Any]) -> bool:
        return (row["signal_direction"] == "LONG" and row["actual_label"] == "UP") or (
            row["signal_direction"] == "SHORT" and row["actual_label"] == "DOWN"
        )

    @staticmethod
    def _direction_accuracy(rows: list[dict[str, Any]], expected_label: str) -> float:
        if not rows:
            return 0.0
        return sum(int(row["actual_label"] == expected_label) for row in rows) / len(rows)

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0
