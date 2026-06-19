from __future__ import annotations

from typing import Any


class TwoStageTradeDiagnostics:
    diagnostic_name = "two_stage_trade_diagnostics"
    diagnostic_version = "ml38.10.5"

    def evaluate_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        trade_row_ratio = float(metrics.get("trade_row_ratio", 0.0) or 0.0)
        predicted_trade_rate = float(metrics.get("predicted_trade_rate", 0.0) or 0.0)
        opportunity_precision = float(metrics.get("opportunity_precision", 0.0) or 0.0)
        opportunity_recall = float(metrics.get("opportunity_recall", 0.0) or 0.0)
        opportunity_f1 = float(metrics.get("opportunity_f1", 0.0) or 0.0)
        direction_accuracy = float(metrics.get("direction_accuracy_on_trade_rows", 0.0) or 0.0)
        direction_rows = int(metrics.get("direction_trade_rows", 0) or 0)

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

        status = "WATCH"
        if warnings:
            status = "NEEDS_REWORK"
        if (
            trade_row_ratio >= 0.03
            and opportunity_precision >= 0.10
            and opportunity_recall >= 0.10
            and opportunity_f1 >= 0.10
            and direction_accuracy >= 0.45
        ):
            status = "PROMISING"

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "status": status,
            "warnings": warnings,
            "trade_row_ratio": trade_row_ratio,
            "no_trade_row_ratio": float(metrics.get("no_trade_row_ratio", 0.0) or 0.0),
            "predicted_trade_rate": predicted_trade_rate,
            "actual_trade_rate": float(metrics.get("actual_trade_rate", trade_row_ratio) or 0.0),
            "opportunity_precision": opportunity_precision,
            "opportunity_recall": opportunity_recall,
            "opportunity_f1": opportunity_f1,
            "opportunity_false_positive_rate": float(metrics.get("opportunity_false_positive_rate", 0.0) or 0.0),
            "direction_accuracy_on_trade_rows": direction_accuracy,
            "direction_trade_rows": direction_rows,
        }
