from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "read_only_real_sidecar_generation_command_design"
DIAGNOSTIC_VERSION = "ml38.10.52"
EXECUTION_MODE = "DESIGN_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
PREFERRED_FUTURE_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality "
    "--quick-quality-symbol SOLUSDT"
)
SIDECAR_FILES = (
    "prediction_payloads/full_dataset_prediction_stream.jsonl",
    "prediction_payloads/full_dataset_prediction_stream_summary.json",
    "prediction_payloads/prediction_payload_schema.json",
)


def build_current_readiness_summary() -> dict[str, Any]:
    return {
        "exporter_implemented": True,
        "fixture_audit_passed": True,
        "compact_whitelist_implemented": True,
        "real_full_dataset_stream_exists": False,
        "quick_quality_generation_executed": False,
        "full_6481_cascade_allowed_now": False,
        "ready_for_command_design": True,
        "ready_for_real_generation_without_user_approval": False,
        "readiness_status": "READY_FOR_DESIGN_ONLY_NOT_EXECUTION",
    }


def build_command_design_board() -> list[dict[str, Any]]:
    common = {
        "expected_symbol": "SOLUSDT",
        "expected_interval": "15m",
        "expected_denominator_scope": "FULL_DATASET_6481",
        "expected_row_count_reference": 6481,
        "run_allowed_now": False,
        "reason_run_not_allowed_now": (
            "ML38.10.52 is design-only; real quick-quality generation requires "
            "a separate explicit user approval."
        ),
        "separate_user_approval_required": True,
    }
    return [
        {
            **common,
            "command_id": "preferred_existing_quick_quality_entry_point",
            "command_text": PREFERRED_FUTURE_COMMAND,
            "command_type": "FUTURE_REAL_QUICK_QUALITY_GENERATION",
            "currently_supported_by_code": "partial",
            "requires_new_flag_or_wiring": "unknown",
            "requires_preflight_probe": True,
            "expected_outputs": [
                "reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>/",
                "reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>.zip",
                *SIDECAR_FILES,
            ],
            "risks": [
                "quick-quality entry point is supported but sidecar exporter wiring is not guaranteed",
                "runtime writes report artifacts inside the repository",
                "source/config metadata could be mixed unless preflight consistency checks pass",
            ],
            "preconditions": [
                "all required preflight checks pass",
                "sidecar exporter invocation is confirmed at the full-dataset prediction boundary",
                "unique output directory and external log path are declared",
                "separate explicit user approval is recorded",
            ],
            "postconditions": [
                "run exit status is recorded",
                "declared sidecars exist without overwriting prior reports",
                "all post-run validation steps pass before any cascade/outcome stage",
            ],
        },
        {
            **common,
            "command_id": "future_explicit_sidecar_export_flag",
            "command_text": PREFERRED_FUTURE_COMMAND + " --export-prediction-sidecar",
            "command_type": "FUTURE_EXPLICIT_SIDECAR_GENERATION_FLAG",
            "currently_supported_by_code": False,
            "requires_new_flag_or_wiring": True,
            "requires_preflight_probe": True,
            "expected_outputs": list(SIDECAR_FILES),
            "risks": [
                "flag is not currently implemented",
                "incorrect wiring could export test-only rather than full-dataset rows",
            ],
            "preconditions": [
                "flag and exporter wiring are implemented in a separately approved stage",
                "targeted tests prove full-dataset and provenance behavior",
                "all required preflight checks and separate approval pass",
            ],
            "postconditions": [
                "sidecar generation is explicit in recorded command metadata",
                "all sidecars and archive manifest checks validate",
            ],
        },
        {
            **common,
            "command_id": "future_validation_only_cli",
            "command_text": (
                "python -m app.cli.commands validate-prediction-sidecar "
                "--run-dir <approved-quick-quality-run-dir>"
            ),
            "command_type": "FUTURE_POST_RUN_VALIDATION_ONLY",
            "currently_supported_by_code": False,
            "requires_new_flag_or_wiring": True,
            "requires_preflight_probe": True,
            "expected_outputs": ["validation result on stdout or an external log only"],
            "risks": [
                "CLI is a design candidate and does not currently exist",
                "wrong run directory could validate stale artifacts",
            ],
            "preconditions": [
                "validation-only CLI is implemented without generation or DB writes",
                "approved run directory is passed explicitly",
                "generated stream, summary, and schema already exist",
            ],
            "postconditions": [
                "validator exits nonzero on every contract violation",
                "validation does not modify source artifacts",
            ],
        },
    ]


def build_preflight_checklist() -> list[dict[str, Any]]:
    rows = [
        ("git status clean", True, "STOP_AND_REPORT_GIT_STATUS"),
        ("branch recorded", True, "STOP_AND_RECORD_BRANCH"),
        ("latest commit recorded", True, "STOP_AND_RECORD_COMMIT"),
        ("no uncommitted code", True, "STOP_AND_REPORT_UNCOMMITTED_CODE"),
        ("no DB-mutating commands planned", True, "REJECT_RUN_PLAN"),
        ("no ml_labels writes planned", True, "REJECT_RUN_PLAN"),
        ("no ml_predictions writes planned", True, "REJECT_RUN_PLAN"),
        ("quick-quality symbol limited to SOLUSDT", True, "REJECT_RUN_PLAN"),
        ("interval expected 15m", True, "REJECT_RUN_PLAN"),
        ("output directory unique", True, "CHOOSE_NEW_TIMESTAMPED_OUTPUT_DIR"),
        ("previous reports not overwritten", True, "REJECT_OUTPUT_PATH"),
        ("exporter module importable", True, "STOP_AND_FIX_IMPORT"),
        ("compact whitelist available", True, "STOP_AND_FIX_WHITELIST"),
        ("source/config consistency enabled", True, "STOP_AND_FIX_VALIDATION"),
        ("expected sidecar paths declared", True, "STOP_AND_DECLARE_PATHS"),
        ("pytest passed before run", True, "STOP_AND_FIX_TESTS"),
        ("logs outside repo", True, "CHOOSE_EXTERNAL_LOG_PATH"),
        ("user approval present", True, "STOP_AND_REQUEST_SEPARATE_APPROVAL"),
    ]
    return [
        {
            "check_name": name,
            "required": True,
            "can_validate_before_run": can_validate,
            "failure_action": action,
            "status_in_design": "NOT_EXECUTED_REQUIRES_FUTURE_PREFLIGHT",
        }
        for name, can_validate, action in rows
    ]


def build_source_config_consistency_contract() -> dict[str, Any]:
    return {
        "ml38_10_49_warning": (
            "Snapshot evidence contained an lv36 probability payload versus lv31 "
            "reference config and fv4 feature metadata versus prior fv3 metadata."
        ),
        "required_consistent_fields": [
            "symbol",
            "interval",
            "config_id",
            "candidate_id",
            "run_id",
            "model_version",
            "feature_version",
            "label_version",
            "horizon_candles",
            "denominator_scope",
            "dataset row identity",
        ],
        "mismatch_policy": "FAIL_CLOSED",
        "forbidden_mix_examples": [
            "lv36 probability payload with lv31 candidate_result",
            "fv4 feature version with fv3 candidate metadata",
            "test-only 973 predictions treated as full 6481 stream",
            "ml_labels.direction_label treated as predicted_label",
        ],
        "validation_timing": [
            "before packaging",
            "after generation",
            "before cascade/outcome",
        ],
        "decision": [
            "SOURCE_CONFIG_MISMATCH_FAILS_CLOSED",
            "NO_SILENT_CROSS_CANDIDATE_PAYLOAD_MIXING",
        ],
    }


def build_expected_artifact_contract() -> dict[str, Any]:
    return {
        "expected_denominator_scope": "FULL_DATASET_6481",
        "expected_join_key": "symbol+interval+candle_open_time",
        "expected_row_count": "must match split_total_rows (6481 reference)",
        "expected_run_root": (
            "reports/feature_regime_experiments/"
            "quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>/"
        ),
        "required_files": list(SIDECAR_FILES),
        "required_summary_fields": [
            "schema_version",
            "denominator_scope",
            "row_count",
            "split_counts",
            "join_key_fields",
            "stream_sha256",
        ],
        "required_schema_fields": [
            "symbol",
            "interval",
            "candle_open_time",
            "split_name",
            "split_row_index",
            "split_total_rows",
            "config_id",
            "feature_version",
            "label_version",
            "model_version",
            "horizon_candles",
            "predicted_label",
            "prob_up",
            "prob_down",
            "prob_flat",
            "confidence",
        ],
        "required_checksums": [
            "summary stream_sha256 matches JSONL bytes",
            "archive manifest records each sidecar relative path and checksum",
        ],
        "archive_manifest_entry_required": True,
        "compact_archive_retention_required": True,
        "real_generation_status_now": "NOT_CREATED",
    }


def build_post_run_validation_plan() -> dict[str, Any]:
    specifications = [
        ("01", "locate latest approved quick-quality run dir", "approved command record", "one unique run directory is selected"),
        ("02", "locate prediction sidecar folder", "selected run directory", "prediction_payloads folder exists"),
        ("03", "validate JSONL row count", "stream and summary", "row_count equals split_total_rows and 6481 reference"),
        ("04", "validate unique keys", "stream JSONL", "all symbol+interval+candle_open_time keys are unique"),
        ("05", "validate split counts", "stream and summary", "train/val/test counts sum to row_count"),
        ("06", "validate predicted label domain", "stream JSONL", "every predicted_label is UP, DOWN, or FLAT"),
        ("07", "validate probability sanity", "stream JSONL", "probabilities are finite, bounded, and sum to one"),
        ("08", "validate config/model/feature/label consistency", "stream plus candidate metadata", "all required provenance fields match"),
        ("09", "validate forbidden actual-label source absent", "stream JSONL", "no actual/target/ml_labels source supplies predicted_label"),
        ("10", "validate compact ZIP includes sidecars", "compact ZIP and manifest", "required sidecars are byte-retained and checksummed"),
        ("11", "confirm no DB or ml_predictions writes", "run command and audit evidence", "no DB, ml_labels, or ml_predictions writes occurred"),
        ("12", "gate future full 6481 cascade/outcome", "all prior validation results", "separate future stage is eligible only after every check passes"),
    ]
    return {
        "validation_mode": "READ_ONLY_FAIL_CLOSED",
        "steps": [
            {
                "step_id": step_id,
                "validation_name": name,
                "required_input": required_input,
                "expected_result": expected,
                "failure_action": "FAIL_CLOSED_AND_BLOCK_ML38_10_53_OR_LATER_ANALYSIS",
                "blocks_next_stage_if_failed": True,
            }
            for step_id, name, required_input, expected in specifications
        ],
    }


def build_failure_handling_plan() -> dict[str, Any]:
    scenarios = [
        "sidecar folder missing",
        "stream JSONL missing",
        "row_count != split_total_rows",
        "duplicate timestamp keys",
        "predicted_label missing/invalid",
        "probability invalid",
        "config mismatch",
        "compact archive missing sidecar",
        "DB writes detected unexpectedly",
        "actual label substitution detected",
        "quick-quality fails",
        "incomplete runtime artifacts",
    ]
    no_retry = {
        "DB writes detected unexpectedly",
        "actual label substitution detected",
        "config mismatch",
    }
    return {
        "default_policy": "FAIL_CLOSED",
        "scenarios": [
            {
                "scenario": scenario,
                "severity": "CRITICAL" if scenario in no_retry else "HIGH",
                "fail_closed": True,
                "cleanup_allowed": "only isolated incomplete run artifacts after review; never prior reports or DB rows",
                "retry_allowed": scenario not in no_retry,
                "commit_allowed": False,
                "next_action": (
                    "STOP_AND_ESCALATE_FOR_ROOT_CAUSE_REVIEW"
                    if scenario in no_retry
                    else "STOP_VALIDATE_ROOT_CAUSE_AND_REQUIRE_NEW_APPROVAL_BEFORE_RETRY"
                ),
            }
            for scenario in scenarios
        ],
        "rollback_plan": [
            "do not commit incomplete runtime artifacts, logs, ZIP, JSON, or sidecars",
            "preserve prior reports and archives unchanged",
            "remove only the uniquely identified failed-run directory after explicit review",
            "do not roll back or mutate database rows because DB writes are forbidden",
            "keep full 6481 cascade/outcome blocked",
        ],
    }


def build_approval_gate_contract() -> dict[str, Any]:
    return {
        "this_stage_allows_real_run": False,
        "real_quick_quality_requires_separate_user_approval": True,
        "approval_text_required": True,
        "allowed_future_command_after_approval": PREFERRED_FUTURE_COMMAND,
        "disallowed_without_approval": [
            "quick-quality",
            "training",
            "runtime",
            "DB-mutating commands",
            "real sidecar generation",
            "full 6481 cascade/outcome",
        ],
        "after_generation_next_required_stage": (
            "ML38.10.53 — real sidecar generation validation audit"
        ),
    }


def build_real_stream_guardrail() -> dict[str, Any]:
    return {
        "real_full_dataset_prediction_stream_created": False,
        "real_full_dataset_prediction_stream_path": None,
        "real_stream_row_count": 0,
        "quick_quality_executed": False,
        "training_or_runtime_executed": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "full_6481_cascade_allowed_now": False,
        "full_6481_outcome_allowed_now": False,
        "production_like_recompute": False,
        "tradable_edge_confirmed": False,
        "real_generation_requires_separate_approval": True,
    }


def build_ml38_10_52_real_sidecar_generation_command_design_decision() -> list[str]:
    return [
        "REAL_SIDECAR_GENERATION_COMMAND_DESIGN_ADDED",
        "COMMAND_CANDIDATES_DEFINED",
        "PREFLIGHT_CHECKLIST_DEFINED",
        "SOURCE_CONFIG_CONSISTENCY_CONTRACT_DEFINED",
        "EXPECTED_ARTIFACT_CONTRACT_DEFINED",
        "POST_RUN_VALIDATION_PLAN_DEFINED",
        "FAILURE_HANDLING_PLAN_DEFINED",
        "APPROVAL_GATE_DEFINED",
        "DESIGN_ONLY_NO_QUICK_QUALITY_EXECUTED",
        "REAL_FULL_6481_STREAM_NOT_CREATED",
        "QUICK_QUALITY_RERUN_REQUIRES_SEPARATE_APPROVAL",
        "DB_WRITES_NOT_ALLOWED",
        "ML_PREDICTIONS_NOT_WRITTEN",
        "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION",
        "FULL_6481_CASCADE_NOT_ALLOWED_UNTIL_STREAM_EXISTS",
        "DO_NOT_CHANGE_LABELS_YET",
        "DO_NOT_CHANGE_GATES",
        "DO_NOT_RUN_TRAINING",
    ]


def build_read_only_real_sidecar_generation_command_design() -> dict[str, Any]:
    decision = build_ml38_10_52_real_sidecar_generation_command_design_decision()
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "generation_scope": "FUTURE_REAL_QUICK_QUALITY_RUN",
        "source_counts_reference": {
            "full_dataset_rows_reference": 6481,
            "test_only_prediction_rows_reference": 973,
            "ml38_10_51_synthetic_fixture_rows": 6,
            "real_stream_rows_created_in_this_stage": 0,
        },
        "current_readiness_summary": build_current_readiness_summary(),
        "command_design_board": build_command_design_board(),
        "preflight_checklist": build_preflight_checklist(),
        "source_config_consistency_contract": build_source_config_consistency_contract(),
        "expected_artifact_contract": build_expected_artifact_contract(),
        "post_run_validation_plan": build_post_run_validation_plan(),
        "failure_handling_plan": build_failure_handling_plan(),
        "approval_gate_contract": build_approval_gate_contract(),
        "real_stream_guardrail": build_real_stream_guardrail(),
        "next_step_plan": [
            "review this design and confirm sidecar wiring before any run",
            "obtain separate explicit user approval for real quick-quality generation",
            "after generation run ML38.10.53 read-only validation audit",
            "keep full 6481 cascade/outcome blocked until validation passes",
        ],
        "decision": decision,
        "ml38_10_52_real_sidecar_generation_command_design_decision": decision,
    }


read_only_real_sidecar_generation_command_design = (
    build_read_only_real_sidecar_generation_command_design()
)
