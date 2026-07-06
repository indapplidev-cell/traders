from __future__ import annotations

from pathlib import Path
from typing import Any

from app.experiments import prediction_sidecar_exporter as sidecar_exporter
from app.experiments.compact_archive_pruner import (
    is_prediction_sidecar_artifact_path,
    should_preserve_prediction_sidecar_artifact,
)


DIAGNOSTIC_NAME = "read_only_real_sidecar_generation_preflight_probe"
DIAGNOSTIC_VERSION = "ml38.10.53"
EXECUTION_MODE = "PREFLIGHT_PROBE_ONLY_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES"
PREFERRED_COMMAND = "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _entrypoint_probe_board() -> list[dict[str, Any]]:
    path = REPO_ROOT / "run_fv3_cached_tuning.py"
    source = _source("run_fv3_cached_tuning.py")
    probes = [
        (
            "run_fv3_cached_tuning.py exists",
            True,
            path.is_file(),
            "run_fv3_cached_tuning.py is present at the repository root.",
            True,
        ),
        (
            "preferred command entry point exists",
            "python run_fv3_cached_tuning.py",
            path.is_file() and "def parse_args(" in source and "def main(" in source,
            "parse_args and main are defined in run_fv3_cached_tuning.py.",
            True,
        ),
        (
            "--quick-quality flag supported or detected",
            "--quick-quality",
            '"--quick-quality"' in source and "args.quick_quality" in source,
            "argparse defines --quick-quality and Fv3CachedTuningWrapper reads args.quick_quality.",
            True,
        ),
        (
            "--quick-quality-symbol flag supported or detected",
            "--quick-quality-symbol",
            '"--quick-quality-symbol"' in source and "args.quick_quality_symbol" in source,
            "argparse defines --quick-quality-symbol and the quick-quality branch consumes it.",
            True,
        ),
        (
            "SOLUSDT can be passed as symbol",
            "SOLUSDT",
            'QUICK_QUALITY_SYMBOL = "SOLUSDT"' in source and "part.upper()" in source,
            "QUICK_QUALITY_SYMBOL defaults to SOLUSDT; parsed symbols are normalized to uppercase.",
            True,
        ),
        (
            "15m interval is default or traceable",
            "15m",
            'DEFAULT_INTERVAL = "15m"' in source and 'parser.add_argument("--interval"' in source,
            "DEFAULT_INTERVAL is 15m and --interval uses that default.",
            True,
        ),
        (
            "output root under reports/feature_regime_experiments is traceable",
            "reports/feature_regime_experiments",
            '"reports" / "feature_regime_experiments"' in source,
            "Fv3CachedTuningWrapper constructs output_root from reports/feature_regime_experiments.",
            True,
        ),
        (
            "command can be logged externally by wrapper/user",
            "external Tee-Object log path",
            "Tee-Object -FilePath" in source,
            "The entrypoint usage text shows Tee-Object with a caller-selected log directory.",
            False,
        ),
    ]
    return [
        {
            "probe_name": name,
            "expected": expected,
            "observed": observed,
            "status": "PASS" if observed else "FAIL",
            "evidence": evidence,
            "blocks_real_generation_if_failed": blocks,
        }
        for name, expected, observed, evidence, blocks in probes
    ]


def _sidecar_wiring_probe_board() -> list[dict[str, Any]]:
    runner = _source("run_fv3_cached_tuning.py")
    exporter = _source("app/experiments/prediction_sidecar_exporter.py")
    experiment_reporter = _source("app/experiments/feature_regime_experiment_reporter.py")
    analyzer = _source("app/experiments/multi_symbol_feature_regime_analyzer.py")
    multi_reporter = _source("app/experiments/multi_symbol_feature_regime_reporter.py")
    training = _source("app/training/training_service.py")
    metrics = _source("app/training/metrics.py")

    return [
        {
            "component": "prediction_sidecar_exporter module importable",
            "expected_wiring": "module and writer API import successfully",
            "observed_wiring": "module import succeeded and write_prediction_sidecar_artifacts is callable",
            "status": "WIRED" if callable(sidecar_exporter.write_prediction_sidecar_artifacts) else "NOT_WIRED",
            "evidence": "app/experiments/prediction_sidecar_exporter.py defines schema, validator, summary, and writer APIs.",
            "required_fix_if_not_wired": "restore an importable exporter writer API",
        },
        {
            "component": "run_fv3_cached_tuning.py",
            "expected_wiring": "references and invokes prediction_sidecar_exporter at the candidate boundary",
            "observed_wiring": "no prediction_sidecar_exporter import, writer reference, or sidecar invocation found",
            "status": "NOT_WIRED" if "prediction_sidecar_exporter" not in runner else "PARTIAL",
            "evidence": "The runner launches the tuning CLI, stages reports, prunes, and archives; it contains no prediction_sidecar_exporter token.",
            "required_fix_if_not_wired": "invoke the exporter with validated full-dataset prediction rows before compact packaging",
        },
        {
            "component": "feature_regime_experiment_reporter",
            "expected_wiring": "propagates sidecar metadata and generation failure status",
            "observed_wiring": "preserves sidecar implementation/design metadata keys only; no exporter invocation",
            "status": "PARTIAL" if "full_dataset_prediction_sidecar_export_implementation" in experiment_reporter else "NOT_WIRED",
            "evidence": "Reporter keeps full_dataset_prediction_sidecar_export_implementation but does not call the writer.",
            "required_fix_if_not_wired": "add generated-sidecar manifest and fail-closed status propagation",
        },
        {
            "component": "multi_symbol_feature_regime_analyzer",
            "expected_wiring": "references sidecar metadata and exporter invocation result",
            "observed_wiring": "imports metadata/decision builders only; no write_prediction_sidecar_artifacts call",
            "status": "PARTIAL" if "build_sidecar_export_implementation_metadata" in analyzer else "NOT_WIRED",
            "evidence": "Analyzer imports two metadata builders from prediction_sidecar_exporter, not its writer.",
            "required_fix_if_not_wired": "consume an explicit validated exporter result from the generation boundary",
        },
        {
            "component": "multi_symbol_feature_regime_reporter",
            "expected_wiring": "reports sidecar metadata, paths, validation, and failures",
            "observed_wiring": "renders implementation metadata only; no real artifact result or exporter call",
            "status": "PARTIAL" if "full_dataset_prediction_sidecar_export_implementation" in multi_reporter else "NOT_WIRED",
            "evidence": "Reporter renders the ML38.10.50 implementation block and real_stream_created=false metadata.",
            "required_fix_if_not_wired": "render actual sidecar manifest/validation status and fail closed on generation failure",
        },
        {
            "component": "training_service full split prediction rows",
            "expected_wiring": "exposes train/val/test prediction rows with split names and candle timestamps",
            "observed_wiring": "split_rows and candle_open_time exist locally, but evaluator probabilities are reduced to metrics and rows are not returned",
            "status": "PARTIAL" if "split_rows =" in training and "candle_open_time" in training else "UNKNOWN",
            "evidence": "TrainingService builds dataset_rows/split_rows and evaluates each tensor split; its return payload exposes test metrics, not row-level predictions.",
            "required_fix_if_not_wired": "capture model probabilities aligned to every split row and return an exporter-ready row stream",
        },
        {
            "component": "exporter invocation at candidate artifact boundary",
            "expected_wiring": "write_prediction_sidecar_artifacts is called for the selected candidate before archive finalization",
            "observed_wiring": "writer definition exists only in exporter module; no caller exists in inspected generation path",
            "status": "NOT_WIRED",
            "evidence": "Repository path scan of runner/training/reporters finds no writer call outside its definition/tests/fixture audit.",
            "required_fix_if_not_wired": "add one explicit candidate-boundary writer call with full-row metadata",
        },
        {
            "component": "three required sidecar writer paths",
            "expected_wiring": "writer declares JSONL, summary JSON, and schema JSON paths",
            "observed_wiring": "all three filenames are constructed below prediction_payloads and written by the exporter",
            "status": "WIRED" if all(name in exporter for name in (
                "full_dataset_prediction_stream.jsonl",
                "full_dataset_prediction_stream_summary.json",
                "prediction_payload_schema.json",
            )) else "NOT_WIRED",
            "evidence": "write_prediction_sidecar_artifacts constructs stream_path, summary_path, and schema_path.",
            "required_fix_if_not_wired": "define all three required companion artifacts",
        },
        {
            "component": "validation before/after write",
            "expected_wiring": "fail-closed validation runs before artifacts are written",
            "observed_wiring": "validate_prediction_sidecar_rows runs before mkdir/write_text and raises on invalid status; no post-write reread validation",
            "status": "PARTIAL" if exporter.index("validate_prediction_sidecar_rows(", exporter.index("def write_prediction_sidecar_artifacts")) < exporter.index(".write_text(") else "NOT_WIRED",
            "evidence": "Exporter validates before writes, but the quick-quality path does not invoke it and no post-write byte reread occurs.",
            "required_fix_if_not_wired": "retain pre-write validation and add post-write/manifest verification in the wired path",
        },
        {
            "component": "candidate/report generation failure capture",
            "expected_wiring": "sidecar failure is captured in candidate/report metadata and blocks completion",
            "observed_wiring": "implementation metadata is present, but there is no generation attempt whose failure can be captured",
            "status": "NOT_WIRED",
            "evidence": f"Reporter metadata exists={bool('full_dataset_prediction_sidecar_export_implementation' in experiment_reporter)}; metrics only aggregate predictions={bool('direction_probabilities' in metrics)}.",
            "required_fix_if_not_wired": "persist exporter status/error in candidate summary and fail archive completion when generation/validation fails",
        },
    ]


def _full_dataset_boundary_probe() -> dict[str, Any]:
    return {
        "expected_denominator_scope": "FULL_DATASET_6481",
        "expected_reference_rows": 6481,
        "training_dataset_split_rows_trace_found": True,
        "test_only_973_boundary_detected": True,
        "full_dataset_prediction_rows_available_before_test_filter": False,
        "split_name_available_for_all_rows": False,
        "timestamp_key_available_for_all_rows": True,
        "can_prove_future_export_will_be_6481": False,
        "reason_if_not_proven": (
            "TrainingService retains full dataset_rows and split_rows with candle_open_time, but row-level "
            "probabilities are transient inside evaluator calls and are not exposed with split_name. The "
            "existing report lineage documents a 973-row test-only payload, so a future caller could export "
            "the test boundary unless full train/val/test capture is implemented explicitly."
        ),
        "status": "TEST_ONLY_BOUNDARY_RISK",
    }


def _artifact_path_probe() -> dict[str, Any]:
    return {
        "expected_paths": [
            "reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>/prediction_payloads/full_dataset_prediction_stream.jsonl",
            "reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>/prediction_payloads/full_dataset_prediction_stream_summary.json",
            "reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_<UTC_TIMESTAMP>/prediction_payloads/prediction_payload_schema.json",
        ],
        "path_construction_found": True,
        "unique_output_strategy_found": True,
        "overwrite_guard_found": False,
        "compact_zip_path_found": True,
        "status": "PARTIAL",
        "blockers": [
            "the exporter is not called with the timestamped quick-quality run directory",
            "no explicit sidecar overwrite refusal is present",
            "archive inclusion cannot occur until sidecars are created inside the staged per-symbol tree",
        ],
    }


def _compact_whitelist_probe() -> dict[str, Any]:
    checks = [
        ("prediction_payloads/full_dataset_prediction_stream.jsonl", True),
        ("prediction_payloads/full_dataset_prediction_stream_summary.json", True),
        ("prediction_payloads/prediction_payload_schema.json", True),
        ("prediction_payloads/test_prediction_stream.jsonl", True),
        ("prediction_payloads/raw_feature_dump.jsonl", False),
        ("raw_features/features.jsonl", False),
        ("credentials/token.json", False),
    ]
    rows = []
    for path, expected in checks:
        observed = bool(
            is_prediction_sidecar_artifact_path(path)
            and should_preserve_prediction_sidecar_artifact(path)
        )
        rows.append(
            {
                "path": path,
                "expected_preserved": expected,
                "observed_preserved": observed,
                "status": "PASS" if observed == expected else "FAIL",
                "reason": (
                    "exact bounded prediction-sidecar whitelist match"
                    if observed
                    else "path is not in the bounded prediction-sidecar whitelist"
                ),
            }
        )
    return {
        "helper_names": [
            "is_prediction_sidecar_artifact_path",
            "should_preserve_prediction_sidecar_artifact",
        ],
        "path_checks": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
    }


def _source_config_consistency_probe() -> dict[str, Any]:
    specifications = [
        ("config_id", True, "expected_config_id is compared with all normalized row values", True, "READY"),
        ("candidate_id", True, "row values are checked for mixed candidate_id values; no expected metadata comparison", True, "PARTIAL"),
        ("run_id", True, "row values are checked for mixed run_id values; no expected metadata comparison", True, "PARTIAL"),
        ("model_version", True, "expected_model_version is compared with all normalized row values", True, "READY"),
        ("feature_version", True, "expected_feature_version is compared with all normalized row values", True, "READY"),
        ("label_version", True, "expected_label_version is compared with all normalized row values", True, "READY"),
        ("horizon_candles", False, "field is required per row but stream-wide or expected-value consistency is not validated", True, "MISSING"),
        ("denominator_scope", True, "FULL_DATASET_6481 requires expected_row_count=6481 and exact materialized count", True, "READY"),
        ("symbol", False, "field is required and part of join key, but mixed symbols are not rejected", True, "MISSING"),
        ("interval", False, "field is required and part of join key, but mixed intervals are not rejected", True, "MISSING"),
        ("dataset row identity", True, "dataset_row_index or row_id is required; duplicate symbol+interval+timestamp is rejected", True, "PARTIAL"),
    ]
    return {
        "field_checks": [
            {
                "required_field": field,
                "validation_available": available,
                "static_evidence": evidence,
                "fail_closed_if_missing": fail_closed,
                "status": status,
            }
            for field, available, evidence, fail_closed, status in specifications
        ],
        "forbidden_mix_examples": [
            "lv36 probability payload with lv31 candidate_result",
            "fv4 feature version with fv3 candidate metadata",
            "973-row test stream treated as 6481-row full stream",
            "ml_labels.direction_label as predicted_label",
        ],
        "mismatch_policy": "FAIL_CLOSED",
        "status": "CONSISTENCY_VALIDATION_PARTIAL",
    }


def _risk_board() -> list[dict[str, Any]]:
    rows = [
        ("sidecar exporter not invoked by quick-quality", "CRITICAL", "CONFIRMED", True, "implement and test explicit candidate-boundary invocation", True),
        ("only test rows are exported", "CRITICAL", "HIGH", True, "capture and identify train/val/test predictions before any test-only selection", True),
        ("source/config mismatch", "CRITICAL", "MEDIUM", True, "extend expected-value validation to every provenance field", True),
        ("sidecar files created but compact ZIP omits them", "HIGH", "LOW", True, "place files under staged tree and assert manifest/ZIP retention", True),
        ("DB writes unexpectedly occur", "CRITICAL", "UNKNOWN", True, "audit the approved runtime command separately and stop on any write", True),
        ("actual labels used as predicted_label", "CRITICAL", "LOW", True, "retain forbidden-source checks and model-output-only construction", True),
        ("quick-quality long run produces no sidecar", "HIGH", "HIGH", True, "do not run until sidecar invocation is wired and targeted tests pass", True),
        ("run creates reports but validation fails", "HIGH", "MEDIUM", True, "validate before write, capture failure, and block archive success", True),
    ]
    return [
        {
            "risk": risk,
            "severity": severity,
            "likelihood_static_probe": likelihood,
            "fail_closed_required": fail_closed,
            "mitigation": mitigation,
            "blocks_real_generation_now": blocks,
        }
        for risk, severity, likelihood, fail_closed, mitigation, blocks in rows
    ]


def _preflight_decision_gate() -> dict[str, Any]:
    return {
        "preferred_command": PREFERRED_COMMAND,
        "quick_quality_run_allowed_now": False,
        "preflight_probe_status": "NOT_READY_SIDEСAR_WIRING_NOT_CONFIRMED",
        "requires_wiring_implementation_stage": True,
        "requires_explicit_user_approval": True,
        "recommended_next_stage": "ML38.10.54 — sidecar quick-quality wiring implementation",
        "approval_text_needed_for_real_run": (
            "I explicitly approve one real SOLUSDT 15m quick-quality run using the reviewed sidecar wiring."
        ),
        "decision_reason": (
            "The entrypoint is traceable, but it does not invoke the exporter; full 6481 prediction rows "
            "are not exposed at the candidate boundary and provenance validation is incomplete."
        ),
    }


def _real_stream_guardrail() -> dict[str, Any]:
    return {
        "real_full_dataset_prediction_stream_created": False,
        "real_full_dataset_prediction_stream_path": None,
        "real_stream_row_count": 0,
        "sidecars_written_to_reports": False,
        "quick_quality_executed": False,
        "training_or_runtime_executed": False,
        "db_writes": False,
        "ml_labels_writes": False,
        "ml_predictions_writes": False,
        "full_6481_cascade_allowed_now": False,
        "full_6481_outcome_allowed_now": False,
        "production_like_recompute": False,
        "tradable_edge_confirmed": False,
    }


def build_ml38_10_53_real_sidecar_generation_preflight_probe_decision() -> list[str]:
    return [
        "REAL_SIDECAR_GENERATION_PREFLIGHT_PROBE_ADDED",
        "QUICK_QUALITY_ENTRYPOINT_PROBED",
        "SIDECAR_WIRING_PROBED",
        "FULL_DATASET_BOUNDARY_PROBED",
        "ARTIFACT_PATHS_PROBED",
        "COMPACT_WHITELIST_PROBED",
        "SOURCE_CONFIG_CONSISTENCY_PROBED",
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
        "NOT_READY_FOR_REAL_GENERATION",
        "NEEDS_SIDECAR_WIRING_IMPLEMENTATION",
        "NEEDS_FULL_DATASET_BOUNDARY_WIRING",
    ]


def build_read_only_real_sidecar_generation_preflight_probe() -> dict[str, Any]:
    decision = build_ml38_10_53_real_sidecar_generation_preflight_probe_decision()
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "preferred_command": PREFERRED_COMMAND,
        "source_counts_reference": {
            "full_dataset_rows_reference": 6481,
            "test_only_prediction_rows_reference": 973,
            "ml38_10_51_synthetic_fixture_rows": 6,
            "real_stream_rows_created_in_this_stage": 0,
        },
        "entrypoint_probe_board": _entrypoint_probe_board(),
        "sidecar_wiring_probe_board": _sidecar_wiring_probe_board(),
        "full_dataset_boundary_probe": _full_dataset_boundary_probe(),
        "artifact_path_probe": _artifact_path_probe(),
        "compact_whitelist_probe": _compact_whitelist_probe(),
        "source_config_consistency_probe": _source_config_consistency_probe(),
        "risk_board": _risk_board(),
        "preflight_decision_gate": _preflight_decision_gate(),
        "real_stream_guardrail": _real_stream_guardrail(),
        "next_step_plan": [
            "implement explicit sidecar wiring in ML38.10.54 without running quick-quality",
            "expose model-output prediction rows for train/val/test with timestamps and split identity",
            "extend fail-closed provenance validation and add candidate/report failure propagation",
            "obtain separate explicit user approval only after wiring tests pass",
            "keep full 6481 cascade/outcome blocked until a real stream exists and validates",
        ],
        "decision": decision,
        "ml38_10_53_real_sidecar_generation_preflight_probe_decision": decision,
    }


read_only_real_sidecar_generation_preflight_probe = (
    build_read_only_real_sidecar_generation_preflight_probe()
)
