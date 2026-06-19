from __future__ import annotations

from typing import Any


class TwoStageTradeDiagnostics:
    diagnostic_name = "two_stage_trade_diagnostics"
    diagnostic_version = "ml38.10.6"

    def evaluate_metrics(
        self,
        metrics: dict[str, Any],
        *,
        min_precision: float = 0.25,
        min_recall: float = 0.50,
        max_predicted_trade_rate: float = 0.15,
        max_predicted_to_actual_trade_rate_ratio: float = 3.0,
        max_false_positive_rate: float = 0.25,
    ) -> dict[str, Any]:
        trade_row_ratio = float(metrics.get("trade_row_ratio", 0.0) or 0.0)
        predicted_trade_rate = float(metrics.get("predicted_trade_rate", 0.0) or 0.0)
        predicted_to_actual_ratio = float(metrics.get("predicted_to_actual_trade_rate_ratio", 0.0) or 0.0)
        opportunity_precision = float(metrics.get("opportunity_precision", 0.0) or 0.0)
        opportunity_recall = float(metrics.get("opportunity_recall", 0.0) or 0.0)
        opportunity_f1 = float(metrics.get("opportunity_f1", 0.0) or 0.0)
        false_positive_rate = float(metrics.get("opportunity_false_positive_rate", 0.0) or 0.0)
        direction_accuracy = float(metrics.get("direction_accuracy_on_trade_rows", 0.0) or 0.0)
        direction_rows = int(metrics.get("direction_trade_rows", 0) or 0)
        threshold = float(metrics.get("opportunity_probability_threshold", 0.5) or 0.5)

        warnings: list[str] = []
        if trade_row_ratio < 0.03:
            warnings.append("trade_rows_too_sparse")
        if predicted_trade_rate > max(0.20, trade_row_ratio * 4.0):
            warnings.append("predicted_trade_rate_too_high")
        if predicted_trade_rate < max(0.005, trade_row_ratio * 0.20):
            warnings.append("predicted_trade_rate_too_low")
        if opportunity_recall < 0.05:
            warnings.append("opportunity_recall_too_low")
        if opportunity_precision < 0.05 and predicted_trade_rate > 0.0:
            warnings.append("opportunity_precision_too_low")
        if direction_rows == 0:
            warnings.append("no_direction_trade_rows")
        if opportunity_precision < min_precision:
            warnings.append("opportunity_precision_below_gate")
        if opportunity_recall < min_recall:
            warnings.append("opportunity_recall_below_gate")
        if predicted_trade_rate > max_predicted_trade_rate:
            warnings.append("predicted_trade_rate_above_gate")
        if predicted_to_actual_ratio > max_predicted_to_actual_trade_rate_ratio:
            warnings.append("predicted_to_actual_trade_rate_ratio_above_gate")
        if false_positive_rate > max_false_positive_rate:
            warnings.append("opportunity_false_positive_rate_above_gate")

        status = "WATCH"
        if warnings:
            status = "NEEDS_REWORK"
        if (
            trade_row_ratio >= 0.03
            and opportunity_precision >= max(0.10, min_precision)
            and opportunity_recall >= max(0.10, min_recall)
            and opportunity_f1 >= 0.10
            and direction_accuracy >= 0.45
        ):
            status = "PROMISING"
        precision_control_warnings = {
            "opportunity_precision_below_gate",
            "opportunity_recall_below_gate",
            "predicted_trade_rate_above_gate",
            "predicted_to_actual_trade_rate_ratio_above_gate",
            "opportunity_false_positive_rate_above_gate",
        }

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "status": status,
            "warnings": warnings,
            "opportunity_probability_threshold": threshold,
            "trade_row_ratio": trade_row_ratio,
            "no_trade_row_ratio": float(metrics.get("no_trade_row_ratio", 0.0) or 0.0),
            "predicted_trade_rate": predicted_trade_rate,
            "actual_trade_rate": float(metrics.get("actual_trade_rate", trade_row_ratio) or 0.0),
            "predicted_to_actual_trade_rate_ratio": predicted_to_actual_ratio,
            "opportunity_precision": opportunity_precision,
            "opportunity_recall": opportunity_recall,
            "opportunity_f1": opportunity_f1,
            "opportunity_false_positive_rate": false_positive_rate,
            "direction_accuracy_on_trade_rows": direction_accuracy,
            "direction_trade_rows": direction_rows,
            "precision_control_passed": not any(reason in precision_control_warnings for reason in warnings),
            "precision_control_gates": {
                "min_precision": float(min_precision),
                "min_recall": float(min_recall),
                "max_predicted_trade_rate": float(max_predicted_trade_rate),
                "max_predicted_to_actual_trade_rate_ratio": float(max_predicted_to_actual_trade_rate_ratio),
                "max_false_positive_rate": float(max_false_positive_rate),
            },
        }
