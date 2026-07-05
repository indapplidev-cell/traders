from __future__ import annotations

from typing import Any, Mapping, Sequence


DIAGNOSTIC_NAME = "read_only_full_dataset_prediction_payload_capture_design_audit"
DIAGNOSTIC_VERSION = "ml38.10.49"
EXECUTION_MODE = "READ_ONLY_DESIGN_ONLY_NO_TRAINING_NO_DB_WRITES"
REFERENCE_CONFIG_ID = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_"
    "rguard_long_bad_dates_exit45_probe"
)

# Confirmed ML38.10.48 snapshot denominators. Builders accept overrides so tests and
# future audits can supply evidence without depending on a database or runtime run.
CONFIRMED_TEST_PREDICTION_ROWS = 973
CONFIRMED_FULL_DATASET_FEATURE_ROWS = 6481


def _source(
    source_name: str,
    path_or_block: str,
    row_count: int,
    *,
    has_timestamp: bool,
    has_predicted_label: bool,
    has_probabilities: bool,
    has_split_name: bool,
    denominator_scope: str,
    usable_for_test_only: bool,
    usable_for_full_dataset: bool,
    reason_if_not_full_dataset: str,
) -> dict[str, Any]:
    return {
        "source_name": source_name,
        "path_or_block": path_or_block,
        "row_count": row_count,
        "has_timestamp": has_timestamp,
        "has_predicted_label": has_predicted_label,
        "has_probabilities": has_probabilities,
        "has_split_name": has_split_name,
        "denominator_scope": denominator_scope,
        "usable_for_test_only": usable_for_test_only,
        "usable_for_full_dataset": usable_for_full_dataset,
        "reason_if_not_full_dataset": reason_if_not_full_dataset,
    }


def build_current_prediction_payload_inventory(
    *,
    probability_payload_path: str | None = None,
    candidate_result_path: str | None = None,
    source_zip_path: str | None = None,
    discovered_prediction_sources: Sequence[Mapping[str, Any]] | None = None,
    test_prediction_rows_found: int = CONFIRMED_TEST_PREDICTION_ROWS,
    dataset_prediction_rows_found: int = 0,
    full_dataset_feature_rows: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS,
    split_total_rows: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS,
    ml_predictions_rows_found: int = 0,
) -> dict[str, Any]:
    sources = list(discovered_prediction_sources or [])
    if not sources:
        sources = [
            _source(
                "calibrated_decision_diagnostics.calibrated_rows",
                "probability_payload.calibrated_decision_diagnostics.calibrated_rows",
                test_prediction_rows_found,
                has_timestamp=True,
                has_predicted_label=True,
                has_probabilities=True,
                has_split_name=False,
                denominator_scope=f"TEST_ONLY_{test_prediction_rows_found}",
                usable_for_test_only=test_prediction_rows_found > 0,
                usable_for_full_dataset=False,
                reason_if_not_full_dataset="test denominator only; train/validation rows absent",
            ),
            _source(
                "calibrated_decision_diagnostics.selected_rows",
                "probability_payload.calibrated_decision_diagnostics.selected_rows",
                test_prediction_rows_found,
                has_timestamp=True,
                has_predicted_label=True,
                has_probabilities=True,
                has_split_name=False,
                denominator_scope=f"TEST_ONLY_{test_prediction_rows_found}",
                usable_for_test_only=test_prediction_rows_found > 0,
                usable_for_full_dataset=False,
                reason_if_not_full_dataset="test denominator only; train/validation rows absent",
            ),
            _source(
                "selected_predictions",
                "bounded_calibrated_decision_selection.selected_predictions",
                test_prediction_rows_found,
                has_timestamp=False,
                has_predicted_label=True,
                has_probabilities=False,
                has_split_name=False,
                denominator_scope=f"TEST_ONLY_{test_prediction_rows_found}_AGGREGATE",
                usable_for_test_only=False,
                usable_for_full_dataset=False,
                reason_if_not_full_dataset="aggregate-only labels have no timestamp join key",
            ),
            _source(
                "compact_archive_candidate_result",
                "quick-quality ZIP!/candidate_results/<candidate>.json",
                test_prediction_rows_found,
                has_timestamp=False,
                has_predicted_label=False,
                has_probabilities=False,
                has_split_name=False,
                denominator_scope="COMPACT_PROFILE_OMISSION_MARKER",
                usable_for_test_only=False,
                usable_for_full_dataset=False,
                reason_if_not_full_dataset="row payloads omitted by compact profile",
            ),
            _source(
                "ml_predictions",
                "ml_predictions table (prior read-only audit evidence)",
                ml_predictions_rows_found,
                has_timestamp=False,
                has_predicted_label=False,
                has_probabilities=False,
                has_split_name=False,
                denominator_scope="NO_MATCHING_ROWS",
                usable_for_test_only=False,
                usable_for_full_dataset=False,
                reason_if_not_full_dataset="table source exists but candidate rows were not found",
            ),
        ]
    denominators = sorted(
        {str(row.get("denominator_scope")) for row in sources if row.get("denominator_scope")}
    )
    full_ready = dataset_prediction_rows_found == split_total_rows and split_total_rows > 0
    return {
        "probability_payload_path": probability_payload_path,
        "candidate_result_path": candidate_result_path,
        "source_zip_path": source_zip_path,
        "discovered_prediction_sources": [dict(row) for row in sources],
        "test_prediction_rows_found": test_prediction_rows_found,
        "dataset_prediction_rows_found": dataset_prediction_rows_found,
        "full_dataset_feature_rows": full_dataset_feature_rows,
        "split_total_rows": split_total_rows,
        "payload_denominators_found": denominators,
        "timestamp_key_status": (
            "TIMESTAMP_KEY_AVAILABLE_FOR_TEST_ONLY"
            if test_prediction_rows_found and not full_ready
            else "FULL_DATASET_TIMESTAMP_KEY_READY" if full_ready else "TIMESTAMP_KEY_MISSING"
        ),
        "current_status": (
            "FULL_DATASET_PREDICTION_STREAM_AVAILABLE"
            if full_ready
            else "BLOCKED_FULL_DATASET_PREDICTION_STREAM_MISSING"
        ),
    }


def _trace_candidate(
    file: str,
    function_or_class: str,
    role: str,
    current_payload_scope: str,
    can_emit_timestamped_rows: bool,
    risk_of_leakage: str,
    notes: str,
) -> dict[str, Any]:
    return locals()


def build_prediction_generation_path_trace() -> dict[str, Any]:
    return {
        "model_inference_stage_candidates": [
            _trace_candidate(
                "app/training/training_service.py", "TrainingService.train",
                "build split tensors and evaluate model outputs", "train/validation/test metrics",
                True, "LOW_IF_FEATURE_ROWS_ONLY", "Full split rows exist here; no capture is added in ML38.10.49.",
            ),
            _trace_candidate(
                "app/training/training_service.py", "TrainingService.evaluate",
                "load model and evaluate dataset test split", "test metrics", True,
                "LOW_IF_TARGETS_STAY_SEPARATE", "Current evaluation path explicitly selects split_rows['test'].",
            ),
        ],
        "probability_calibration_stage_candidates": [
            _trace_candidate(
                "app/training/training_service.py", "fit_direction_temperature_for_model",
                "fit validation temperature and apply calibrated evaluation", "split metrics",
                True, "MEDIUM_VALIDATION_TARGETS_USED_FOR_FIT",
                "Calibration metadata must identify its validation-only fit scope.",
            ),
        ],
        "decision_selection_stage_candidates": [
            _trace_candidate(
                "app/training/metrics.py", "TrainingMetrics.compute",
                "derive predicted classes and decision-mask diagnostics", "metric payload",
                False, "MEDIUM_IF_TARGET_ARRAY_REUSED", "Row identity is not preserved by aggregate metrics.",
            ),
        ],
        "evaluator_payload_stage_candidates": [
            _trace_candidate(
                "app/evaluation/profit_aware_evaluator_v2.py", "ProfitAwareEvaluatorV2.evaluate_predictions",
                "consume prediction rows for gate and profit evaluation", "provided prediction list",
                True, "HIGH_IF_ACTUAL_LABEL_IS_RENAMED", "Suitable only when prediction provenance is explicit.",
            ),
        ],
        "artifact_writer_stage_candidates": [
            _trace_candidate(
                "app/experiments/feature_regime_experiment_reporter.py", "write_candidate_json",
                "persist candidate artifacts", "candidate result", True, "LOW",
                "Preferred future boundary for a separate JSONL sidecar exporter.",
            ),
        ],
        "compact_pruning_stage_candidates": [
            _trace_candidate(
                "app/experiments/compact_archive_pruner.py", "compact_json_value",
                "replace heavy row arrays and long lists with omission markers", "compact archive",
                False, "LOW", "Future sidecars require an explicit archive-path whitelist.",
            ),
        ],
        "likely_missing_capture_point": (
            "after calibrated all-split decision selection and before candidate artifact compaction"
        ),
        "trace_status": "CODE_PATH_DESIGN_TRACE_ONLY_NO_RUNTIME_EXECUTION",
    }


def build_current_artifact_gap_board(
    inventory: Mapping[str, Any], *, profit_outcome_rows_found: int = 0
) -> list[dict[str, Any]]:
    full_rows = int(inventory.get("full_dataset_feature_rows") or 0)
    test_rows = int(inventory.get("test_prediction_rows_found") or 0)
    dataset_rows = int(inventory.get("dataset_prediction_rows_found") or 0)
    specs = [
        ("full_dataset_feature_rows_vs_test_prediction_rows", full_rows, test_rows,
         "prediction denominator does not cover the dataset", "full 6481 cascade/outcome", "capture/export", "CRITICAL"),
        ("timestamp_key_available_only_for_test_predictions", "6481 timestamped rows", f"{test_rows} timestamped test rows",
         "train/validation cannot be joined", "full-dataset join", "capture/export", "CRITICAL"),
        ("compact_profile_omits_prediction_payloads", "whitelisted prediction sidecars", "row payload omission markers",
         "archive cannot recover row stream", "reproducible audit", "compact whitelist", "HIGH"),
        ("full_uncompressed_candidate_result_not_found_or_not_packaged", "packaged full payload", "not found or not packaged",
         "no non-compact recovery source", "full-dataset audit", "artifact packaging", "HIGH"),
        ("ml_predictions_table_not_populated_for_candidate", full_rows, dataset_rows,
         "database cannot supply candidate predictions", "database recovery", "optional later DB persistence", "HIGH"),
        ("profit_outcome_rows_missing", "explicit per-row profit outcomes", profit_outcome_rows_found,
         "profit conclusions are invalid", "profit outcome audit", "separate outcome capture", "HIGH"),
    ]
    return [
        {
            "gap_name": name, "expected": expected, "observed": observed,
            "impact": impact, "blocker_for": blocker, "required_fix_type": fix,
            "severity": severity, "status": "OPEN",
        }
        for name, expected, observed, impact, blocker, fix, severity in specs
    ]


def build_required_full_dataset_prediction_stream_contract(
    *, required_row_count: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS
) -> dict[str, Any]:
    return {
        "contract_name": "full_dataset_timestamp_keyed_prediction_stream_v1",
        "denominator_scope": f"FULL_DATASET_{required_row_count}",
        "required_row_count": required_row_count,
        "required_join_key": "symbol+interval+candle_open_time",
        "required_identity_fields": ["symbol", "interval", "candle_open_time", "dataset_row_index or row_id", "split_name", "feature_version", "label_version", "horizon_candles", "config_id"],
        "required_prediction_fields": ["predicted_label", "original_predicted_label, if different", "calibrated_predicted_label, if applicable", "prediction_source_stage"],
        "required_probability_fields": ["prob_up", "prob_down", "prob_flat", "confidence"],
        "required_split_fields": ["split_name", "split_row_index", "split_total_rows"],
        "required_model_fields": ["model_name", "model_version", "run_id or candidate_id", "calibration_id, if available"],
        "optional_actual_label_fields": ["actual_label only as target/outcome, never prediction", "actual_label_source", "actual_label_version"],
        "optional_mask_fields": ["setup_quality_score", "entry_path_quality_score", "stop_pressure_risk_score", "recovery_guard_decision"],
        "optional_profit_outcome_fields": ["net_r", "gross_r", "exit_reason", "profit_outcome_source"],
        "forbidden_fields_as_prediction": ["ml_labels.direction_label", "any actual/target/outcome label"],
        "leakage_guardrails": ["prediction provenance must name model inference stage", "actual labels remain target-only", "calibration fit split must be declared", "validation/test labels cannot enter model features"],
        "validation_rules": [
            f"exactly {required_row_count} unique join keys for full-dataset stream",
            "no duplicate symbol+interval+candle_open_time within stream",
            "predicted_label present for every row",
            "predicted_label in UP/DOWN/FLAT",
            "probabilities sum sanity check if available",
            "actual_label may be null but if present must be separate from predicted_label",
            f"split_name coverage train/val/test totals should match dataset split counts and sum to {required_row_count}",
            "artifact must declare denominator_scope explicitly",
        ],
        "artifact_formats": ["JSONL row stream", "JSON summary", "JSON schema"],
    }


def build_capture_point_options_board() -> list[dict[str, Any]]:
    rows = [
        ("A", "after model inference before calibration", "FULL_DATASET", True, True, True, True, True, True, False, "LOW", "HIGH", "MEDIUM", False, "does not preserve calibrated/selected decision"),
        ("B", "after calibration before decision selection", "FULL_DATASET", True, True, True, True, True, True, False, "MEDIUM", "HIGH", "MEDIUM", False, "does not preserve final decision selection"),
        ("C", "after decision selection for all dataset rows", "FULL_DATASET", True, True, True, True, True, True, False, "LOW", "HIGH", "MEDIUM", True, "best semantic capture point for final predictions"),
        ("D", "evaluator payload rows during quality evaluation", "CURRENTLY_TEST_ONLY", True, True, True, False, False, True, False, "MEDIUM", "HIGH", "LOW", False, "current evaluator input is not full-dataset"),
        ("E", "persist to ml_predictions table", "FULL_DATASET", True, True, True, True, True, True, True, "LOW", "LOW", "HIGH", False, "optional later persistence; DB writes forbidden in this stage"),
        ("F", "export sidecar JSON/JSONL beside candidate_result", "FULL_DATASET", True, True, True, True, True, True, False, "LOW", "LOW_WITH_WHITELIST", "MEDIUM", True, "preferred future artifact design; separate implementation approval required"),
        ("G", "compact archive whitelist only for existing test payload", "TEST_ONLY", True, True, True, False, False, False, False, "LOW", "LOW", "LOW", False, "preserves 973 only and cannot create missing 6481 rows"),
    ]
    keys = ["option_id", "capture_point", "expected_denominator", "captures_predicted_label", "captures_probabilities", "captures_timestamp_key", "captures_split_name", "supports_full_6481", "requires_training_rerun", "requires_db_write", "leakage_risk", "compact_archive_risk", "implementation_complexity", "recommended", "reason"]
    return [dict(zip(keys, row)) for row in rows]


def build_compact_profile_whitelist_design() -> dict[str, Any]:
    return {
        "current_compact_problem": "row-heavy prediction payloads are replaced by compact omission markers",
        "payloads_to_whitelist": ["full_dataset_prediction_stream.jsonl", "full_dataset_prediction_stream_summary.json", "prediction_payload_schema.json", "test_prediction_stream.jsonl (optional)"],
        "minimal_safe_fields": ["identity fields", "predicted_label", "probabilities", "confidence", "split_name", "model_version", "actual_label optional but clearly target-only"],
        "fields_to_exclude": ["large raw feature arrays unless needed", "training internals", "private credentials", "non-deterministic huge payloads"],
        "size_risk": "BOUNDED_BY_6481_JSONL_ROWS_AND_MANIFEST_COUNTS",
        "privacy_or_leakage_risk": "actual labels must remain explicitly target-only; credentials forbidden",
        "validation_rules": ["whitelisted files survive compact pruning byte-for-byte", "manifest records row count and checksum", "schema and summary must accompany stream", "archive fails validation when declared stream is absent"],
        "archive_manifest_requirements": ["relative_path", "schema_version", "denominator_scope", "row_count", "sha256", "split_counts"],
        "recommended_zip_paths": ["prediction_payloads/full_dataset_prediction_stream.jsonl", "prediction_payloads/full_dataset_prediction_stream_summary.json", "prediction_payloads/prediction_payload_schema.json"],
    }


def build_leakage_and_guardrail_contract() -> dict[str, Any]:
    decisions = ["DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION", "FAIL_CLOSED_IF_PREDICTED_LABEL_STREAM_MISSING", "DO_NOT_BUILD_FULL_6481_CASCADE_WITHOUT_FULL_PREDICTIONS"]
    return {
        "actual_label_substitution_allowed": False,
        "forbidden_substitutions": ["ml_labels.direction_label -> predicted_label", "actual_label -> predicted_label", "target/outcome label -> any prediction field"],
        "target_leakage_risks": ["using target direction as model output", "calibrating on test targets", "joining targets before inference", "silent prediction fallback from direction_label"],
        "allowed_actual_label_usage": ["post-prediction outcome comparison", "target-only confusion matrix", "optional nullable target fields with explicit provenance"],
        "prediction_field_requirements": ["non-null predicted_label", "model/run provenance", "prediction_source_stage", "separate target namespace"],
        "validation_fail_closed_behavior": "reject full-dataset cascade/outcome when stream, provenance, uniqueness, or denominator validation fails",
        "decisions": decisions,
    }


def build_implementation_plan() -> dict[str, Any]:
    return {
        "recommended_next_stage_name": "ML38.10.50 — full-dataset prediction sidecar export implementation",
        "implementation_steps": ["add sidecar schema", "add exporter helper at candidate/evaluation artifact boundary", "emit full_dataset_prediction_stream.jsonl on a future quick-quality/training run", "add compact whitelist", "add manifest counts", "add validator", "add tests", "run only tests first; actual quick-quality rerun requires separate user approval"],
        "files_likely_to_touch": ["app/training/training_service.py", "app/experiments/feature_regime_experiment_reporter.py", "app/experiments/compact_archive_pruner.py", "new prediction sidecar exporter/validator modules", "targeted tests"],
        "tests_to_add": ["schema validation", "6481 unique-key validation", "split-count validation", "actual/predicted separation", "compact archive retention", "missing stream fail-closed"],
        "acceptance_criteria": ["future run produces 6481 rows for SOLUSDT current dataset", "rows unique by symbol+interval+candle_open_time", "train/val/test split counts sum to 6481", "predicted_label present and not from actual label", "probability fields present", "compact ZIP keeps payload", "no DB writes unless explicitly approved later"],
        "rollback_plan": ["remove sidecar exporter invocation", "remove archive whitelist entries", "retain current candidate/evaluator behavior", "do not migrate or mutate database rows"],
        "non_goals": ["no implementation in ML38.10.49", "no training/runtime run", "no DB persistence", "no label/gate/model changes", "no full cascade/outcome recompute", "no tradable-edge claim"],
        "future_capture_requires_separate_approval": True,
    }


def build_full_dataset_guardrail(
    *,
    full_dataset_feature_rows: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS,
    full_dataset_prediction_rows_found: int = 0,
    test_prediction_rows_found: int = CONFIRMED_TEST_PREDICTION_ROWS,
    training_required_for_future_capture: bool | str = "UNKNOWN_UNTIL_IMPLEMENTATION_DESIGN",
) -> dict[str, Any]:
    return {
        "full_dataset_feature_rows": full_dataset_feature_rows,
        "full_dataset_prediction_rows_found": full_dataset_prediction_rows_found,
        "test_prediction_rows_found": test_prediction_rows_found,
        "design_only": True,
        "full_dataset_cascade_allowed_now": False,
        "full_dataset_outcome_allowed_now": False,
        "training_required_for_future_capture": training_required_for_future_capture,
        "db_writes_allowed_now": False,
        "actual_label_substitution_allowed": False,
        "production_like_recompute": False,
        "tradable_edge_confirmed": False,
        "decision": ["DESIGN_ONLY_NO_CAPTURE_EXECUTED", "FULL_6481_PREDICTION_STREAM_STILL_MISSING", "DO_NOT_BUILD_FULL_6481_CASCADE", "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_FULL_DATASET", "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION", "FUTURE_CAPTURE_REQUIRES_SEPARATE_APPROVAL"],
    }


def classify_payload_capture_design_decision(
    inventory: Mapping[str, Any], *, design_complete: bool = True
) -> list[str]:
    decisions = []
    if design_complete:
        decisions.extend(["FULL_DATASET_PREDICTION_PAYLOAD_CAPTURE_DESIGN_ADDED", "CURRENT_PAYLOAD_INVENTORY_COMPLETED"])
    if int(inventory.get("test_prediction_rows_found") or 0) == CONFIRMED_TEST_PREDICTION_ROWS:
        decisions.append("ONLY_TEST_973_TIMESTAMPED_PREDICTIONS_AVAILABLE")
    if int(inventory.get("dataset_prediction_rows_found") or 0) < int(inventory.get("split_total_rows") or 0):
        decisions.append("FULL_6481_PREDICTION_STREAM_MISSING")
    decisions.extend(["REQUIRED_PREDICTION_STREAM_CONTRACT_DEFINED", "CAPTURE_POINT_OPTIONS_DEFINED", "COMPACT_WHITELIST_DESIGN_DEFINED", "LEAKAGE_GUARDRAILS_DEFINED", "IMPLEMENTATION_PLAN_DEFINED", "DESIGN_ONLY_NO_CAPTURE_EXECUTED", "FULL_6481_CASCADE_NOT_ALLOWED", "FULL_6481_OUTCOME_NOT_ALLOWED", "FUTURE_CAPTURE_REQUIRES_SEPARATE_APPROVAL", "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION", "DO_NOT_CHANGE_LABELS_YET", "DO_NOT_CHANGE_GATES", "DO_NOT_RUN_TRAINING"])
    return decisions


def build_read_only_full_dataset_prediction_payload_capture_design_audit(
    *,
    symbol: str = "SOLUSDT",
    interval: str = "15m",
    date_range: str = "2026-04-01 -> 2026-06-15",
    reference_config_id: str = REFERENCE_CONFIG_ID,
    selected_feature_version: str = "fv3_candle_ta_context",
    selected_label_version: str = "lv31_h12_dates_exit45_long",
    selected_horizon_candles: int = 12,
    source_counts: Mapping[str, Any] | None = None,
    probability_payload_path: str | None = None,
    candidate_result_path: str | None = None,
    source_zip_path: str | None = None,
    discovered_prediction_sources: Sequence[Mapping[str, Any]] | None = None,
    test_prediction_rows_found: int = CONFIRMED_TEST_PREDICTION_ROWS,
    dataset_prediction_rows_found: int = 0,
    full_dataset_feature_rows: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS,
    split_total_rows: int = CONFIRMED_FULL_DATASET_FEATURE_ROWS,
) -> dict[str, Any]:
    inventory = build_current_prediction_payload_inventory(
        probability_payload_path=probability_payload_path,
        candidate_result_path=candidate_result_path,
        source_zip_path=source_zip_path,
        discovered_prediction_sources=discovered_prediction_sources,
        test_prediction_rows_found=test_prediction_rows_found,
        dataset_prediction_rows_found=dataset_prediction_rows_found,
        full_dataset_feature_rows=full_dataset_feature_rows,
        split_total_rows=split_total_rows,
    )
    guardrail = build_full_dataset_guardrail(
        full_dataset_feature_rows=full_dataset_feature_rows,
        full_dataset_prediction_rows_found=dataset_prediction_rows_found,
        test_prediction_rows_found=test_prediction_rows_found,
    )
    decision = classify_payload_capture_design_decision(inventory)
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "symbol": symbol,
        "interval": interval,
        "date_range": date_range,
        "reference_config_id": reference_config_id,
        "selected_feature_version": selected_feature_version,
        "selected_label_version": selected_label_version,
        "selected_horizon_candles": selected_horizon_candles,
        "source_counts": dict(source_counts or {}),
        "current_prediction_payload_inventory": inventory,
        "prediction_generation_path_trace": build_prediction_generation_path_trace(),
        "current_artifact_gap_board": build_current_artifact_gap_board(inventory),
        "required_full_dataset_prediction_stream_contract": build_required_full_dataset_prediction_stream_contract(required_row_count=split_total_rows),
        "capture_point_options_board": build_capture_point_options_board(),
        "compact_profile_whitelist_design": build_compact_profile_whitelist_design(),
        "leakage_and_guardrail_contract": build_leakage_and_guardrail_contract(),
        "implementation_plan": build_implementation_plan(),
        "full_dataset_guardrail": guardrail,
        "next_step_plan": ["review ML38.10.49 design", "obtain separate approval for ML38.10.50 implementation", "implement and test sidecar export without DB writes", "obtain separate approval before any quick-quality/training rerun"],
        "decision": decision,
        "ml38_10_49_payload_capture_design_decision": decision,
    }
