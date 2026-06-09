from __future__ import annotations

from typing import Any


class DirectionBiasDiagnostics:
    def build_report(self, predictions: list[dict[str, Any]], signal_rows: list[dict[str, Any]]) -> dict[str, Any]:
        total_predictions = len(predictions)
        predicted_counts = {"UP": 0, "DOWN": 0, "FLAT": 0}
        actual_counts = {"UP": 0, "DOWN": 0, "FLAT": 0}
        for row in predictions:
            predicted_counts[row["predicted_label"]] += 1
            actual_counts[row["actual_label"]] += 1

        long_count = sum(int(row["signal_direction"] == "LONG") for row in signal_rows)
        short_count = sum(int(row["signal_direction"] == "SHORT") for row in signal_rows)
        total_signals = len(signal_rows)
        signal_long_ratio = (long_count / total_signals) if total_signals else 0.0
        signal_short_ratio = (short_count / total_signals) if total_signals else 0.0
        warnings: list[str] = []
        predicted_up_ratio = (predicted_counts["UP"] / total_predictions) if total_predictions else 0.0
        predicted_down_ratio = (predicted_counts["DOWN"] / total_predictions) if total_predictions else 0.0
        predicted_flat_ratio = (predicted_counts["FLAT"] / total_predictions) if total_predictions else 0.0
        if predicted_up_ratio >= 0.80:
            warnings.append("predicted_up_ratio_gte_0_80")
        if predicted_down_ratio >= 0.80:
            warnings.append("predicted_down_ratio_gte_0_80")
        if long_count == 0:
            warnings.append("no_long_signals")
        if short_count == 0:
            warnings.append("no_short_signals")
        if total_signals and max(signal_long_ratio, signal_short_ratio) >= 0.90:
            warnings.append("long_short_imbalance_gte_0_90")

        return {
            "predicted_up_ratio": predicted_up_ratio,
            "predicted_down_ratio": predicted_down_ratio,
            "predicted_flat_ratio": predicted_flat_ratio,
            "signal_long_ratio": signal_long_ratio,
            "signal_short_ratio": signal_short_ratio,
            "actual_up_ratio": (actual_counts["UP"] / total_predictions) if total_predictions else 0.0,
            "actual_down_ratio": (actual_counts["DOWN"] / total_predictions) if total_predictions else 0.0,
            "actual_flat_ratio": (actual_counts["FLAT"] / total_predictions) if total_predictions else 0.0,
            "long_short_signal_balance": abs(signal_long_ratio - signal_short_ratio),
            "warnings": warnings,
        }
