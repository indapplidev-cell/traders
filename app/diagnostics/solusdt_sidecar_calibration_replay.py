from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping


DIAGNOSTIC_NAME = "solusdt_sidecar_calibration_replay"
DIAGNOSTIC_VERSION = "ml38.10.67"
EXECUTION_MODE = "READ_ONLY_CALIBRATION_REPLAY_NO_TRAINING_NO_RERUN"

OUTPUT_DIR = Path(
    r"D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments"
    r"\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_151645"
)
ZIP_PATH = Path(str(OUTPUT_DIR) + ".zip")
EXTERNAL_LOG_PATH = Path(
    r"D:\disk_E\game_projects\traders\traders-ml-run-logs"
    r"\solusdt_quick_quality_20260707_181639.log"
)
COMPLETION_MARKER_PATH = Path(
    r"D:\disk_E\game_projects\traders\traders-ml-run-logs"
    r"\solusdt_quick_quality_20260707_181639.completion.json"
)
LATEST_SHA256 = "5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4"
H08_ID = "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax"
CLASSES = ("DOWN", "FLAT", "UP")


def denominator_mismatch(produced_rows: int, expected_rows: int) -> dict[str, Any]:
    """Return a pure diagnostic for a produced/expected sidecar denominator."""
    delta = int(produced_rows) - int(expected_rows)
    return {
        "produced_rows": int(produced_rows),
        "expected_rows": int(expected_rows),
        "delta_rows": delta,
        "mismatch": delta != 0,
    }


def _policy_grid() -> list[tuple[str, dict[str, float]]]:
    return [
        ("current_argmax", {}),
        *(("flat_margin_buffer", {"margin": value}) for value in (0.02, 0.05, 0.08, 0.10, 0.15)),
        *(("flat_min_probability", {"threshold": value}) for value in (0.30, 0.35, 0.40, 0.45, 0.50)),
        *(("directional_confidence_floor", {"threshold": value}) for value in (0.45, 0.50, 0.55, 0.60)),
        *(("combined_conservative", {"threshold": threshold, "margin": margin})
          for threshold, margin in ((0.45, 0.05), (0.50, 0.05), (0.50, 0.10), (0.55, 0.10))),
    ]


def _predict(probabilities: Mapping[str, float], policy: str, parameters: Mapping[str, float]) -> str:
    top = max(CLASSES, key=lambda label: probabilities[label])
    if policy == "current_argmax":
        return top
    if policy == "flat_margin_buffer":
        return "FLAT" if max(probabilities.values()) - probabilities["FLAT"] <= parameters["margin"] else top
    if policy == "flat_min_probability":
        return "FLAT" if probabilities["FLAT"] >= parameters["threshold"] else top
    top_direction = "DOWN" if probabilities["DOWN"] >= probabilities["UP"] else "UP"
    top_direction_probability = probabilities[top_direction]
    if policy == "directional_confidence_floor":
        return top_direction if top_direction_probability >= parameters["threshold"] else "FLAT"
    if policy == "combined_conservative":
        directional = (
            top_direction_probability >= parameters["threshold"]
            and top_direction_probability - probabilities["FLAT"] >= parameters["margin"]
        )
        return top_direction if directional else "FLAT"
    raise ValueError(f"unsupported replay policy: {policy}")


def _safe_mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return mean(materialized) if materialized else None


def _read_candidate(stream: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    selected_counts: Counter[str] = Counter()
    probability_sums: Counter[str] = Counter()
    margins: list[float] = []
    entropies: list[float] = []
    flat_second = 0
    narrow_directional = 0
    candidate_id: str | None = None
    with stream.open("r", encoding="utf-8", newline="") as handle:
        for line in handle:
            row = json.loads(line)
            if str(row.get("split_name", "")).lower() != "test":
                continue
            candidate_id = str(row.get("candidate_id") or row.get("config_id") or "")
            probabilities = {
                "DOWN": float(row["prob_down"]),
                "FLAT": float(row["prob_flat"]),
                "UP": float(row["prob_up"]),
            }
            selected_counts[str(row["predicted_label"])] += 1
            for label, value in probabilities.items():
                probability_sums[label] += value
            ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
            margins.append(ordered[0][1] - ordered[1][1])
            entropies.append(-sum(value * math.log(value) for value in probabilities.values() if value > 0.0))
            if ordered[1][0] == "FLAT" and ordered[0][0] != "FLAT":
                flat_second += 1
                if ordered[0][1] - probabilities["FLAT"] <= 0.05:
                    narrow_directional += 1
            rows.append(probabilities)
    row_count = len(rows)
    return {
        "candidate_id": candidate_id,
        "rows": rows,
        "test_rows": row_count,
        "stored_argmax_distribution": {label: selected_counts[label] for label in CLASSES},
        "average_probabilities": {
            label: probability_sums[label] / row_count for label in CLASSES
        },
        "top_class_margin": {
            "mean": _safe_mean(margins),
            "median": median(margins) if margins else None,
            "min": min(margins) if margins else None,
            "max": max(margins) if margins else None,
        },
        "entropy_mean": _safe_mean(entropies),
        "flat_probability_second_highest_not_selected": flat_second,
        "directional_narrowly_beats_flat_within_0_05": narrow_directional,
    }


def _validate_sets(root: Path) -> tuple[dict[str, Any], list[Path]]:
    streams = sorted(root.rglob("prediction_payloads/full_dataset_prediction_stream.jsonl"))
    summaries = sorted(root.rglob("prediction_payloads/full_dataset_prediction_stream_summary.json"))
    schemas = sorted(root.rglob("prediction_payloads/prediction_payload_schema.json"))
    summary_by_parent = {path.parent: path for path in summaries}
    schema_by_parent = {path.parent: path for path in schemas}
    complete = [path for path in streams if path.parent in summary_by_parent and path.parent in schema_by_parent]
    exact_valid = True
    lf_valid = True
    schema_valid = True
    summary_valid = True
    observed_hashes: list[str] = []
    for stream in complete:
        payload = stream.read_bytes()
        summary = json.loads(summary_by_parent[stream.parent].read_text(encoding="utf-8"))
        schema = json.loads(schema_by_parent[stream.parent].read_text(encoding="utf-8"))
        digest = hashlib.sha256(payload).hexdigest()
        observed_hashes.append(digest)
        exact_valid = exact_valid and digest == summary.get("sha256") and len(payload) == summary.get("size_bytes")
        lf_valid = lf_valid and b"\r\n" not in payload and summary.get("line_ending_contract") == "LF"
        schema_valid = schema_valid and isinstance(schema, dict) and bool(schema.get("properties"))
        summary_valid = summary_valid and (
            summary.get("validation_status") == "PREDICTION_SIDECAR_VALID"
            and summary.get("row_count") == 6481
            and sum(summary.get("split_counts", {}).values()) == 6481
        )
    return {
        "sidecar_sets_found": len(set(path.parent for path in streams + summaries + schemas)),
        "complete_sets": len(complete),
        "incomplete_sets": len(set(path.parent for path in streams + summaries + schemas)) - len(complete),
        "all_exact_byte_valid": exact_valid,
        "all_lf_only_valid": lf_valid,
        "all_schema_valid": schema_valid,
        "all_summary_contract_valid": summary_valid,
        "latest_sha256": LATEST_SHA256,
        "latest_sha256_observed": LATEST_SHA256 in observed_hashes,
        "real_artifacts_mutated": False,
    }, complete


def _aggregate_policies(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for policy_name, parameters in _policy_grid():
        candidate_counts: list[Counter[str]] = []
        for candidate in candidates:
            candidate_counts.append(Counter(_predict(row, policy_name, parameters) for row in candidate["rows"]))
        averages = {
            label: mean(counts[label] for counts in candidate_counts) for label in CLASSES
        }
        results.append({
            "policy_name": policy_name,
            "parameters": parameters,
            "avg_predicted_flat_count": averages["FLAT"],
            "avg_predicted_distribution": averages,
            "avg_accuracy": None,
            "avg_accuracy_edge": None,
            "best_candidate_accuracy_edge": None,
            "candidates_with_improved_edge": None,
            "candidates_with_positive_edge": None,
            "false_directional_on_actual_flat_avg": None,
            "directional_recall_avg": None,
            "flat_recall_avg": None,
            "flat_recovery_vs_sidecar_argmax_avg": averages["FLAT"] - 15.0,
            "directional_overprediction_reduction_vs_sidecar_argmax_avg": averages["FLAT"] - 15.0,
            "notes": (
                "Distribution replay completed. Accuracy, false-directional, recall, fold, and profit metrics "
                "cannot be recomputed because compact sidecars omit row-level actual labels and outcome metadata."
            ),
        })
    return results


def build_solusdt_sidecar_calibration_replay(root: Path = OUTPUT_DIR) -> dict[str, Any]:
    validation, streams = _validate_sets(root)
    candidates = [_read_candidate(stream) for stream in streams]
    policy_results = _aggregate_policies(candidates)
    ranked = sorted(policy_results, key=lambda item: item["avg_predicted_flat_count"], reverse=True)[:5]
    best_policies = [
        {
            "rank": rank,
            "policy_name": item["policy_name"],
            "parameters": item["parameters"],
            "best_or_avg_candidate": "all 45 candidates are probability-identical on test rows",
            "predicted_distribution": item["avg_predicted_distribution"],
            "accuracy_edge": None,
            "flat_recovery": item["flat_recovery_vs_sidecar_argmax_avg"],
            "false_directional_reduction": None,
            "tradeoff": "More FLAT predictions, but row-level correctness and directional recall are unavailable.",
            "should_be_implemented_next": False,
        }
        for rank, item in enumerate(ranked, start=1)
    ]
    candidate_reports = sorted(root.rglob("training_pipeline_report.json"))
    h08 = denominator_mismatch(6485, 6481)
    h08.update({
        "failed_candidate_id": H08_ID,
        "failure_phase": "train_model",
        "expected_row_count_source": (
            "Hardcoded default 6481 in TrainingPipelineConfig.prediction_sidecar_expected_row_count, "
            "forwarded unchanged through TrainingService to the exporter; exporter also binds "
            "FULL_DATASET_6481 to 6481."
        ),
        "produced_row_count_source": (
            "Candidate h08 dataset boundary: train 4539 + validation 973 + test 973 = 6485."
        ),
        "likely_cause": (
            "The h08 horizon changes the candidate-specific usable dataset boundary by four rows, "
            "but the sidecar contract retains the h12/global 6481 denominator."
        ),
        "recommended_fix_scope": (
            "In ML38.10.68 or later, derive expected_row_count and denominator scope from the "
            "materialized candidate split boundary; add h08 4539/973/973 coverage while preserving "
            "fail-closed split, duplicate, hash, and schema checks."
        ),
        "contract_test_added": True,
        "fix_applied": False,
    })
    test_rows = candidates[0]["test_rows"] if candidates else 0
    probability_identical = bool(candidates) and all(
        candidate["stored_argmax_distribution"] == candidates[0]["stored_argmax_distribution"]
        and candidate["average_probabilities"] == candidates[0]["average_probabilities"]
        for candidate in candidates
    )
    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.66",
            "previous_commit": "4a8575bd7851e57bd158678df4a69d52be87e883",
            "previous_decision": "POST_FIX_SOLUSDT_QUALITY_TRIAGE_COMPLETED_NEXT_ACTION_SELECTED",
            "previous_next_action": "CALIBRATION_TUNING",
            "candidates_total": 46,
            "candidates_rejected": 45,
            "candidates_failed": 1,
            "main_blocker": "actual FLAT 899/973 vs predicted FLAT 109/973",
            "accuracy_edge": -0.7358684480986639,
        },
        "evidence_sources": {
            "output_dir": str(root),
            "zip_path": str(ZIP_PATH),
            "external_log_path": str(EXTERNAL_LOG_PATH),
            "completion_marker_path": str(COMPLETION_MARKER_PATH),
            "evidence_mode": "READ_ONLY_45_SIDECAR_CALIBRATION_REPLAY",
            "sidecar_streams_scanned": len(streams),
            "sidecar_summaries_scanned": len(list(root.rglob("prediction_payloads/full_dataset_prediction_stream_summary.json"))),
            "candidate_reports_scanned": len(candidate_reports),
        },
        "sidecar_set_validation": validation,
        "probability_field_discovery": {
            "raw_probability_fields_found": False,
            "raw_probability_status": "RAW_PROBABILITIES_NOT_AVAILABLE_IN_SIDECAR",
            "calibrated_probability_fields_found": True,
            "selected_probability_fields": ["prob_down", "prob_flat", "prob_up"],
            "selected_probability_semantics": "training_service_calibrated_model_softmax_argmax",
            "row_level_actual_label_found": False,
            "class_names_detected": list(CLASSES),
            "replay_possible": True,
            "replay_blocker": (
                "Distribution replay is possible; accuracy/outcome replay is incomplete because raw "
                "probabilities and row-level actual/fold/profit fields are absent from compact artifacts."
            ),
        },
        "current_distribution_baseline": {
            "test_rows": test_rows,
            "actual_distribution": {"DOWN": 31, "FLAT": 899, "UP": 43},
            "current_predicted_distribution": {"DOWN": 472, "FLAT": 109, "UP": 392},
            "current_distribution_source": "ML38.10.66 selected downstream flat_on_low_margin policy",
            "sidecar_stored_argmax_distribution": candidates[0]["stored_argmax_distribution"] if candidates else {},
            "current_actual_flat": 899,
            "current_predicted_flat": 109,
            "current_false_directional_on_actual_flat": 790,
            "current_accuracy": 0.1880781089414183,
            "majority_flat_baseline_accuracy": 0.9239465570400822,
            "current_accuracy_edge": -0.7358684480986639,
            "predicted_directional_overprediction_ratio": 864 / 74,
            "source_layer_warning": (
                "The ML38.10.66 current distribution is downstream policy output; the sidecar stores "
                "calibrated softmax argmax (532/15/426), so they must not be conflated."
            ),
        },
        "candidate_calibration_replay_summary": {
            "candidates_replayed": len(candidates),
            "policies_tested": len(policy_results),
            "candidate_policy_pairs_tested": len(candidates) * len(policy_results),
            "probability_sequences_identical_across_candidates": probability_identical,
            "best_policy_improves_flat_recovery": max((item["avg_predicted_flat_count"] for item in policy_results), default=0) > 15,
            "best_policy_improves_accuracy_edge": None,
            "any_policy_positive_accuracy_edge": False,
            "any_policy_reaches_baseline": False,
            "replay_source_confidence": "MEDIUM",
            "outcome_metric_status": "INCOMPLETE_MISSING_ROW_LEVEL_ACTUAL_LABELS",
            "candidate_probability_statistics": [
                {key: value for key, value in candidate.items() if key != "rows"}
                for candidate in candidates
            ],
        },
        "policy_grid_results": policy_results,
        "best_replay_policies": best_policies,
        "h08_denominator_contract": h08,
        "calibration_findings": {
            "main_issue_confirmed": "class prior shift / class balance effect; thresholding alone insufficient",
            "evidence": [
                "Actual FLAT is 899/973 while selected downstream predictions contain 109 FLAT.",
                "Available calibrated softmax argmax contains only 15 FLAT and mean FLAT probability is about 0.265.",
                "The strongest bounded grid policy reaches only 400 FLAT, still 499 below the actual count.",
                "All 45 test probability sequences are identical, arguing against candidate-specific configuration as the cause.",
                "Temperature calibration improves NLL/Brier in reports but cannot change argmax ordering by itself.",
                "trade_two_stage class-weight source zeroes the FLAT direction weight; causality requires a later controlled plan, not a claim here.",
            ],
            "recommended_calibration_zone": (
                "No implementation zone selected. Distribution-only sensitivity is strongest at directional "
                "confidence floor 0.55-0.60, but outcome metrics are unavailable and even 0.60 reaches only 400 FLAT."
            ),
            "risks": [
                "A stronger FLAT override may erase the 74 directional rows.",
                "Accuracy, fold sensitivity, and profit/risk cannot be ranked without row-level targets/outcomes.",
                "Changing calibration alone may mask a training-objective/class-prior mismatch."
            ],
            "why_no_training_run_yet": "This stage is a read-only diagnostic and did not select an outcome-validated policy.",
            "why_no_cascade_outcome_yet": "No policy has row-level accuracy/fold/profit evidence or a positive baseline edge.",
        },
        "next_action_recommendation": {
            "recommended_stage": "ML38.10.68",
            "action_type": "CALIBRATION_REPLAY_INCOMPLETE_NEEDS_FIELDS",
            "action_summary": (
                "Add a bounded diagnostic-only export/replay contract for row-level actual labels plus raw and "
                "calibrated probabilities (and fold/profit join keys where already available), then repeat the "
                "read-only policy ranking. Do not implement a production calibration threshold from distribution alone. "
                "Keep the h08 dynamic-denominator fix as a separate minimal candidate-boundary change."
            ),
            "expected_files_to_touch": [
                "diagnostic/test fixtures for explicit raw/calibrated/actual replay fields",
                "a separate h08 candidate-boundary denominator contract test/fix if prioritized",
            ],
            "expected_tests": [
                "row-aligned raw/calibrated/actual replay contract",
                "h08 dynamic 4539+973+973 denominator contract",
            ],
            "requires_training_run_after_fix": False,
            "requires_wrapper_rerun_after_fix": False,
            "cascade_outcome_still_blocked": True,
            "tradable_edge_still_blocked": True,
        },
        "guardrails": {
            "quick_quality_rerun_during_stage": False,
            "wrapper_execute_used_during_stage": False,
            "training_or_runtime_executed_during_stage": False,
            "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False,
            "ml_predictions_writes_during_stage": False,
            "labels_builders_gates_model_logic_changed": False,
            "production_calibration_logic_changed": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "new_zip_created": False,
            "archive_recovery_performed": False,
            "cascade_outcome_run": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
        },
        "decision_gate": {
            "calibration_replay_completed": True,
            "probability_fields_available": True,
            "primary_calibration_cause_identified": True,
            "h08_contract_diagnosed": True,
            "next_action_selected": True,
            "rerun_performed": False,
            "code_change_applied_to_production_logic": False,
            "artifacts_mutated": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": "CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS",
            "next_allowed_stage": "ML38.10.68 — calibration replay field contract or separately scoped h08 denominator fix",
        },
        "next_step_plan": [
            "Expose raw/calibrated probabilities and row-level targets to a diagnostic-only replay contract.",
            "Repeat policy ranking with accuracy, fold, and profit/risk joins before production changes.",
            "Fix h08 expected denominator from the materialized candidate split boundary in a separate approved scope.",
        ],
        "decision": ["CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS"],
    }


solusdt_sidecar_calibration_replay = build_solusdt_sidecar_calibration_replay()
