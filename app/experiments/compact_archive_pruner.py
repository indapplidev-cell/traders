from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Callable


DEFAULT_MAX_COMPACT_TRAINING_REPORT_BYTES = 2_000_000
DEFAULT_MAX_COMPACT_FEATURE_SUMMARY_BYTES = 8_000_000
DEFAULT_LIST_SAMPLE_SIZE = 3
DEFAULT_MAX_DEPTH = 7
DEFAULT_MAX_STRING_CHARS = 20_000

COMPACT_SCHEMA_VERSION = "ml38.10.36.1"

KEEP_TOP_LEVEL_KEYS = {
    "status",
    "stage",
    "stage_name",
    "stage_context",
    "symbol",
    "interval",
    "start_date",
    "end_date",
    "config_id",
    "label_config_id",
    "model_version",
    "model_type",
    "training_run_id",
    "run_id",
    "candidate_status",
    "quality_status",
    "quality_decision_allowed",
    "approved_for_live_trading",
    "approved_for_auto_activation",
    "started_at",
    "finished_at",
    "duration_seconds",
    "error",
    "errors",
    "warnings",
}

KEEP_SUMMARY_KEYS = {
    "dataset_summary",
    "label_summary",
    "training_summary",
    "model_summary",
    "quality_validation",
    "quality_gate_summary",
    "gate_summary",
    "profit_aware_summary",
    "profit_aware_evaluation_summary",
    "walk_forward_summary",
    "walk_forward_validation_summary",
    "feature_regime_filter_summary",
    "feature_filter_diagnostics",
    "candidate_summary",
    "candidate_result_summary",
    "rejection_summary",
    "flat_bias_root_cause_audit",
    "label_threshold_horizon_sensitivity_audit",
    "label_recoverability_requirements",
    "next_label_diagnostic_plan",
    "ml38_10_38_label_audit_decision",
    "read_only_label_grid_sensitivity_recompute",
    "production_label_semantics_parity_audit",
    "label_recompute_semantics_gap_board",
    "current_config_mapping_audit",
    "ml38_10_40_parity_decision",
    "production_denominator_mask_alignment_audit",
    "mask_cascade_board",
    "denominator_gap_board",
    "production_like_recompute_prerequisite_checklist",
    "ml38_10_41_alignment_decision",
    "per_row_production_mask_join_audit",
    "mask_source_discovery_board",
    "per_row_mask_join_board",
    "mask_cascade_count_board",
    "missing_per_row_sources",
    "next_extractor_requirements",
    "production_mask_join_decision",
    "read_only_production_mask_value_extractor_audit",
    "timestamp_join_key_audit",
    "mask_value_extraction_board",
    "mask_value_availability_summary",
    "production_label_extraction_summary",
    "extractor_blockers",
    "next_join_plan",
    "ml38_10_43_extractor_decision",
    "read_only_evaluator_payload_reproduction_audit",
    "evaluator_payload_source_audit",
    "payload_reproduction_board",
    "timestamp_payload_join_board",
    "reproduced_mask_value_summary",
    "cascade_readiness_after_reproduction",
    "reproduction_blockers",
    "next_step_plan",
    "ml38_10_44_reproduction_decision",
    "read_only_predicted_label_payload_trace_audit",
    "predicted_label_source_discovery_board",
    "candidate_payload_omission_audit",
    "prediction_row_locator_board",
    "timestamp_prediction_join_readiness",
    "actual_vs_predicted_guardrail",
    "trace_blockers",
    "next_reproduction_plan",
    "ml38_10_45_predicted_label_trace_decision",
    "read_only_test_only_evaluator_payload_reproduction_audit",
    "test_prediction_payload_source",
    "test_prediction_join_board",
    "test_only_payload_reproduction_board",
    "test_only_reproduced_mask_summary",
    "test_only_cascade_readiness",
    "full_dataset_guardrail",
    "ml38_10_46_test_only_reproduction_decision",
    "read_only_test_only_mask_cascade_counts_audit",
    "test_only_mask_input_summary",
    "test_only_mask_cascade_board",
    "test_only_mask_removed_breakdown",
    "test_only_distribution_before_after",
    "test_only_final_mask_summary",
    "ml38_10_47_test_only_mask_cascade_decision",
    "conditional_regime_rule_threshold_sensitivity_board",
    "conditional_regime_threshold_sensitivity_summary",
    "aggregate_conditional_regime_rule_threshold_sensitivity_board",
    "aggregate_conditional_regime_threshold_sensitivity_summary",
    "conditional_regime_rule_relaxation_probe_board",
    "conditional_regime_relaxation_probe_summary",
    "aggregate_conditional_regime_rule_relaxation_probe_board",
    "aggregate_conditional_regime_relaxation_probe_summary",
    "conditional_regime_metric_overlap_board",
    "aggregate_conditional_regime_metric_overlap_board",
}

KEEP_FEATURE_SUMMARY_KEYS = {
    "status",
    "stage",
    "symbol",
    "interval",
    "experiment_id",
    "candidate_count",
    "accepted_candidate_count",
    "rejected_candidate_count",
    "failed_candidate_count",
    "best_candidate_config_id",
    "best_candidate_score",
    "quality_decision_allowed",
    "approved_for_live_trading",
    "approved_for_auto_activation",
    "validation",
    "ranking",
    "candidate_board",
    "compact_summary",
    "feature_filter_diagnostics",
    "fold_feature_regime_repair_probe",
    "fold_feature_regime_adaptive_repair_probe",
    "walk_forward_summary",
    "flat_bias_root_cause_audit",
    "label_threshold_horizon_sensitivity_audit",
    "label_recoverability_requirements",
    "next_label_diagnostic_plan",
    "ml38_10_38_label_audit_decision",
    "read_only_label_grid_sensitivity_recompute",
    "production_label_semantics_parity_audit",
    "label_recompute_semantics_gap_board",
    "current_config_mapping_audit",
    "ml38_10_40_parity_decision",
    "production_denominator_mask_alignment_audit",
    "mask_cascade_board",
    "denominator_gap_board",
    "production_like_recompute_prerequisite_checklist",
    "ml38_10_41_alignment_decision",
    "per_row_production_mask_join_audit",
    "mask_source_discovery_board",
    "per_row_mask_join_board",
    "mask_cascade_count_board",
    "missing_per_row_sources",
    "next_extractor_requirements",
    "production_mask_join_decision",
    "read_only_production_mask_value_extractor_audit",
    "timestamp_join_key_audit",
    "mask_value_extraction_board",
    "mask_value_availability_summary",
    "production_label_extraction_summary",
    "extractor_blockers",
    "next_join_plan",
    "ml38_10_43_extractor_decision",
    "read_only_evaluator_payload_reproduction_audit",
    "evaluator_payload_source_audit",
    "payload_reproduction_board",
    "timestamp_payload_join_board",
    "reproduced_mask_value_summary",
    "cascade_readiness_after_reproduction",
    "reproduction_blockers",
    "next_step_plan",
    "ml38_10_44_reproduction_decision",
    "read_only_predicted_label_payload_trace_audit",
    "predicted_label_source_discovery_board",
    "candidate_payload_omission_audit",
    "prediction_row_locator_board",
    "timestamp_prediction_join_readiness",
    "actual_vs_predicted_guardrail",
    "trace_blockers",
    "next_reproduction_plan",
    "ml38_10_45_predicted_label_trace_decision",
    "read_only_test_only_evaluator_payload_reproduction_audit",
    "test_prediction_payload_source",
    "test_prediction_join_board",
    "test_only_payload_reproduction_board",
    "test_only_reproduced_mask_summary",
    "test_only_cascade_readiness",
    "full_dataset_guardrail",
    "ml38_10_46_test_only_reproduction_decision",
    "read_only_test_only_mask_cascade_counts_audit",
    "test_only_mask_input_summary",
    "test_only_mask_cascade_board",
    "test_only_mask_removed_breakdown",
    "test_only_distribution_before_after",
    "test_only_final_mask_summary",
    "ml38_10_47_test_only_mask_cascade_decision",
}

# Scalar and bounded summaries required by the multi-symbol analyzer after the
# verbose feature/regime payload has been pruned.  This is deliberately small:
# it preserves aggregation truth without restoring candidate rows or fold data.
COMPACT_AGGREGATION_KEYS = (
    "status",
    "experiment_id",
    "experiment_status",
    "symbol",
    "interval",
    "candidate_count",
    "evaluated_candidate_count",
    "failed_candidate_count",
    "accepted_candidate_count",
    "rejected_candidate_count",
    "feature_version_used",
    "real_feature_diagnostics_used",
    "real_feature_diagnostics_row_count",
    "real_feature_diagnostics_missing_reason",
    "effective_gap_count_for_training",
    "gap_severity_for_training",
    "gap_training_safe",
    "regime_training_applied",
    "regime_specific_training_applied",
    "regime_specific_training_applied_any",
    "regime_specific_training_applied_all",
    "regime_label_builder_used_in_training_any",
    "regime_label_builder_used_in_training_all",
    "regime_features_attached",
    "regime_feature_count",
    "regime_features_missing_reason",
    "candle_ta_context_features_attached",
    "candle_ta_context_feature_count",
    "candle_ta_context_missing_reason",
    "book_setup_context_features_attached",
    "book_setup_context_feature_count",
    "book_setup_context_missing_reason",
    "fv4_feature_count",
    "missing_context_feature_count",
)

COMPACT_AGGREGATION_BOUNDED_KEYS = (
    "regime_label_builder_status",
    "feature_quality_summary",
    "regime_feature_summary",
    "gap_quality_summary",
    "gap_training_summary",
)

FEATURE_CANDIDATE_ARRAY_KEYS = {
    "candidate_results",
    "configs_ranked",
    "candidates",
    "accepted_candidates",
    "rejected_candidates",
    "failed_candidates",
}

HEAVY_DETAIL_KEYS = {
    "rows",
    "data",
    "records",
    "predictions",
    "prediction_rows",
    "probability_rows",
    "feature_rows",
    "label_rows",
    "dataset_rows",
    "train_rows",
    "validation_rows",
    "test_rows",
    "events",
    "pipeline_events",
    "training_events",
    "raw_events",
    "fold_rows",
    "fold_details",
    "per_row_results",
    "per_candle_results",
    "trade_rows",
    "sample_rows",
    "debug_rows",
    "raw_predictions",
    "raw_probabilities",
    "raw_features",
    "raw_labels",
}


@dataclass(frozen=True)
class CompactFileResult:
    path: str
    compacted: bool
    original_size_bytes: int
    final_size_bytes: int
    saved_size_bytes: int
    reason: str


@dataclass(frozen=True)
class CompactArchivePruneResult:
    root: str
    training_pipeline_reports_seen: int
    training_pipeline_reports_compacted: int
    feature_summaries_seen: int
    feature_summaries_compacted: int
    original_size_bytes: int
    final_size_bytes: int
    saved_size_bytes: int
    files: list[CompactFileResult]


def _value_length(value: Any) -> int | None:
    return len(value) if isinstance(value, (dict, list, str)) else None


def _heavy_key_marker(key: str, value: Any) -> dict[str, Any]:
    return {
        "_compact_pruned": True,
        "reason": "heavy_detail_key",
        "key": key,
        "original_type": type(value).__name__,
        "original_len": _value_length(value),
    }


def compact_json_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = DEFAULT_MAX_DEPTH,
    list_sample_size: int = DEFAULT_LIST_SAMPLE_SIZE,
    max_string_chars: int = DEFAULT_MAX_STRING_CHARS,
) -> Any:
    if isinstance(value, dict):
        if depth >= max_depth:
            return {
                "_compact_pruned": True,
                "reason": "max_depth",
                "original_type": "dict",
                "keys_count": len(value),
            }
        compacted: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            if text_key in HEAVY_DETAIL_KEYS:
                compacted[text_key] = _heavy_key_marker(text_key, item)
            else:
                compacted[text_key] = compact_json_value(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    list_sample_size=list_sample_size,
                    max_string_chars=max_string_chars,
                )
        return compacted

    if isinstance(value, list):
        sample = [
            compact_json_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                list_sample_size=list_sample_size,
                max_string_chars=max_string_chars,
            )
            for item in value[:list_sample_size]
        ]
        if len(value) <= list_sample_size:
            return sample
        return {
            "_compact_pruned": True,
            "original_type": "list",
            "original_len": len(value),
            "sample": sample,
        }

    if isinstance(value, str) and len(value) > max_string_chars:
        return {
            "_compact_pruned": True,
            "reason": "string_truncated",
            "original_type": "str",
            "original_len": len(value),
            "preview": value[:max_string_chars],
        }

    return value


def compact_training_pipeline_report_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "compact_report": True,
            "compact_reason": "non_dict_payload",
            "original_type": type(payload).__name__,
        }

    compacted: dict[str, Any] = {}
    for key in payload:
        if key in KEEP_TOP_LEVEL_KEYS or key in KEEP_SUMMARY_KEYS:
            compacted[key] = compact_json_value(payload[key])
        elif key in HEAVY_DETAIL_KEYS:
            compacted[key] = _heavy_key_marker(key, payload[key])
    compacted["compact_report"] = True
    compacted["compact_reason"] = "training_pipeline_report_hardening"
    return compacted


def compact_feature_regime_summary_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "compact_report": True,
            "compact_reason": "non_dict_payload",
            "original_type": type(payload).__name__,
        }

    compacted: dict[str, Any] = {}
    for key in payload:
        if key in KEEP_FEATURE_SUMMARY_KEYS or key in FEATURE_CANDIDATE_ARRAY_KEYS:
            compacted[key] = compact_json_value(payload[key])

    existing_compact_summary = (
        dict(payload.get("compact_summary"))
        if isinstance(payload.get("compact_summary"), dict)
        else {}
    )
    aggregation_summary = dict(existing_compact_summary)
    for key in COMPACT_AGGREGATION_KEYS:
        if key in payload:
            aggregation_summary[key] = payload[key]
    for key in COMPACT_AGGREGATION_BOUNDED_KEYS:
        if key in payload:
            aggregation_summary[key] = compact_json_value(
                payload[key],
                max_depth=4,
                list_sample_size=1,
                max_string_chars=2_000,
            )
    aggregation_summary["schema_version"] = "ml38.10.36.2"
    aggregation_summary["source"] = "feature_regime_experiment_summary"
    compacted["compact_summary"] = aggregation_summary
    compacted["compact_report"] = True
    compacted["compact_reason"] = "feature_regime_summary_hardening"
    return compacted


def compact_json_file(
    path: Path,
    *,
    payload_compactor: Callable[[Any], dict[str, Any]],
    max_target_bytes: int,
    reason: str,
) -> CompactFileResult:
    path = Path(path)
    original_size = path.stat().st_size
    if original_size <= max_target_bytes:
        return CompactFileResult(
            path=str(path),
            compacted=False,
            original_size_bytes=original_size,
            final_size_bytes=original_size,
            saved_size_bytes=0,
            reason="within_target_size",
        )

    result_reason = reason
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        compacted = payload_compactor(payload)
        compacted["__compact_archive_pruning__"] = {
            "compact_report": True,
            "reason": reason,
            "original_size_bytes": original_size,
            "target_max_bytes": max_target_bytes,
            "schema_version": COMPACT_SCHEMA_VERSION,
        }
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        result_reason = "invalid_json_replaced_with_stub"
        compacted = {
            "compact_report": True,
            "compact_error": "invalid_json_replaced_with_stub",
            "original_size_bytes": original_size,
            "schema_version": COMPACT_SCHEMA_VERSION,
        }

    path.write_text(
        json.dumps(compacted, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    final_size = path.stat().st_size
    return CompactFileResult(
        path=str(path),
        compacted=True,
        original_size_bytes=original_size,
        final_size_bytes=final_size,
        saved_size_bytes=max(0, original_size - final_size),
        reason=result_reason,
    )


def compact_staged_symbol_output(
    root: Path,
    *,
    max_training_report_bytes: int = DEFAULT_MAX_COMPACT_TRAINING_REPORT_BYTES,
    max_feature_summary_bytes: int = DEFAULT_MAX_COMPACT_FEATURE_SUMMARY_BYTES,
) -> CompactArchivePruneResult:
    root = Path(root)
    training_reports = sorted(
        root.glob("label_grid_runtime/**/training_pipeline_report.json")
    )
    feature_summaries = [
        path
        for path in [root / "feature_regime_experiment_summary.json"]
        if path.is_file()
    ]

    file_results: list[CompactFileResult] = []
    for path in training_reports:
        file_results.append(
            compact_json_file(
                path,
                payload_compactor=compact_training_pipeline_report_payload,
                max_target_bytes=max_training_report_bytes,
                reason="training_pipeline_report_exceeds_compact_target",
            )
        )
    for path in feature_summaries:
        file_results.append(
            compact_json_file(
                path,
                payload_compactor=compact_feature_regime_summary_payload,
                max_target_bytes=max_feature_summary_bytes,
                reason="feature_regime_summary_exceeds_compact_target",
            )
        )

    result = CompactArchivePruneResult(
        root=str(root),
        training_pipeline_reports_seen=len(training_reports),
        training_pipeline_reports_compacted=sum(
            result.compacted for result in file_results[: len(training_reports)]
        ),
        feature_summaries_seen=len(feature_summaries),
        feature_summaries_compacted=sum(
            result.compacted for result in file_results[len(training_reports) :]
        ),
        original_size_bytes=sum(result.original_size_bytes for result in file_results),
        final_size_bytes=sum(result.final_size_bytes for result in file_results),
        saved_size_bytes=sum(result.saved_size_bytes for result in file_results),
        files=file_results,
    )
    summary_payload = {
        "schema_version": COMPACT_SCHEMA_VERSION,
        **asdict(result),
    }
    (root / "compact_archive_pruning_summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    return result
