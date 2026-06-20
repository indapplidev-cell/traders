from __future__ import annotations

from typing import Any


class TwoStageTradeDiagnostics:
    diagnostic_name = "two_stage_trade_diagnostics"
    diagnostic_version = "ml38.10.9"

    def evaluate_metrics(
        self,
        metrics: dict[str, Any],
        *,
        min_precision: float = 0.30,
        min_recall: float = 0.45,
        min_f1: float = 0.35,
        min_predicted_trade_rate: float = 0.03,
        max_predicted_trade_rate: float = 0.14,
        max_predicted_to_actual_trade_rate_ratio: float = 2.5,
        max_false_positive_rate: float = 0.10,
        min_direction_trade_rows: int = 20,
        setup_quality_min_threshold: float | None = None,
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

        setup_quality_bucket_metrics = dict(metrics.get("setup_quality_bucket_metrics", {}))
        setup_quality_bucket_metrics_raw = dict(
            metrics.get("setup_quality_bucket_metrics_raw", {})
        )
        setup_quality_bucket_metrics_after_mask = dict(
            metrics.get("setup_quality_bucket_metrics_after_mask", setup_quality_bucket_metrics)
        )
        setup_quality_distribution = dict(metrics.get("setup_quality_distribution", {}))
        setup_quality_filter_summary = dict(metrics.get("setup_quality_filter_summary", {}))
        setup_quality_precision_signal = self._build_setup_quality_precision_signal(
            setup_quality_bucket_metrics=setup_quality_bucket_metrics_after_mask
            or setup_quality_bucket_metrics,
        )
        setup_quality_decision_mask_summary = {
            "enabled": bool(metrics.get("setup_quality_decision_mask_enabled", False)),
            "min_threshold": metrics.get("setup_quality_decision_mask_min_threshold"),
            "masked_row_count": int(metrics.get("setup_quality_masked_row_count", 0) or 0),
            "forced_no_trade_count": int(metrics.get("setup_quality_forced_no_trade_count", 0) or 0),
            "trade_prediction_removed_count": int(
                metrics.get("setup_quality_mask_trade_prediction_removed_count", 0) or 0
            ),
        }

        missing_or_zero_bucket = dict(
            setup_quality_bucket_metrics_after_mask.get("missing_or_zero", {})
        )
        missing_or_zero_false_positive_count = int(
            missing_or_zero_bucket.get("false_positive_count", 0) or 0
        )

        warnings: list[str] = []
        quality_gate_failures: list[str] = []
        anti_undertrading_failures: list[str] = []

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
            quality_gate_failures.append("opportunity_precision_below_gate")
        if opportunity_recall < min_recall:
            warnings.append("opportunity_recall_below_gate")
            quality_gate_failures.append("opportunity_recall_below_gate")
        if opportunity_f1 < min_f1:
            warnings.append("opportunity_f1_below_gate")
            quality_gate_failures.append("opportunity_f1_below_gate")
        if predicted_trade_rate < min_predicted_trade_rate:
            warnings.append("predicted_trade_rate_below_gate")
            quality_gate_failures.append("predicted_trade_rate_below_gate")
            anti_undertrading_failures.append("predicted_trade_rate_below_gate")
        if predicted_trade_rate > max_predicted_trade_rate:
            warnings.append("predicted_trade_rate_above_gate")
            quality_gate_failures.append("predicted_trade_rate_above_gate")
        if predicted_to_actual_ratio > max_predicted_to_actual_trade_rate_ratio:
            warnings.append("predicted_to_actual_trade_rate_ratio_above_gate")
            quality_gate_failures.append("predicted_to_actual_trade_rate_ratio_above_gate")
        if false_positive_rate > max_false_positive_rate:
            warnings.append("opportunity_false_positive_rate_above_gate")
            quality_gate_failures.append("opportunity_false_positive_rate_above_gate")
        if missing_or_zero_false_positive_count > 0:
            warnings.append("missing_or_zero_false_positive_count_above_gate")
            quality_gate_failures.append("missing_or_zero_false_positive_count_above_gate")
        if direction_rows < min_direction_trade_rows:
            warnings.append("direction_trade_rows_below_quality_gate")
            quality_gate_failures.append("direction_trade_rows_below_quality_gate")

        if opportunity_recall < 0.35:
            anti_undertrading_failures.append("opportunity_recall_below_anti_undertrading_minimum")
        if opportunity_f1 < 0.20:
            anti_undertrading_failures.append("opportunity_f1_below_anti_undertrading_minimum")
        if direction_rows < 10:
            anti_undertrading_failures.append("direction_trade_rows_below_anti_undertrading_minimum")

        precision_control_warnings = {
            "opportunity_precision_below_gate",
            "opportunity_recall_below_gate",
            "predicted_trade_rate_above_gate",
            "predicted_to_actual_trade_rate_ratio_above_gate",
            "opportunity_false_positive_rate_above_gate",
        }

        two_stage_quality_gate = {
            "passed": not quality_gate_failures,
            "failed_reasons": list(dict.fromkeys(quality_gate_failures)),
            "min_precision": float(min_precision),
            "min_recall": float(min_recall),
            "min_f1": float(min_f1),
            "min_predicted_trade_rate": float(min_predicted_trade_rate),
            "max_predicted_trade_rate": float(max_predicted_trade_rate),
            "max_predicted_to_actual_trade_rate_ratio": float(max_predicted_to_actual_trade_rate_ratio),
            "max_false_positive_rate": float(max_false_positive_rate),
            "min_direction_trade_rows": int(min_direction_trade_rows),
            "missing_or_zero_false_positive_count": int(missing_or_zero_false_positive_count),
        }
        anti_undertrading_gate = {
            "passed": not anti_undertrading_failures,
            "failed_reasons": list(dict.fromkeys(anti_undertrading_failures)),
            "min_predicted_trade_rate": float(min_predicted_trade_rate),
            "min_recall": 0.35,
            "min_f1": 0.20,
            "min_direction_trade_rows": 10,
        }

        status = "WATCH"
        if warnings:
            status = "NEEDS_REWORK"
        if two_stage_quality_gate["passed"] and anti_undertrading_gate["passed"]:
            status = "TWO_STAGE_PROMISING"
        elif not anti_undertrading_gate["passed"]:
            status = "TWO_STAGE_UNDERTRADING"
        elif (
            trade_row_ratio >= 0.03
            and opportunity_precision >= max(0.10, min_precision)
            and opportunity_recall >= max(0.10, min_recall)
            and opportunity_f1 >= 0.10
            and direction_accuracy >= 0.45
        ):
            status = "PROMISING"

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "status": status,
            "warnings": list(dict.fromkeys(warnings)),
            "opportunity_probability_threshold": threshold,
            "setup_quality_min_threshold": (
                metrics.get("setup_quality_min_threshold")
                if metrics.get("setup_quality_min_threshold") is not None
                else setup_quality_min_threshold
            ),
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
            "precision_control_passed": not any(
                reason in precision_control_warnings for reason in warnings
            ),
            "precision_control_gates": {
                "min_precision": float(min_precision),
                "min_recall": float(min_recall),
                "max_predicted_trade_rate": float(max_predicted_trade_rate),
                "max_predicted_to_actual_trade_rate_ratio": float(
                    max_predicted_to_actual_trade_rate_ratio
                ),
                "max_false_positive_rate": float(max_false_positive_rate),
            },
            "two_stage_quality_gate": two_stage_quality_gate,
            "two_stage_quality_gate_passed": bool(two_stage_quality_gate["passed"]),
            "anti_undertrading_gate": anti_undertrading_gate,
            "anti_undertrading_gate_passed": bool(anti_undertrading_gate["passed"]),
            "setup_quality_bucket_metrics": setup_quality_bucket_metrics,
            "setup_quality_bucket_metrics_raw": setup_quality_bucket_metrics_raw,
            "setup_quality_bucket_metrics_after_mask": setup_quality_bucket_metrics_after_mask,
            "setup_quality_distribution": setup_quality_distribution,
            "setup_quality_filter_summary": setup_quality_filter_summary,
            "setup_quality_decision_mask_summary": setup_quality_decision_mask_summary,
            "setup_quality_precision_signal": setup_quality_precision_signal,
        }

    @staticmethod
    def _build_setup_quality_precision_signal(
        *,
        setup_quality_bucket_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        if not setup_quality_bucket_metrics:
            return {
                "best_precision_bucket": None,
                "best_precision_bucket_precision": 0.0,
                "best_precision_bucket_recall": 0.0,
                "recommended_next_action": "setup_quality_score_not_discriminative",
            }

        ranked = [
            (
                str(bucket_name),
                float(dict(bucket_payload).get("precision", 0.0) or 0.0),
                float(dict(bucket_payload).get("recall", 0.0) or 0.0),
                int(dict(bucket_payload).get("row_count", 0) or 0),
            )
            for bucket_name, bucket_payload in setup_quality_bucket_metrics.items()
            if int(dict(bucket_payload).get("row_count", 0) or 0) > 0
        ]
        if not ranked:
            return {
                "best_precision_bucket": None,
                "best_precision_bucket_precision": 0.0,
                "best_precision_bucket_recall": 0.0,
                "recommended_next_action": "setup_quality_score_not_discriminative",
            }
        ranked.sort(key=lambda item: (item[1], item[2], item[3]), reverse=True)
        best_bucket, best_precision, best_recall, _ = ranked[0]
        recommended_next_action = "setup_quality_score_not_discriminative"
        if best_bucket in {"good_0_60_0_75", "strong_0_75_1_00"} and best_precision >= 0.30 and best_recall >= 0.45:
            recommended_next_action = "evaluate_setup_quality_filtered_runtime"
        elif best_bucket == "strong_0_75_1_00" and best_precision >= 0.30 and best_recall < 0.45:
            recommended_next_action = "lower_setup_quality_threshold_or_add_features"
        return {
            "best_precision_bucket": best_bucket,
            "best_precision_bucket_precision": float(best_precision),
            "best_precision_bucket_recall": float(best_recall),
            "recommended_next_action": recommended_next_action,
        }
