from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.diagnostics.walk_forward_profit_diagnostics import (
    WalkForwardProfitDiagnostics,
)
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.training.training_pipeline_runner import TrainingPipelineRunner


def test_profit_aware_diagnostics_preserves_best_gate_feature_summary():
    profit_aware_summary = {
        "gate_results": [
            {
                "gate_type": "max_prob",
                "threshold": 0.34,
                "resolved_signal_count": 82,
                "profit_factor": 1.37,
                "total_r": 9.04,
                "fold_feature_regime_filter_summary": {
                    "diagnostic_name": "fold_feature_regime_filter_summary",
                    "removed_signal_count": 1,
                    "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
                    "removed_counts_by_date": {"2026-06-09": 1},
                },
            }
        ],
        "summary": {"profit_factor": 1.37, "total_r": 9.04},
    }

    payload = WalkForwardProfitDiagnostics().build_profit_aware_diagnostics(
        profit_aware_summary=profit_aware_summary
    )

    assert payload["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1
    assert payload["best_gate"]["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1


def test_training_pipeline_extracts_best_gate_repair_summary_from_gate_results():
    runner = TrainingPipelineRunner()
    profit_aware_summary = {
        "gate_results": [
            {
                "gate_type": "max_prob",
                "threshold": 0.34,
                "resolved_signal_count": 82,
                "profit_factor": 1.37,
                "total_r": 9.04,
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 1,
                    "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
                },
            }
        ]
    }
    profit_aware_diagnostics = {
        "best_gate": {"gate_type": "max_prob", "threshold": 0.34}
    }

    payload = runner._extract_best_gate_repair_summaries(
        profit_aware_summary=profit_aware_summary,
        profit_aware_diagnostics=profit_aware_diagnostics,
    )

    assert payload["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1


def test_training_pipeline_attaches_repair_summaries_to_quality_payload():
    runner = TrainingPipelineRunner()
    payload = {
        "profit_aware_diagnostics": {
            "best_gate": {"gate_type": "max_prob", "threshold": 0.34}
        }
    }
    repair_summaries = {
        "fold_feature_regime_filter_summary": {
            "removed_signal_count": 1,
            "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
        },
        "fold_time_slice_blackout_summary": {
            "removed_signal_count": 3,
        },
    }

    runner._attach_repair_summaries_to_quality_payload(
        payload,
        repair_summaries=repair_summaries,
    )

    assert payload["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1
    assert payload["fold_repair_probe_diagnostics"]["removed_signal_count"] == 3
    assert payload["profit_aware_diagnostics"]["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1
    assert payload["profit_aware_diagnostics"]["best_gate"]["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1


def test_label_grid_nested_summary_reads_profit_aware_best_gate():
    quality_payload = {
        "profit_aware_diagnostics": {
            "best_gate": {
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 2,
                }
            }
        }
    }

    payload = LabelGridExperimentRunner._profit_aware_nested_summary(
        quality_payload,
        "fold_feature_regime_filter_summary",
    )

    assert payload["removed_signal_count"] == 2


def test_fold_feature_regime_probe_reads_nested_best_gate_summary():
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
            "fold_repair_feature_filter_enabled": True,
            "profit_aware_diagnostics": {
                "best_gate": {
                    "fold_feature_regime_filter_summary": {
                        "removed_signal_count": 1,
                        "input_signal_count": 82,
                        "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
                        "removed_counts_by_date": {"2026-06-09": 1},
                        "removed_counts_by_regime": {"missing": 1},
                    }
                }
            },
            "profit_total_r": 9.0,
            "profit_factor": 1.37,
            "walk_forward_total_r": 0.0,
        }
    ]

    result = FoldFeatureRegimeRepairProbe().analyze(candidates)

    assert result["feature_filter_diagnostics"]["readiness"] == "DIAGNOSTICS_READY"
    assert result["feature_filter_diagnostics"]["active_filter_candidate_count"] == 1
    assert result["feature_filter_diagnostics"]["aggregate_primary_removed_counts_by_reason"] == {
        "low_entry_path_quality": 1
    }
