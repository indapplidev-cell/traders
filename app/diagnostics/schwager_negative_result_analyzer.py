from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.diagnostics._book_audit_utils import safe_float


class SchwagerNegativeResultAnalyzer:
    diagnostic_name = "schwager_negative_result_analyzer"
    diagnostic_version = "ml38_9_7"

    def evaluate(self, candidate_payload: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(candidate_payload)
        prediction_root = dict(payload.get("prediction_root_cause_audit", {}))
        feature_sep = dict(payload.get("feature_label_separability_audit", {}))
        label_ambiguity = dict(payload.get("label_ambiguity_audit", {}))
        setup_context = dict(payload.get("setup_context_audit", {}))
        failed_gates = [str(item) for item in payload.get("failed_gates", []) or []]
        baseline_edge = safe_float(payload.get("baseline_edge"))
        model_accuracy = safe_float(payload.get("model_accuracy"))
        baseline_accuracy = safe_float(payload.get("baseline_accuracy"))
        walk_forward_pf = safe_float(
            payload.get("walk_forward_profit_factor", payload.get("walk_forward_pf"))
        )
        profit_factor = safe_float(payload.get("profit_factor"))
        collapse_severity = str(payload.get("collapse_severity") or "").upper()
        bias_severity = str(
            payload.get("symbol_bias_severity")
            or dict(payload.get("flat_bias_diagnostics", {})).get("symbol_bias_severity")
            or ""
        ).upper()
        root_warning_set = {str(item) for item in prediction_root.get("warnings", []) or []}
        label_noise = str(label_ambiguity.get("label_noise_rating") or "UNAVAILABLE").upper()
        feature_rating = str(feature_sep.get("global_separability_rating") or "UNAVAILABLE").upper()
        positive_groups = list(setup_context.get("groups_with_positive_edge", []) or [])

        bucket = "UNKNOWN"
        if root_warning_set & {
            "actual_down_rows_mapped_to_up",
            "actual_flat_rows_mapped_to_up",
            "predicted_up_overwhelms_other_classes",
        } or collapse_severity == "CRITICAL":
            bucket = "WEAK_RAW_CLASS_SEPARATION"
        elif label_noise == "HIGH_NOISE":
            bucket = "LABEL_AMBIGUITY_HIGH"
        elif feature_rating == "WEAK":
            bucket = "FEATURE_SEPARABILITY_WEAK"
        elif positive_groups and (baseline_edge is None or baseline_edge <= 0.0):
            bucket = "SETUP_EDGE_ONLY"
        elif model_accuracy is not None and baseline_accuracy is not None and model_accuracy <= baseline_accuracy:
            bucket = "BASELINE_STRONGER_THAN_MODEL"
        elif walk_forward_pf is not None and walk_forward_pf < 1.0:
            bucket = "WALK_FORWARD_UNSTABLE"
        elif profit_factor is not None and profit_factor < 1.0:
            bucket = "PROFIT_NOT_CONFIRMED"
        elif "decision_policy_grid" in str(payload.get("prediction_decision_source") or "") or payload.get(
            "decision_policy_selected_policy_id"
        ):
            bucket = "POST_PROCESSING_NOT_ROOT_CAUSE"

        recommendation_map = {
            "WEAK_RAW_CLASS_SEPARATION": "do_not_tune_class_weights_yet",
            "LABEL_AMBIGUITY_HIGH": "evaluate_first_touch_labels",
            "FEATURE_SEPARABILITY_WEAK": "add_setup_context_features",
            "SETUP_EDGE_ONLY": "build_opportunity_first_model",
            "POST_PROCESSING_NOT_ROOT_CAUSE": "keep_gates_strict",
            "BASELINE_STRONGER_THAN_MODEL": "build_opportunity_first_model",
            "WALK_FORWARD_UNSTABLE": "keep_gates_strict",
            "PROFIT_NOT_CONFIRMED": "keep_gates_strict",
            "UNKNOWN": "do_not_tune_class_weights_yet",
        }
        primary_recommendation = recommendation_map[bucket]

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "candidate_status": payload.get("candidate_status"),
            "failed_gates": failed_gates,
            "baseline_edge": baseline_edge,
            "model_accuracy": model_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "collapse_severity": collapse_severity or None,
            "bias_severity": bias_severity or None,
            "walk_forward_profit_factor": walk_forward_pf,
            "profit_factor": profit_factor,
            "root_cause_bucket": bucket,
            "primary_recommendation": primary_recommendation,
        }
