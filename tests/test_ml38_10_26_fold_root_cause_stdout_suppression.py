from __future__ import annotations

import json

from app.cli.commands import build_ml38_2_fv3_tuning_stdout_payload
from app.diagnostics.walk_forward_fold_root_cause_diagnostics import (
    WalkForwardFoldRootCauseDiagnostics,
)
from app.diagnostics.walk_forward_validation_candidate_board import (
    WalkForwardValidationCandidateBoard,
)


def test_ml38_10_26_minimal_stdout_payload_excludes_heavy_fields() -> None:
    payload = {
        "status": "ok",
        "experiment_id": "exp1",
        "symbol": "SOLUSDT",
        "candidate_count": 21,
        "accepted_candidate_count": 0,
        "failed_candidate_count": 0,
        "summary_json_path": "reports/x/feature_regime_experiment_summary.json",
        "candidate_results": [
            {
                "candidate_id": "c1",
                "config_id": "lv30_h12",
                "candidate_status": "REJECTED",
                "profit_factor": 1.2,
                "profit_total_r": 6.0,
                "walk_forward_profit_diagnostics": {"folds": [{"huge": "x" * 1000}]},
            }
        ],
        "ranking": [{"huge": "x" * 1000}],
        "configs_ranked": [{"huge": "x" * 1000}],
    }

    result = build_ml38_2_fv3_tuning_stdout_payload(
        payload,
        stdout_payload_profile="minimal",
    )
    text = json.dumps(result)

    assert result["stdout_payload_profile"] == "minimal"
    assert result["stdout_payload_suppressed_heavy_fields"] is True
    assert result["candidate_count"] == 21
    assert "candidate_results" not in result
    assert "ranking" not in result
    assert "configs_ranked" not in result
    assert "walk_forward_profit_diagnostics" not in text
    assert len(text) < 10_000


def test_ml38_10_26_fold_root_cause_detects_loss_concentration() -> None:
    fold = {
        "fold_index": 1,
        "validation_start": "2026-04-20",
        "validation_end": "2026-05-01",
    }
    gate = {"gate_type": "opportunity_probability", "threshold": 0.65}
    signal_rows = [
        {
            "signal_direction": "LONG",
            "entry_path_bucket": "pullback",
            "regime_label": "range",
            "setup_quality_score": 0.2,
            "stop_pressure_risk_score": 0.9,
            "mae_pressure_risk_score": 0.8,
        },
        {
            "signal_direction": "LONG",
            "entry_path_bucket": "pullback",
            "regime_label": "range",
            "setup_quality_score": 0.2,
            "stop_pressure_risk_score": 0.9,
            "mae_pressure_risk_score": 0.8,
        },
        {
            "signal_direction": "LONG",
            "entry_path_bucket": "breakout",
            "regime_label": "trend_up",
            "setup_quality_score": 0.8,
            "stop_pressure_risk_score": 0.1,
            "mae_pressure_risk_score": 0.1,
        },
    ]
    outcomes = [
        {"result": "SL", "net_r": -1.02},
        {"result": "EXIT_MITIGATED", "net_r": -0.52},
        {"result": "TP", "net_r": 1.48},
    ]

    report = WalkForwardFoldRootCauseDiagnostics().analyze(
        fold=fold,
        gate=gate,
        signal_rows=signal_rows,
        outcomes=outcomes,
    )

    assert report["diagnostic_status"] == "COMPLETED"
    assert report["validation_signal_count"] == 3
    assert report["validation_loss_count"] == 2
    assert "stop_or_mitigation_loss_dominates" in report["root_cause_flags"]
    assert "low_setup_quality_bucket_negative" in report["root_cause_flags"]
    assert "high_stop_pressure_bucket_negative" in report["root_cause_flags"]


def test_ml38_10_26_candidate_board_exposes_worst_fold_root_cause() -> None:
    walk_forward_summary = {
        "folds": [
            {
                "fold_index": 1,
                "selected_gate": None,
                "gate_reject_reason": "no_validation_gate_passed",
                "validation_gate_selection_diagnostics": {
                    "failure_reason_counts": {"total_r_below_min": 2},
                    "best_failed_gate_by_distance_to_pass": {
                        "gate_type": "opportunity_probability",
                        "threshold": 0.65,
                        "total_r": -5.9,
                        "threshold_deficits": {"total_r_deficit": 4.6},
                        "primary_blocker": "total_r_below_min",
                        "repair_hint": "total_r_deficit_too_large_feature_repair_needed",
                    },
                    "total_r_failure_candidate_board": {
                        "recommended_validation_repair_profile": "NO_THRESHOLD_REPAIR_RECOMMENDED",
                        "verdict": "TOTAL_R_DEFICIT_TOO_LARGE_FEATURE_REPAIR_NEEDED",
                    },
                },
                "validation_fold_root_cause": {
                    "diagnostic_status": "COMPLETED",
                    "fold_index": 1,
                    "validation_total_r": -5.9,
                    "primary_root_cause": "large_negative_validation_total_r",
                    "root_cause_flags": ["large_negative_validation_total_r"],
                },
            }
        ]
    }

    board = WalkForwardValidationCandidateBoard().analyze(
        walk_forward_summary=walk_forward_summary
    )

    assert board["diagnostic_version"] == "ml38.10.26"
    assert board["fold_root_cause_count"] == 1
    assert board["primary_root_cause_counts"]["large_negative_validation_total_r"] == 1
    assert board["worst_fold_root_cause"]["fold_index"] == 1
