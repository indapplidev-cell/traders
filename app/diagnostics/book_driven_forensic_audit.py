from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.diagnostics.feature_label_separability_audit import FeatureLabelSeparabilityAudit
from app.diagnostics.label_ambiguity_audit import LabelAmbiguityAudit
from app.diagnostics.schwager_negative_result_analyzer import SchwagerNegativeResultAnalyzer
from app.diagnostics.setup_context_audit import SetupContextAudit


class BookDrivenForensicAudit:
    diagnostic_name = "book_driven_forensic_audit"
    diagnostic_version = "ml38_9_7"

    def __init__(self) -> None:
        self._feature_audit = FeatureLabelSeparabilityAudit()
        self._label_audit = LabelAmbiguityAudit()
        self._setup_audit = SetupContextAudit()
        self._negative_result_analyzer = SchwagerNegativeResultAnalyzer()

    def evaluate(
        self,
        rows: Sequence[Any],
        candidate_payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        feature_label_separability_audit = self._feature_audit.evaluate(rows)
        label_ambiguity_audit = self._label_audit.evaluate(rows)
        setup_context_audit = self._setup_audit.evaluate(rows)
        analyzer_payload = dict(candidate_payload or {})
        analyzer_payload["feature_label_separability_audit"] = feature_label_separability_audit
        analyzer_payload["label_ambiguity_audit"] = label_ambiguity_audit
        analyzer_payload["setup_context_audit"] = setup_context_audit
        schwager_negative_result_analyzer = self._negative_result_analyzer.evaluate(analyzer_payload)
        final_diagnosis = self._final_diagnosis(
            feature_label_separability_audit=feature_label_separability_audit,
            label_ambiguity_audit=label_ambiguity_audit,
            setup_context_audit=setup_context_audit,
            schwager_negative_result_analyzer=schwager_negative_result_analyzer,
        )
        next_action_recommendation = self._next_action(final_diagnosis, schwager_negative_result_analyzer)
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": len(rows),
            "feature_label_separability_audit": feature_label_separability_audit,
            "label_ambiguity_audit": label_ambiguity_audit,
            "setup_context_audit": setup_context_audit,
            "schwager_negative_result_analyzer": schwager_negative_result_analyzer,
            "final_diagnosis": final_diagnosis,
            "next_action_recommendation": next_action_recommendation,
        }

    @staticmethod
    def _final_diagnosis(
        *,
        feature_label_separability_audit: Mapping[str, Any],
        label_ambiguity_audit: Mapping[str, Any],
        setup_context_audit: Mapping[str, Any],
        schwager_negative_result_analyzer: Mapping[str, Any],
    ) -> str:
        feature_rating = str(feature_label_separability_audit.get("global_separability_rating") or "UNAVAILABLE").upper()
        label_noise = str(label_ambiguity_audit.get("label_noise_rating") or "UNAVAILABLE").upper()
        ambiguous_ratio = float(label_ambiguity_audit.get("ambiguous_row_ratio") or 0.0)
        positive_groups = list(setup_context_audit.get("groups_with_positive_edge", []) or [])
        root_bucket = str(schwager_negative_result_analyzer.get("root_cause_bucket") or "UNKNOWN").upper()

        if feature_rating == "WEAK" and root_bucket in {"WEAK_RAW_CLASS_SEPARATION", "FEATURE_SEPARABILITY_WEAK"}:
            return "FEATURES_AND_LABELS_NOT_SEPARABLE"
        if label_noise == "HIGH_NOISE" or ambiguous_ratio >= 0.4:
            return "LABELS_TOO_AMBIGUOUS"
        if positive_groups and root_bucket in {"SETUP_EDGE_ONLY", "BASELINE_STRONGER_THAN_MODEL"}:
            return "SETUP_CONTEXT_EDGE_EXISTS"
        if root_bucket == "POST_PROCESSING_NOT_ROOT_CAUSE":
            return "POST_PROCESSING_NOT_ROOT_CAUSE"
        if root_bucket in {"WEAK_RAW_CLASS_SEPARATION", "WALK_FORWARD_UNSTABLE", "PROFIT_NOT_CONFIRMED"}:
            return "GLOBAL_DIRECTION_TASK_TOO_NOISY"
        if feature_rating == "GOOD" and label_noise == "GOOD":
            return "READY_FOR_CLASS_SEPARATION_OBJECTIVE"
        if label_noise in {"WATCH", "HIGH_NOISE"}:
            return "READY_FOR_SETUP_AWARE_LABELS"
        if positive_groups:
            return "READY_FOR_OPPORTUNITY_FIRST_MODEL"
        return "READY_FOR_CLASS_SEPARATION_OBJECTIVE"

    @staticmethod
    def _next_action(final_diagnosis: str, analyzer: Mapping[str, Any]) -> str:
        primary = str(analyzer.get("primary_recommendation") or "").strip()
        if primary:
            return primary
        mapping = {
            "FEATURES_AND_LABELS_NOT_SEPARABLE": "add_setup_context_features",
            "LABELS_TOO_AMBIGUOUS": "evaluate_first_touch_labels",
            "SETUP_CONTEXT_EDGE_EXISTS": "build_opportunity_first_model",
            "GLOBAL_DIRECTION_TASK_TOO_NOISY": "do_not_tune_class_weights_yet",
            "POST_PROCESSING_NOT_ROOT_CAUSE": "keep_gates_strict",
            "READY_FOR_CLASS_SEPARATION_OBJECTIVE": "do_not_tune_class_weights_yet",
            "READY_FOR_SETUP_AWARE_LABELS": "evaluate_first_touch_labels",
            "READY_FOR_OPPORTUNITY_FIRST_MODEL": "build_opportunity_first_model",
        }
        return mapping.get(final_diagnosis, "keep_gates_strict")
