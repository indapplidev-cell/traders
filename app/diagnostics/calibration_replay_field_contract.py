"""ML38.10.68 diagnostic contract for a future row-aligned calibration replay.

This module is deliberately pure: it reads no artifacts, writes nothing, and does
not import the training runtime.  The constants below record source discovery;
the helpers exercise the proposed fail-closed contract with synthetic rows.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


DIAGNOSTIC_NAME = "calibration_replay_field_contract"
DIAGNOSTIC_VERSION = "ml38.10.68"
EXECUTION_MODE = "DIAGNOSTIC_FIELD_CONTRACT_NO_TRAINING_NO_RERUN"
LABELS = ("DOWN", "FLAT", "UP")

RAW_FIELDS = ("raw_prob_down", "raw_prob_flat", "raw_prob_up")
CALIBRATED_FIELDS = (
    "calibrated_prob_down",
    "calibrated_prob_flat",
    "calibrated_prob_up",
)
ALIGNMENT_FIELDS = ("row_alignment_key",)
FOLD_PROFIT_FIELDS = ("fold_id", "profit_join_key")


def _all_rows_have(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bool:
    return bool(rows) and all(
        all(row.get(field) is not None and row.get(field) != "" for field in fields)
        for row in rows
    )


def classify_replay_payload(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify replay capability and fail closed when row identity is incomplete."""
    has_calibrated = _all_rows_have(rows, CALIBRATED_FIELDS)
    has_raw = _all_rows_have(rows, RAW_FIELDS)
    has_actual = _all_rows_have(rows, ("actual_label",))
    has_alignment = _all_rows_have(rows, ALIGNMENT_FIELDS)
    has_fold_profit = _all_rows_have(rows, FOLD_PROFIT_FIELDS)
    outcome = has_calibrated and has_actual and has_alignment
    full = outcome and has_raw
    return {
        "distribution_replay_supported": has_calibrated,
        "outcome_aware_replay_supported": outcome,
        "raw_vs_calibrated_replay_supported": full,
        "safe_external_join_supported": has_alignment,
        "fold_profit_ranking_supported": outcome and has_fold_profit,
        "status": (
            "COMPLETE_FOR_FULL_CALIBRATION_REPLAY"
            if full
            else "INCOMPLETE_FOR_OUTCOME_AWARE_REPLAY"
            if not outcome
            else "INCOMPLETE_FOR_RAW_VS_CALIBRATED_REPLAY"
        ),
        "blocking_fields": {
            "raw_probabilities": not has_raw,
            "actual_label": not has_actual,
            "alignment_key": not has_alignment,
            "fold_profit_keys": not has_fold_profit,
        },
    }


def compute_outcome_metrics(
    rows: Sequence[Mapping[str, Any]], *, predicted_field: str = "current_predicted_label"
) -> dict[str, float]:
    """Compute basic synthetic replay metrics after enforcing row alignment."""
    capability = classify_replay_payload(rows)
    if not capability["outcome_aware_replay_supported"]:
        raise ValueError("actual_label, row_alignment_key, and calibrated probabilities are required")
    if not _all_rows_have(rows, (predicted_field,)):
        raise ValueError(f"{predicted_field} is required")
    actual = [str(row["actual_label"]).upper() for row in rows]
    predicted = [str(row[predicted_field]).upper() for row in rows]
    count = len(rows)
    accuracy = sum(a == p for a, p in zip(actual, predicted)) / count
    majority = max(Counter(actual).values()) / count
    actual_flat = sum(label == "FLAT" for label in actual)
    true_flat = sum(a == p == "FLAT" for a, p in zip(actual, predicted))
    false_directional = sum(a == "FLAT" and p in {"DOWN", "UP"} for a, p in zip(actual, predicted))
    return {
        "accuracy": accuracy,
        "majority_baseline_accuracy": majority,
        "accuracy_edge": accuracy - majority,
        "flat_recall": true_flat / actual_flat if actual_flat else 0.0,
        "false_directional_on_actual_flat": float(false_directional),
    }


def _field(
    name: str,
    required_for: str,
    present: bool,
    available: bool | str,
    location: str,
    fail_closed: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "field_name": name,
        "required_for": required_for,
        "currently_present": present,
        "source_available_now": available,
        "source_location": location,
        "fail_closed_if_missing": fail_closed,
        "reason": reason,
    }


_WIRING = "app/experiments/prediction_sidecar_wiring.py:build_full_dataset_prediction_sidecar_rows"
_SERVICE = "app/training/training_service.py:TrainingService.train"
_EXPORTER = "app/experiments/prediction_sidecar_exporter.py"

_FIELDS = [
    _field("candidate_id", "candidate identity", True, True, _WIRING, True, "prevents cross-candidate joins"),
    _field("symbol", "dataset identity", True, True, _WIRING, True, "prevents cross-symbol joins"),
    _field("interval", "dataset identity", True, True, _WIRING, True, "prevents cross-interval joins"),
    _field("horizon", "dataset identity", True, True, "horizon_candles in " + _WIRING, True, "labels depend on horizon"),
    _field("split", "split-aware replay", True, True, "split_name in " + _WIRING, True, "prevents split leakage"),
    _field("row_index_global", "stable row order", True, True, "dataset_row_index in " + _WIRING, True, "detects missing or reordered rows"),
    _field("row_index_split", "split-local order", True, True, "split_row_index in " + _WIRING, True, "checks split alignment"),
    _field("timestamp or candle_open_time", "temporal alignment", True, True, "source_row.candle_open_time in " + _WIRING, True, "primary temporal join component"),
    _field("actual_label", "outcome-aware ranking", False, True, "source_row.direction_label available in " + _WIRING, True, "required for correctness metrics"),
    _field("current_predicted_label", "current layer replay", False, "UNKNOWN", "downstream aggregate metrics; row-level source not wired to sidecar", True, "must identify current evaluated prediction explicitly"),
    _field("sidecar_argmax_label", "sidecar layer replay", True, True, "predicted_label in " + _WIRING, True, "separates softmax argmax from downstream policy"),
    _field("downstream_policy_predicted_label", "downstream comparison", False, "UNKNOWN", "Evaluator/TrainingMetrics policy path; no row field exported", False, "optional explicit policy layer"),
    _field("raw_prob_down", "raw-vs-calibrated replay", False, True, "direction_logits + softmax_with_temperature(..., 1.0) in " + _SERVICE, True, "raw DOWN probability"),
    _field("raw_prob_flat", "raw-vs-calibrated replay", False, True, "direction_logits + softmax_with_temperature(..., 1.0) in " + _SERVICE, True, "raw FLAT probability"),
    _field("raw_prob_up", "raw-vs-calibrated replay", False, True, "direction_logits + softmax_with_temperature(..., 1.0) in " + _SERVICE, True, "raw UP probability"),
    _field("calibrated_prob_down", "calibrated replay", True, True, "prob_down from temperature-scaled logits in " + _SERVICE, True, "calibrated DOWN probability"),
    _field("calibrated_prob_flat", "calibrated replay", True, True, "prob_flat from temperature-scaled logits in " + _SERVICE, True, "calibrated FLAT probability"),
    _field("calibrated_prob_up", "calibrated replay", True, True, "prob_up from temperature-scaled logits in " + _SERVICE, True, "calibrated UP probability"),
    _field("selected_probability_source", "probability provenance", False, True, "prediction_source_stage in " + _WIRING, True, "prevents raw/calibrated ambiguity"),
    _field("policy_predicted_label", "policy rerank", False, "UNKNOWN", "future replay-derived field", False, "optional replay output"),
    _field("fold_id", "walk-forward ranking", False, "UNKNOWN", "not present in TrainingService sidecar export boundary", False, "optional for basic accuracy, required for folds"),
    _field("profit_join_key", "profit-risk ranking", False, "UNKNOWN", "not present in TrainingService sidecar export boundary", False, "optional for basic accuracy, required for profit join"),
    _field("schema_version", "contract compatibility", False, True, "sidecar artifact schema in " + _EXPORTER, True, "row contract must be versioned"),
    _field("sidecar_writer_version", "writer provenance", False, True, "WRITER_CONTRACT_VERSION in " + _EXPORTER, True, "writer semantics must be traceable"),
    _field("row_alignment_key", "safe row join", True, True, "symbol+interval+candle_open_time and dataset_row_index in " + _WIRING, True, "must be unique and stable"),
]


def _synthetic_rows() -> list[dict[str, Any]]:
    values = [
        ("FLAT", "FLAT", (0.20, 0.60, 0.20), (0.15, 0.70, 0.15)),
        ("UP", "UP", (0.20, 0.10, 0.70), (0.15, 0.10, 0.75)),
        ("DOWN", "FLAT", (0.65, 0.20, 0.15), (0.55, 0.30, 0.15)),
    ]
    rows: list[dict[str, Any]] = []
    for index, (actual, predicted, raw, calibrated) in enumerate(values):
        rows.append({
            "row_alignment_key": f"SOLUSDT:15m:{index}",
            "actual_label": actual,
            "current_predicted_label": predicted,
            "raw_prob_down": raw[0], "raw_prob_flat": raw[1], "raw_prob_up": raw[2],
            "calibrated_prob_down": calibrated[0],
            "calibrated_prob_flat": calibrated[1],
            "calibrated_prob_up": calibrated[2],
            "fold_id": "fold-0", "profit_join_key": f"profit:{index}",
        })
    return rows


_COMPLETE_SYNTHETIC = _synthetic_rows()
_COMPLETE_METRICS = compute_outcome_metrics(_COMPLETE_SYNTHETIC)

calibration_replay_field_contract: dict[str, Any] = {
    "diagnostic_name": DIAGNOSTIC_NAME,
    "diagnostic_version": DIAGNOSTIC_VERSION,
    "execution_mode": EXECUTION_MODE,
    "previous_stage_summary": {
        "previous_stage": "ML38.10.67",
        "previous_commit": "2afaab2c0b4c572d79dbbfe4e7bdbc358f077a21",
        "previous_decision": "CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS",
        "sidecars_valid": 45, "policies_tested": 19, "replay_pairs": 855,
        "calibrated_fields_found": True, "raw_probabilities_found": False,
        "row_level_actual_labels_found": False, "distribution_replay_possible": True,
        "outcome_ranking_complete": False,
        "main_blocker": "class-prior/class-balance mismatch",
        "thresholding_effect": "helps but insufficient",
        "next_action": "CALIBRATION_REPLAY_INCOMPLETE_NEEDS_FIELDS",
    },
    "source_discovery": {
        "sidecar_stream_writer_file": _EXPORTER,
        "sidecar_stream_writer_function": "write_prediction_sidecar_artifacts",
        "sidecar_summary_writer_file": _EXPORTER,
        "sidecar_summary_writer_function": "build_prediction_sidecar_summary / write_prediction_sidecar_artifacts",
        "sidecar_schema_writer_file": _EXPORTER,
        "sidecar_schema_writer_function": "build_prediction_payload_schema / write_prediction_sidecar_artifacts",
        "expected_row_count_source_file": "app/training/training_pipeline_runner.py; app/training/training_service.py; " + _EXPORTER,
        "expected_row_count_symbol_or_field": "TrainingPipelineConfig.prediction_sidecar_expected_row_count; FULL_DATASET_ROW_COUNT",
        "expected_row_count_current_behavior": "hardcoded/global 6481 forwarded unchanged and enforced for FULL_DATASET_6481",
        "candidate_boundary_source_file": "app/training/training_service.py",
        "candidate_boundary_source_function_or_field": "TrainingService.train: dataset_rows -> DatasetBuilder.split_rows -> split_rows lengths",
        "calibrated_probability_source_found": True,
        "calibrated_probability_source_file": "app/training/training_service.py",
        "calibrated_probability_source_symbol_or_field": "direction_logits -> softmax_with_temperature(direction_temperature) -> split_probabilities",
        "raw_probability_source_found": True,
        "raw_probability_source_file_or_candidate": "app/training/training_service.py; app/training/probability_calibration.py",
        "raw_probability_source_symbol_or_candidate": "direction_logits -> softmax_with_temperature(temperature=1.0)",
        "actual_label_source_found": True,
        "actual_label_source_file_or_candidate": "app/training/training_service.py; app/experiments/prediction_sidecar_wiring.py",
        "actual_label_source_symbol_or_candidate": "split_rows source_row.direction_label",
        "row_alignment_key_source_found": True,
        "row_alignment_key_candidates": ["timestamp", "row_index", "dataset_index", "candle_open_time", "split local index", "symbol+interval+candle_open_time"],
        "fold_profit_join_key_source_found": "UNKNOWN",
        "fold_profit_join_key_candidates": ["fold_id", "candle_open_time", "symbol+interval+candle_open_time", "profit_join_key"],
        "source_discovery_confidence": "HIGH",
    },
    "prediction_layer_mapping": {
        "source_layer_warning": "The ML38.10.66 current distribution is downstream policy output; the sidecar stores calibrated softmax argmax (532/15/426), so they must not be conflated.",
        "downstream_policy_output_distribution": {"DOWN": 472, "FLAT": 109, "UP": 392},
        "sidecar_stored_calibrated_softmax_argmax_distribution": {"DOWN": 532, "FLAT": 15, "UP": 426},
        "best_distribution_only_policy_distribution": {"DOWN": 281, "FLAT": 400, "UP": 292},
        "best_distribution_only_policy_name": "directional_confidence_floor",
        "best_distribution_only_policy_threshold": 0.60,
        "best_distribution_only_policy_should_be_implemented_next": False,
        "reason_not_to_implement": "row-level correctness, directional recall, fold sensitivity, and profit/risk metrics are unavailable",
        "layer_mapping_confidence": "HIGH",
    },
    "current_sidecar_field_status": {
        "existing_real_sidecars_scanned": True, "sidecar_sets_checked": 45,
        "current_compact_sidecar_has_calibrated_probabilities": True,
        "current_compact_sidecar_has_raw_probabilities": False,
        "current_compact_sidecar_has_row_level_actual_label": False,
        "current_compact_sidecar_has_split": True,
        "current_compact_sidecar_has_timestamp_or_row_id": True,
        "current_compact_sidecar_has_candidate_id": True,
        "current_compact_sidecar_has_alignment_key": True,
        "current_compact_sidecar_has_fold_id": False,
        "current_compact_sidecar_has_profit_join_key": False,
        "current_compact_sidecar_supports_distribution_replay": True,
        "current_compact_sidecar_supports_outcome_ranking": False,
        "current_compact_sidecar_supports_raw_vs_calibrated_replay": False,
        "current_compact_sidecar_supports_fold_profit_join": False,
        "compact_sidecar_status": "INCOMPLETE_FOR_OUTCOME_AWARE_REPLAY",
        "existing_artifacts_mutated": False,
    },
    "required_row_alignment_contract": {"fields": _FIELDS},
    "missing_field_impact": {
        "missing_raw_probabilities": {"impact": "cannot compare raw vs calibrated or identify calibration method effect", "blocks": ["raw_vs_calibrated_replay", "calibration_method_effect_diagnosis"]},
        "missing_row_level_actual_label": {"impact": "cannot recompute accuracy/baseline edge/FLAT recall/false directional/outcome ranking", "blocks": ["accuracy_edge_replay", "baseline_edge_replay", "FLAT_recall", "false_directional_on_actual_FLAT", "outcome_policy_ranking"]},
        "missing_alignment_key": {"impact": "cannot safely join labels/profit/folds", "blocks": ["label_join", "fold_join", "profit_join", "timestamp_traceability"]},
        "missing_fold_profit_keys": {"impact": "cannot rerank by walk-forward/profit-risk", "blocks": ["walk_forward_policy_ranking", "profit_risk_policy_ranking"]},
        "prediction_layer_conflation_risk": {"impact": "downstream policy output and sidecar argmax can be mixed incorrectly unless explicitly separated"},
        "conclusion": "distribution-only replay is insufficient for selecting production policy",
    },
    "synthetic_replay_contract": {
        "complete_payload_replay_supported": classify_replay_payload(_COMPLETE_SYNTHETIC)["outcome_aware_replay_supported"],
        "complete_payload_metrics_available": ["accuracy", "majority_baseline_accuracy", "accuracy_edge", "flat_recall", "false_directional_on_actual_flat", "raw_vs_calibrated_comparison"],
        "complete_payload_example_metrics": _COMPLETE_METRICS,
        "missing_raw_blocks_raw_calibration_comparison": True,
        "missing_actual_blocks_outcome_ranking": True,
        "missing_alignment_key_blocks_safe_join": True,
        "missing_fold_profit_keys_blocks_fold_profit_ranking": True,
        "compact_sidecar_classified_incomplete": True,
        "distribution_only_payload_not_enough_for_production_policy": True,
    },
    "h08_scope_boundary": {
        "h08_diagnosed_in_ml38_10_67": True,
        "h08_failed_candidate_id": "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
        "h08_candidate_boundary_train": 4539, "h08_candidate_boundary_val": 973,
        "h08_candidate_boundary_test": 973, "h08_candidate_boundary_total": 6485,
        "h08_expected_global_denominator": 6481, "h08_delta_rows": 4,
        "h08_fix_applied_in_ml38_10_68": False,
        "h08_reason_to_keep_separate": "denominator fix is candidate-boundary contract, not calibration field contract",
        "recommended_h08_stage": "separate ML38.10.69 or later if prioritized",
    },
    "implementation_recommendation": {
        "recommended_stage": "ML38.10.69",
        "action_type": "SIDECAR_FIELD_CONTRACT_IMPLEMENTATION",
        "action_summary": "Add versioned raw/calibrated probability, actual-label, explicit prediction-layer, and stable row-alignment fields at the TrainingService-to-sidecar wiring boundary with fail-closed validation; keep fold/profit keys optional until their row-level source is proven.",
        "expected_files_to_touch": ["app/training/training_service.py", "app/experiments/prediction_sidecar_wiring.py", "app/experiments/prediction_sidecar_exporter.py", "targeted sidecar contract tests"],
        "expected_tests": ["complete row payload", "missing raw", "missing actual", "missing alignment", "schema/version and duplicate alignment checks"],
        "requires_real_training_run_after_implementation": True,
        "requires_wrapper_rerun_after_implementation": True,
        "expected_next_real_run_scope": "one SOLUSDT quick-quality wrapper rerun only after field contract implementation and full pytest, if implementation changes export output",
        "h08_scope": "keep separately scoped unless action_type is H08_DENOMINATOR_FIX_FIRST",
        "cascade_outcome_still_blocked": True, "tradable_edge_still_blocked": True,
    },
    "guardrails": {
        "quick_quality_rerun_during_stage": False, "wrapper_execute_used_during_stage": False,
        "training_or_runtime_executed_during_stage": False, "db_writes_during_stage": False,
        "ml_labels_writes_during_stage": False, "ml_predictions_writes_during_stage": False,
        "labels_builders_gates_model_logic_changed": False, "class_weights_changed": False,
        "training_objective_changed": False, "production_calibration_logic_changed": False,
        "directional_confidence_floor_implemented": False, "flat_override_implemented": False,
        "sidecar_export_production_logic_changed": False, "existing_real_artifacts_mutated": False,
        "new_real_sidecars_created": False, "new_zip_created": False,
        "archive_recovery_performed": False, "cascade_outcome_run": False,
        "production_like_recompute": False, "tradable_edge_confirmed": False,
    },
    "decision_gate": {
        "field_contract_diagnostic_completed": True, "source_locations_identified": True,
        "prediction_layers_disambiguated": True, "required_fields_defined": True,
        "synthetic_contract_tests_added": True, "production_sidecar_field_change_applied": False,
        "production_calibration_policy_applied": False, "directional_confidence_floor_applied": False,
        "h08_fix_applied": False, "rerun_performed": False, "artifacts_mutated": False,
        "next_action_selected": True, "cascade_outcome_allowed_now": False,
        "production_like_recompute_allowed_now": False, "tradable_edge_claim_allowed_now": False,
        "decision": "FIELD_CONTRACT_DIAGNOSTIC_COMPLETED_NEXT_ACTION_SELECTED",
        "next_allowed_stage": "ML38.10.69 — SIDECAR_FIELD_CONTRACT_IMPLEMENTATION",
    },
    "next_step_plan": [
        "Implement the minimal versioned row field contract in ML38.10.69.",
        "Add fail-closed completeness, probability, unique-alignment, and prediction-layer checks.",
        "Keep h08 denominator correction separately scoped.",
        "Require full pytest approval before any separately approved SOLUSDT rerun.",
    ],
    "decision": [
        "FIELD_CONTRACT_DIAGNOSTIC_COMPLETED_NEXT_ACTION_SELECTED",
        "ML38.10.69_SIDECAR_FIELD_CONTRACT_IMPLEMENTATION",
        "NO_TRAINING_NO_RERUN_NO_ARTIFACT_MUTATION",
        "DISTRIBUTION_ONLY_REPLAY_CANNOT_AUTHORIZE_PRODUCTION_POLICY",
    ],
}

