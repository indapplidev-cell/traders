from __future__ import annotations

from typing import Any


DIAGNOSTIC_NAME = "model_quality_post_fix_solusdt_triage"
DIAGNOSTIC_VERSION = "ml38.10.66"
EXECUTION_MODE = (
    "READ_ONLY_POST_FIX_SOLUSDT_QUALITY_TRIAGE_NO_TRAINING_NO_RERUN"
)


def _reason_group(
    count: int | str,
    examples: list[str],
    severity: str,
    actionability: str,
) -> dict[str, Any]:
    return {
        "count": count,
        "examples": examples,
        "severity": severity,
        "actionability": actionability,
    }


def build_model_quality_post_fix_solusdt_triage() -> dict[str, Any]:
    """Return the read-only ML38.10.66 triage of the successful real run."""
    output_dir = (
        "D:\\disk_E\\game_projects\\traders\\traders-ml\\reports\\"
        "feature_regime_experiments\\"
        "quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_151645"
    )
    label_grid_root = (
        output_dir
        + "\\per_symbol_experiments\\"
        "fv3_cached_fresh_tuning_solusdt_15m_20260707_151645\\"
        "label_grid_runtime\\"
        "fv3_cached_fresh_tuning_solusdt_15m_20260707_151645_label_grid"
    )
    failed_id = (
        "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax"
    )
    summary_path = label_grid_root + "\\label_grid_experiment_summary.json"
    failed_report_path = (
        label_grid_root
        + "\\pipeline_runs\\"
        "fv3_cached_fresh_tuning_solusdt_15m_20260707_151645_label_grid_"
        + failed_id
        + "\\training_pipeline_report.json"
    )

    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "execution_mode": EXECUTION_MODE,
        "previous_stage_summary": {
            "previous_stage": "ML38.10.65",
            "previous_base_commit": "374f09a86b90a935c8d7eef86bbfcfbeb6bc37c6",
            "previous_decision": "POST_FIX_SOLUSDT_QUICK_QUALITY_RERUN_PASSED",
            "wrapper_exit_code": 0,
            "child_exit_code": 0,
            "typeerror_repeated": False,
            "sidecar_sets_valid": 45,
            "quality_note": "1 failed, 45 rejected",
        },
        "evidence_sources": {
            "output_dir": output_dir,
            "zip_path": output_dir + ".zip",
            "external_log_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_181639.log"
            ),
            "completion_marker_path": (
                "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\"
                "solusdt_quick_quality_20260707_181639.completion.json"
            ),
            "evidence_mode": "READ_ONLY_LATEST_SUCCESSFUL_SOLUSDT_RUN",
            "files_scanned_count": 435,
            "json_files_scanned_count": 244,
            "md_files_scanned_count": 141,
        },
        "candidate_status_summary": {
            "total_candidates": 46,
            "passed_candidates": 0,
            "accepted_candidates": 0,
            "rejected_candidates": 45,
            "failed_candidates": 1,
            "unknown_candidates": 0,
            "status_source_confidence": "HIGH",
            "candidate_status_source_files": [
                summary_path,
                output_dir + "\\multi_symbol_feature_regime_analysis.json",
                output_dir
                + "\\per_symbol_experiments\\"
                "fv3_cached_fresh_tuning_solusdt_15m_20260707_151645\\"
                "feature_regime_experiment_summary.json",
            ],
        },
        "failed_candidate_analysis": {
            "failed_candidate_found": True,
            "failed_candidate_id": failed_id,
            "failed_candidate_name": failed_id,
            "failed_candidate_path": failed_report_path,
            "failed_reason": (
                "full-dataset prediction sidecar is not ready: row_count 6485 "
                "does not equal expected_row_count 6481"
            ),
            "failed_phase": "train_model",
            "failed_traceback_present": False,
            "failed_is_typeerror_repeat": False,
            "failed_is_sidecar_export_failure": True,
            "failed_is_quality_eval_failure": False,
            "recommended_action_for_failed_candidate": (
                "Before retrying h08, make the sidecar denominator/expected row count "
                "derive from the candidate dataset boundary and add a targeted h08 "
                "contract test; do not normalize or rewrite this real artifact."
            ),
        },
        "rejected_candidate_analysis": {
            "rejected_candidates_count": 45,
            "top_rejection_reasons": [
                {"reason": "baseline_edge_gate", "count": 45},
                {"reason": "walk_forward_gate", "count": 38},
                {
                    "reason": "research_only_fold_1_exit_time_slice_repair_probe_gate",
                    "count": 25,
                },
                {"reason": "profit_aware_gate", "count": 16},
                {
                    "reason": "research_only_validation_total_r_repair_gate",
                    "count": 2,
                },
            ],
            "common_gate_failures": [
                "baseline_edge_gate: 45/45",
                "walk_forward_gate: 38/45",
                "profit_aware_gate: 16/45",
            ],
            "rejection_examples": [
                {
                    "config_id": (
                        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_"
                        "long_bad_dates_exit45_probe"
                    ),
                    "rank": 1,
                    "failed_gates": [
                        "baseline_edge_gate",
                        "research_only_fold_1_exit_time_slice_repair_probe_gate",
                    ],
                    "profit_factor": 1.4073880546739959,
                    "walk_forward_profit_factor": 1.0716948164711737,
                },
                {
                    "config_id": (
                        "lv26_h12_tts_thr065_sqmask060_epq072_sp043_"
                        "recovery_guard_strict"
                    ),
                    "rank": 3,
                    "failed_gates": ["baseline_edge_gate", "profit_aware_gate"],
                    "walk_forward_profit_factor": 1.114912058801216,
                },
                {
                    "config_id": "lv19_h12_tts_thr065_sqmask060",
                    "rank": 37,
                    "failed_gates": [
                        "baseline_edge_gate",
                        "profit_aware_gate",
                        "walk_forward_gate",
                    ],
                },
            ],
            "all_rejected_due_to_same_primary_reason": True,
            "rejection_source_confidence": "HIGH",
        },
        "rejection_reason_groups": {
            "gate_policy": _reason_group(
                45,
                [
                    "baseline_edge_gate failed for 45/45 rejected candidates",
                    "model_accuracy=0.188078 vs FLAT-majority baseline_accuracy=0.923947",
                ],
                "HIGH",
                "HIGH",
            ),
            "walk_forward_stability": _reason_group(
                38,
                [
                    "walk_forward_gate failed for 38 candidates",
                    "only 8 candidates had positive walk-forward PF and total R",
                    "worst audited fold: validation_total_r=-37.2088",
                ],
                "HIGH",
                "HIGH",
            ),
            "directional_coverage": _reason_group(
                45,
                [
                    "test actual directional rows=74/973 (31 DOWN, 43 UP)",
                    "directional sample is sparse while predictions are 864/973 directional",
                ],
                "HIGH",
                "HIGH",
            ),
            "calibration": _reason_group(
                45,
                [
                    "actual FLAT=899/973 but predicted FLAT=109/973",
                    "avg probabilities: DOWN=0.37344, FLAT=0.26507, UP=0.36149",
                    "selected baseline edge=-0.735868 despite distribution-safe policy",
                ],
                "HIGH",
                "HIGH",
            ),
            "class_balance": _reason_group(
                45,
                [
                    "test actual ratios: DOWN=3.19%, FLAT=92.39%, UP=4.42%",
                    "majority baseline accuracy=0.923947",
                ],
                "HIGH",
                "HIGH",
            ),
            "label_distribution": _reason_group(
                45,
                [
                    "all 45 completed candidates expose the same test actual counts 31/899/43",
                    "no-trade/FLAT dominance makes baseline separation the binding test",
                ],
                "HIGH",
                "MEDIUM",
            ),
            "profit_risk_proxy": _reason_group(
                16,
                [
                    "profit_aware_gate failed for 16 candidates",
                    "31 candidates had positive full-sample PF and total R",
                    "stop/mitigation loss dominates the audited worst walk-forward fold",
                ],
                "HIGH",
                "HIGH",
            ),
            "data_quality": _reason_group(
                0,
                [
                    "45 completed candidates report zero effective training gaps",
                    "the h08 row-count mismatch is a failed-candidate contract issue, not a rejection",
                ],
                "LOW",
                "MEDIUM",
            ),
            "config_consistency": _reason_group(
                0,
                [
                    "45 sidecar config-consistency validations passed",
                    "no label substitution was detected",
                ],
                "LOW",
                "LOW",
            ),
            "other": _reason_group(
                27,
                [
                    "25 candidates failed the research-only fold-1 repair probe gate",
                    "2 candidates failed the research-only validation total-R repair gate",
                    "all 45 completed results set collapse_detected=true with collapse_type=NONE",
                ],
                "MEDIUM",
                "MEDIUM",
            ),
        },
        "quality_blocker_ranking": [
            {
                "rank": 1,
                "blocker": "Negative edge versus the FLAT-majority baseline",
                "evidence": "baseline_edge_gate failed 45/45; accuracy edge=-0.735868",
                "affected_candidates_count": 45,
                "why_it_matters": "No candidate can be accepted without model separation.",
                "proposed_next_action": (
                    "Replay calibration/decision policy from existing sidecars before retraining."
                ),
            },
            {
                "rank": 2,
                "blocker": "Probability calibration and label/prediction distribution mismatch",
                "evidence": "actual FLAT 899 versus predicted FLAT 109 on 973 test rows",
                "affected_candidates_count": 45,
                "why_it_matters": (
                    "The model assigns most mass to directional classes on a FLAT-heavy target."
                ),
                "proposed_next_action": (
                    "Measure raw versus calibrated probabilities and bounded FLAT-policy sensitivity."
                ),
            },
            {
                "rank": 3,
                "blocker": "Walk-forward instability",
                "evidence": "walk_forward_gate failed 38/45; only 8 positive WF candidates",
                "affected_candidates_count": 38,
                "why_it_matters": "Full-sample positives do not generalize consistently by fold.",
                "proposed_next_action": (
                    "Require calibration candidates to improve every fold, not aggregate score only."
                ),
            },
            {
                "rank": 4,
                "blocker": "Research-only repair dependence",
                "evidence": "27 candidates failed an explicit research-only repair gate",
                "affected_candidates_count": 27,
                "why_it_matters": "These probes cannot establish an acceptable candidate.",
                "proposed_next_action": "Exclude research-only repairs from acceptance conclusions.",
            },
            {
                "rank": 5,
                "blocker": "Profit/risk proxy weakness",
                "evidence": "profit_aware_gate failed 16 candidates",
                "affected_candidates_count": 16,
                "why_it_matters": "Classification changes must also survive risk-aware evaluation.",
                "proposed_next_action": "Retain existing profit/risk gates in the replay.",
            },
            {
                "rank": 6,
                "blocker": "h08 sidecar denominator contract mismatch",
                "evidence": "6485 produced rows versus fixed expected 6481",
                "affected_candidates_count": 1,
                "why_it_matters": "The h08 candidate never reached quality evaluation.",
                "proposed_next_action": "Fix and test dynamic candidate dataset row expectations first.",
            },
        ],
        "sidecar_context": {
            "sidecar_sets_found": 45,
            "sidecar_sets_valid": 45,
            "latest_sidecar_sha256": (
                "5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4"
            ),
            "latest_sidecar_size_bytes": 6837243,
            "exact_byte_valid": True,
            "lf_only_valid": True,
            "schema_valid": True,
            "summary_contract_valid": True,
            "runtime_truth_valid": True,
            "archive_valid": True,
            "label_substitution_detected": False,
            "sidecar_bytes_not_mutated": True,
        },
        "model_quality_context": {
            "label_version": "multiple h12 versions; best=lv31_h12_dates_exit45_long",
            "feature_version": "fv4_book_setup_context",
            "symbol": "SOLUSDT",
            "interval": "15m",
            "horizon": 12,
            "row_count": 6481,
            "splits": {"train": 4536, "val": 972, "test": 973},
            "prediction_distribution": {"DOWN": 472, "FLAT": 109, "UP": 392},
            "label_distribution": {"DOWN": 31, "FLAT": 899, "UP": 43},
            "directional_coverage": {
                "actual_directional_rows": 74,
                "actual_directional_ratio": 0.07605344295991778,
                "predicted_directional_rows": 864,
                "predicted_directional_ratio": 0.8879753340184995,
            },
            "model_family": "candle_mlp / trade_two_stage",
            "quality_status": "QUALITY_REJECTED",
            "baseline_metrics": {
                "majority_flat_accuracy": 0.9239465570400822,
            },
            "candidate_metrics": {
                "model_accuracy": 0.1880781089414183,
                "accuracy_edge": -0.7358684480986639,
                "positive_full_profit_candidates": 31,
                "positive_walk_forward_candidates": 8,
                "best_candidate_profit_factor": 1.4073880546739959,
                "best_candidate_walk_forward_profit_factor": 1.0716948164711737,
            },
        },
        "next_training_quality_action": {
            "recommended_stage": "ML38.10.67",
            "action_type": "CALIBRATION_TUNING",
            "action_summary": (
                "Build a read-only sidecar calibration/decision-policy replay across the "
                "45 valid candidates, quantify raw-versus-calibrated FLAT recovery and "
                "per-fold baseline/profit effects, and select a bounded calibration zone "
                "before authorizing another real training run. Separately add an h08 "
                "dynamic-row-count contract test before that candidate is retried."
            ),
            "why_this_action": (
                "All rejected candidates share the baseline failure and the same severe "
                "actual-versus-predicted distribution mismatch. Existing exact sidecars "
                "contain probabilities and labels, so this hypothesis can be tested in "
                "minutes without another multi-hour run or gate relaxation."
            ),
            "expected_files_to_touch": [
                "app/diagnostics/solusdt_sidecar_calibration_replay.py",
                "tests/test_ml38_10_67_solusdt_sidecar_calibration_replay.py",
                "reports/stage_ml38_10_67_solusdt_calibration_replay_report.md",
                "tests/test_prediction_sidecar_wiring.py (h08 denominator contract only)",
                (
                    "app/labels/label_quality_grid.py only in a later stage if replay "
                    "evidence selects a calibration zone"
                ),
            ],
            "expected_run_command": (
                "python -m pytest "
                "tests/test_ml38_10_67_solusdt_sidecar_calibration_replay.py; "
                "then run the ML38.10.67 read-only replay against the latest 45 sidecars "
                "(no run_fv3_cached_tuning.py)"
            ),
            "expected_runtime": "minutes for replay; no real training in ML38.10.67",
            "requires_real_training_run": False,
            "requires_code_change_first": True,
            "requires_full_pytest_before_run": False,
            "still_blocks_cascade_outcome": True,
            "still_blocks_tradable_edge_claim": True,
        },
        "guardrails": {
            "quick_quality_rerun_during_stage": False,
            "wrapper_execute_used_during_stage": False,
            "training_or_runtime_executed_during_stage": False,
            "db_writes_during_stage": False,
            "ml_labels_writes_during_stage": False,
            "ml_predictions_writes_during_stage": False,
            "labels_builders_gates_model_logic_changed": False,
            "analyzer_logic_changed": False,
            "existing_real_artifacts_mutated": False,
            "new_real_sidecars_created": False,
            "new_zip_created": False,
            "archive_recovery_performed": False,
            "cascade_outcome_run": False,
            "production_like_recompute": False,
            "tradable_edge_confirmed": False,
        },
        "decision_gate": {
            "quality_triage_completed": True,
            "latest_run_successfully_parsed": True,
            "primary_quality_blockers_identified": True,
            "next_training_action_selected": True,
            "rerun_performed": False,
            "code_change_applied": False,
            "cascade_outcome_allowed_now": False,
            "production_like_recompute_allowed_now": False,
            "tradable_edge_claim_allowed_now": False,
            "decision": (
                "POST_FIX_SOLUSDT_QUALITY_TRIAGE_COMPLETED_NEXT_ACTION_SELECTED"
            ),
            "next_allowed_stage": (
                "ML38.10.67 — selected next training/quality action"
            ),
        },
        "next_step_plan": [
            "Implement read-only calibration replay over the 45 valid sidecars.",
            "Rank bounded policies by baseline edge, fold stability, and profit/risk proxies.",
            "Add an h08 dynamic sidecar-row-count contract test without retrying the run.",
            "Authorize a new SOLUSDT real run only after a replay-supported change is selected.",
        ],
        "decision": [
            "POST_FIX_SOLUSDT_QUALITY_TRIAGE_COMPLETED_NEXT_ACTION_SELECTED"
        ],
    }


model_quality_post_fix_solusdt_triage = (
    build_model_quality_post_fix_solusdt_triage()
)
