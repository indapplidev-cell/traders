from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable


DEFAULT_MAX_COMPACT_TRAINING_REPORT_BYTES = 2_000_000
DEFAULT_MAX_COMPACT_FEATURE_SUMMARY_BYTES = 8_000_000
DEFAULT_LIST_SAMPLE_SIZE = 3
DEFAULT_MAX_DEPTH = 7
DEFAULT_MAX_STRING_CHARS = 20_000

COMPACT_SCHEMA_VERSION = "ml38.10.36.1"
COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY = (
    "COMPACT_ARCHIVE_MANIFEST_ONLY_LARGE_SIDECAR_STREAMS"
)
COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION = "ml38.10.72"
PREDICTION_SIDECAR_STREAM_MANIFEST_NAME = "prediction_sidecar_stream_manifest.json"
FULL_DATASET_PREDICTION_STREAM_NAME = "full_dataset_prediction_stream.jsonl"
FULL_DATASET_PREDICTION_STREAM_SUMMARY_NAME = (
    "full_dataset_prediction_stream_summary.json"
)
PREDICTION_PAYLOAD_SCHEMA_NAME = "prediction_payload_schema.json"

PREDICTION_SIDECAR_WHITELIST_PATHS = frozenset(
    {
        "prediction_payloads/full_dataset_prediction_stream.jsonl",
        "prediction_payloads/full_dataset_prediction_stream_summary.json",
        "prediction_payloads/prediction_payload_schema.json",
        "prediction_payloads/test_prediction_stream.jsonl",
    }
)


def is_prediction_sidecar_artifact_path(path: str) -> bool:
    normalized = str(path).replace("\\", "/").lstrip("./")
    return any(
        normalized == allowed or normalized.endswith("/" + allowed)
        for allowed in PREDICTION_SIDECAR_WHITELIST_PATHS
    )


def should_preserve_prediction_sidecar_artifact(path: str) -> bool:
    """Return true only for bounded, schema-backed prediction sidecars."""
    return is_prediction_sidecar_artifact_path(path)

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
    "read_only_test_only_mask_outcome_audit",
    "test_only_outcome_input_summary",
    "final_pass_label_prediction_distribution",
    "final_pass_confusion_matrix",
    "final_pass_directional_precision_board",
    "final_pass_probability_confidence_summary",
    "final_pass_profit_outcome_summary",
    "final_pass_sample_rows",
    "test_only_outcome_interpretation",
    "ml38_10_48_test_only_outcome_decision",
    "read_only_full_dataset_prediction_payload_capture_design_audit",
    "current_prediction_payload_inventory",
    "prediction_generation_path_trace",
    "current_artifact_gap_board",
    "required_full_dataset_prediction_stream_contract",
    "capture_point_options_board",
    "compact_profile_whitelist_design",
    "leakage_and_guardrail_contract",
    "implementation_plan",
    "ml38_10_49_payload_capture_design_decision",
    "full_dataset_prediction_sidecar_export_implementation",
    "ml38_10_50_sidecar_export_implementation_decision",
    "full_dataset_prediction_sidecar_wiring",
    "ml38_10_54_sidecar_quick_quality_wiring_decision",
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
    "read_only_test_only_mask_outcome_audit",
    "test_only_outcome_input_summary",
    "final_pass_label_prediction_distribution",
    "final_pass_confusion_matrix",
    "final_pass_directional_precision_board",
    "final_pass_probability_confidence_summary",
    "final_pass_profit_outcome_summary",
    "final_pass_sample_rows",
    "test_only_outcome_interpretation",
    "ml38_10_48_test_only_outcome_decision",
    "read_only_full_dataset_prediction_payload_capture_design_audit",
    "current_prediction_payload_inventory",
    "prediction_generation_path_trace",
    "current_artifact_gap_board",
    "required_full_dataset_prediction_stream_contract",
    "capture_point_options_board",
    "compact_profile_whitelist_design",
    "leakage_and_guardrail_contract",
    "implementation_plan",
    "ml38_10_49_payload_capture_design_decision",
    "full_dataset_prediction_sidecar_export_implementation",
    "ml38_10_50_sidecar_export_implementation_decision",
    "full_dataset_prediction_sidecar_wiring",
    "ml38_10_54_sidecar_quick_quality_wiring_decision",
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
    sidecar_streams_seen: int
    sidecar_streams_manifest_only: int
    original_size_bytes: int
    final_size_bytes: int
    final_archive_size_bytes: int
    saved_size_bytes: int
    files: list[CompactFileResult]
    sidecar_stream_manifests: list[dict[str, Any]]


class CompactArchivePrunerError(RuntimeError):
    """Raised when compact archive pruning cannot preserve an auditable contract."""


def is_prediction_sidecar_stream_omitted_from_compact_archive(
    path: str | Path,
    *,
    archive_root: str | Path | None = None,
) -> bool:
    """Return true only for streams with a valid ml38.10.72 manifest-only marker."""

    stream_path = Path(path)
    if stream_path.name != FULL_DATASET_PREDICTION_STREAM_NAME:
        return False
    manifest_path = stream_path.with_name(PREDICTION_SIDECAR_STREAM_MANIFEST_NAME)
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return False
    if manifest.get("policy_name") != COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY:
        return False
    if (
        manifest.get("omission_policy_version")
        != COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION
    ):
        return False
    if manifest.get("full_stream_in_compact_archive") is not False:
        return False
    if manifest.get("full_stream_available_in_output_dir") is not True:
        return False
    if manifest.get("stream_filename") != FULL_DATASET_PREDICTION_STREAM_NAME:
        return False
    if archive_root is not None:
        try:
            rel = stream_path.resolve().relative_to(Path(archive_root).resolve()).as_posix()
        except (OSError, ValueError):
            rel = None
        if rel and manifest.get("archive_relative_path") not in {None, rel}:
            return False
    return True


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
    if should_preserve_prediction_sidecar_artifact(str(path)):
        return CompactFileResult(
            path=str(path),
            compacted=False,
            original_size_bytes=original_size,
            final_size_bytes=original_size,
            saved_size_bytes=0,
            reason="prediction_sidecar_whitelist_byte_preserved",
        )
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


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_MANIFEST_INVALID_JSON: path={path}; error={type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_MANIFEST_NON_OBJECT_JSON: path={path}"
        )
    return payload


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_has_lf_only_contract(path: Path) -> bool:
    saw_bytes = False
    previous = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if chunk:
                saw_bytes = True
            if b"\r\n" in previous + chunk or b"\r" in chunk:
                return False
            previous = chunk[-1:] if chunk else previous
    if not saw_bytes:
        return True
    return previous == b"\n"


def _stream_paths(root: Path) -> list[Path]:
    return sorted(root.rglob(f"prediction_payloads/{FULL_DATASET_PREDICTION_STREAM_NAME}"))


def _archive_included_size_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if is_prediction_sidecar_stream_omitted_from_compact_archive(path):
            continue
        total += path.stat().st_size
    return total


def _build_prediction_sidecar_stream_manifest(
    root: Path,
    stream_path: Path,
    *,
    archive_relative_path: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    if not stream_path.is_file():
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_MISSING: path={stream_path}"
        )

    summary_path = stream_path.with_name(FULL_DATASET_PREDICTION_STREAM_SUMMARY_NAME)
    schema_path = stream_path.with_name(PREDICTION_PAYLOAD_SCHEMA_NAME)
    manifest_path = stream_path.with_name(PREDICTION_SIDECAR_STREAM_MANIFEST_NAME)
    if manifest_path.exists():
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_MANIFEST_DUPLICATE: path={manifest_path}"
        )
    if not summary_path.is_file():
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_SUMMARY_MISSING: stream={stream_path}; summary={summary_path}"
        )
    if not schema_path.is_file():
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_SCHEMA_MISSING: stream={stream_path}; schema={schema_path}"
        )

    summary = _read_json_object(summary_path)
    schema = _read_json_object(schema_path)
    stream_size = stream_path.stat().st_size
    stream_sha256 = _sha256_file(stream_path)

    expected_size = summary.get("size_bytes")
    if expected_size != stream_size:
        raise CompactArchivePrunerError(
            "COMPACT_ARCHIVE_SIDECAR_STREAM_SUMMARY_SIZE_MISMATCH: "
            f"stream={stream_path}; summary_size_bytes={expected_size!r}; actual_size_bytes={stream_size}"
        )
    expected_sha256 = summary.get("sha256")
    if expected_sha256 != stream_sha256:
        raise CompactArchivePrunerError(
            "COMPACT_ARCHIVE_SIDECAR_STREAM_SUMMARY_HASH_MISMATCH: "
            f"stream={stream_path}; summary_sha256={expected_sha256!r}; actual_sha256={stream_sha256}"
        )
    if not _stream_has_lf_only_contract(stream_path):
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_LF_ONLY_MISMATCH: stream={stream_path}"
        )

    row_count = summary.get("row_count", summary.get("expected_row_count"))
    if not isinstance(row_count, int) or row_count < 0:
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_ROW_COUNT_INVALID: stream={stream_path}; row_count={row_count!r}"
        )

    sidecar_schema_version = (
        summary.get("sidecar_schema_version")
        or summary.get("schema_version")
        or schema.get("schema_version")
    )
    prediction_field_contract_version = summary.get("prediction_field_contract_version")
    if not sidecar_schema_version:
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_SCHEMA_VERSION_MISSING: stream={stream_path}"
        )
    if not prediction_field_contract_version:
        raise CompactArchivePrunerError(
            f"COMPACT_ARCHIVE_SIDECAR_STREAM_FIELD_CONTRACT_VERSION_MISSING: stream={stream_path}"
        )

    root_relative_path = stream_path.relative_to(root).as_posix()
    manifest = {
        "schema_version": COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION,
        "policy_name": COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY,
        "omission_policy_version": COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION,
        "omission_reason": "compact archive size budget exceeded by full JSONL prediction sidecar stream",
        "root_relative_path": root_relative_path,
        "archive_relative_path": archive_relative_path,
        "stream_filename": FULL_DATASET_PREDICTION_STREAM_NAME,
        "original_stream_relative_path": root_relative_path,
        "summary_relative_path": summary_path.relative_to(root).as_posix(),
        "schema_relative_path": schema_path.relative_to(root).as_posix(),
        "manifest_relative_path": manifest_path.relative_to(root).as_posix(),
        "full_stream_in_compact_archive": False,
        "full_stream_available_in_output_dir": True,
        "sha256": stream_sha256,
        "size_bytes": stream_size,
        "row_count": row_count,
        "sidecar_schema_version": sidecar_schema_version,
        "prediction_field_contract_version": prediction_field_contract_version,
        "line_ending_contract": summary.get("line_ending_contract"),
        "lf_only": True,
        "summary_hash_verified": True,
        "summary_size_verified": True,
        "summary_hash_contract": summary.get("hash_contract"),
        "summary_byte_size_contract": summary.get("byte_size_contract"),
        "summary_validation_status": summary.get("validation_status"),
        "summary_path": summary_path.name,
        "schema_path": schema_path.name,
        "manifest_note": "Full JSONL stream remains on disk but is intentionally omitted from compact archive members.",
    }
    return manifest_path, manifest


def compact_staged_symbol_output(
    root: Path,
    *,
    max_training_report_bytes: int = DEFAULT_MAX_COMPACT_TRAINING_REPORT_BYTES,
    max_feature_summary_bytes: int = DEFAULT_MAX_COMPACT_FEATURE_SUMMARY_BYTES,
    max_archive_stage_bytes: int | None = None,
    archive_root: Path | None = None,
) -> CompactArchivePruneResult:
    root = Path(root)
    archive_root = Path(archive_root) if archive_root is not None else root
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

    sidecar_streams = _stream_paths(root)
    sidecar_stream_manifests: list[dict[str, Any]] = []
    manifest_plans: list[tuple[Path, dict[str, Any]]] = []
    manifest_bytes: list[tuple[Path, dict[str, Any], bytes]] = []
    if max_archive_stage_bytes is not None:
        archive_size_before_manifest_only = _archive_included_size_bytes(root)
        if archive_size_before_manifest_only > max_archive_stage_bytes:
            for summary_path in sorted(
                root.rglob(
                    f"prediction_payloads/{FULL_DATASET_PREDICTION_STREAM_SUMMARY_NAME}"
                )
            ):
                expected_stream = summary_path.with_name(
                    FULL_DATASET_PREDICTION_STREAM_NAME
                )
                if not expected_stream.is_file():
                    raise CompactArchivePrunerError(
                        "COMPACT_ARCHIVE_SIDECAR_STREAM_MISSING: "
                        f"summary={summary_path}; expected_stream={expected_stream}"
                    )
            for stream_path in sidecar_streams:
                try:
                    archive_relative_path = (
                        stream_path.resolve()
                        .relative_to(archive_root.resolve())
                        .as_posix()
                    )
                except (OSError, ValueError):
                    archive_relative_path = None
                manifest_plans.append(
                    _build_prediction_sidecar_stream_manifest(
                        root,
                        stream_path,
                        archive_relative_path=archive_relative_path,
                    )
                )

    if manifest_plans:
        manifest_bytes = [
            (
                manifest_path,
                manifest,
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
            )
            for manifest_path, manifest in manifest_plans
        ]
        manifest_size_bytes = sum(len(payload) for _, _, payload in manifest_bytes)
        final_archive_size_bytes = (
            archive_size_before_manifest_only
            - sum(stream_path.stat().st_size for stream_path in sidecar_streams)
            + manifest_size_bytes
        )
    else:
        final_archive_size_bytes = _archive_included_size_bytes(root)
    if (
        max_archive_stage_bytes is not None
        and final_archive_size_bytes > max_archive_stage_bytes
    ):
        omitted_streams = (
            {path.resolve() for path in sidecar_streams} if manifest_plans else set()
        )
        largest = sorted(
            (
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                }
                for path in root.rglob("*")
                if path.is_file()
                and path.resolve() not in omitted_streams
                and not is_prediction_sidecar_stream_omitted_from_compact_archive(path)
            ),
            key=lambda item: (-int(item["size_bytes"]), str(item["path"])),
        )[:20]
        raise CompactArchivePrunerError(
            "COMPACT_ARCHIVE_MANIFEST_ONLY_STAGE_SIZE_CAP_EXCEEDED: "
            f"root={root}; final_archive_size_bytes={final_archive_size_bytes}; "
            f"max_archive_stage_bytes={max_archive_stage_bytes}; largest_files={largest}"
        )

    for manifest_path, manifest, payload in manifest_bytes:
        manifest_path.write_bytes(payload)
        sidecar_stream_manifests.append(manifest)
    if manifest_plans:
        final_archive_size_bytes = _archive_included_size_bytes(root)

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
        sidecar_streams_seen=len(sidecar_streams),
        sidecar_streams_manifest_only=len(sidecar_stream_manifests),
        original_size_bytes=sum(result.original_size_bytes for result in file_results),
        final_size_bytes=sum(result.final_size_bytes for result in file_results),
        final_archive_size_bytes=final_archive_size_bytes,
        saved_size_bytes=sum(result.saved_size_bytes for result in file_results),
        files=file_results,
        sidecar_stream_manifests=sidecar_stream_manifests,
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
