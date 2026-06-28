from __future__ import annotations

import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _write_summary(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ml38_10_26_3_root_cause_board_uses_candidate_results_source_of_truth(
    tmp_path: Path,
) -> None:
    summary = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2026-04-01",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv30_h12_long",
        "feature_version_used": "fv3_candle_ta_context",
        "gap_training_safe": True,
        "gap_severity_for_training": "OK",
        "candidate_results": [
            {
                "symbol": "SOLUSDT",
                "candidate_id": "c1",
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
                "profit_factor": 1.21,
                "profit_total_r": 6.06,
                "walk_forward_profit_factor": None,
                "walk_forward_total_r": 0.0,
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "research_only_total_r_repair_enabled": True,
                "failed_gates": ["walk_forward_gate", "research_only_validation_total_r_repair_gate"],
                "passed_gates": [],
                "worst_fold_root_cause": {
                    "diagnostic_status": "COMPLETED",
                    "fold_index": 1,
                    "validation_start": "2026-05-18T04:15:00+00:00",
                    "validation_end": "2026-05-28T04:15:00+00:00",
                    "validation_total_r": -5.9364,
                    "validation_signal_count": 110,
                    "validation_loss_count": 54,
                    "validation_loss_rate": 0.49,
                    "primary_root_cause": "large_negative_validation_total_r",
                    "root_cause_flags": [
                        "large_negative_validation_total_r",
                        "stop_or_mitigation_loss_dominates",
                        "losses_concentrated_in_time_slice",
                    ],
                    "outcome_counts": {"SL": 32, "EXIT_MITIGATED": 17, "TP": 45},
                    "time_slice_summary": [
                        {"time_slice": "2026-05-25", "total_r": -9.92, "signal_count": 10},
                        {"time_slice": "2026-05-28", "total_r": -7.75, "signal_count": 11},
                    ],
                    "outcome_summary": [
                        {"result": "SL", "total_r": -32.96, "signal_count": 32},
                        {"result": "EXIT_MITIGATED", "total_r": -11.05, "signal_count": 17},
                    ],
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
            }
        ],
    }

    summary_path = _write_summary(tmp_path / "summary.json", summary)
    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    board = result["walk_forward_fold_root_cause_board"]

    assert board["diagnostic_version"] == "ml38.10.26.3"
    assert board["candidate_count_with_root_cause"] == 1
    assert board["primary_root_cause_counts"]["large_negative_validation_total_r"] == 1
    assert board["worst_candidates"][0]["fold_index"] == 1
    assert board["worst_candidates"][0]["validation_total_r"] == -5.9364


def test_ml38_10_26_3_fold_1_repair_target_selection_finds_research_targets(
    tmp_path: Path,
) -> None:
    summary = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2026-04-01",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv30_h12_long",
        "feature_version_used": "fv3_candle_ta_context",
        "gap_training_safe": True,
        "gap_severity_for_training": "OK",
        "candidate_results": [
            {
                "symbol": "SOLUSDT",
                "candidate_id": "c1",
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
                "profit_factor": 1.21,
                "profit_total_r": 6.06,
                "walk_forward_profit_factor": 0.91,
                "walk_forward_total_r": -0.75,
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "research_only_total_r_repair_enabled": True,
                "failed_gates": ["walk_forward_gate", "research_only_validation_total_r_repair_gate"],
                "passed_gates": [],
                "worst_fold_root_cause": {
                    "diagnostic_status": "COMPLETED",
                    "fold_index": 1,
                    "validation_start": "2026-05-18T04:15:00+00:00",
                    "validation_end": "2026-05-28T04:15:00+00:00",
                    "validation_total_r": -5.9364,
                    "validation_signal_count": 110,
                    "validation_loss_count": 54,
                    "validation_loss_rate": 0.49,
                    "primary_root_cause": "large_negative_validation_total_r",
                    "root_cause_flags": [
                        "large_negative_validation_total_r",
                        "stop_or_mitigation_loss_dominates",
                        "losses_concentrated_in_time_slice",
                    ],
                    "outcome_counts": {"SL": 32, "EXIT_MITIGATED": 17, "TP": 45},
                    "time_slice_summary": [
                        {"time_slice": "2026-05-25", "total_r": -9.92, "signal_count": 10},
                        {"time_slice": "2026-05-28", "total_r": -7.75, "signal_count": 11},
                    ],
                    "outcome_summary": [
                        {"result": "SL", "total_r": -32.96, "signal_count": 32},
                        {"result": "EXIT_MITIGATED", "total_r": -11.05, "signal_count": 17},
                    ],
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
            }
        ],
    }

    summary_path = _write_summary(tmp_path / "summary.json", summary)
    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    selection = result["fold_1_repair_target_selection"]

    assert selection["diagnostic_version"] == "ml38.10.26.3"
    assert selection["target_fold_index"] == 1
    assert selection["selected_target_count"] == 1
    target = selection["selected_targets"][0]
    assert target["side_profile"] == "long_only_research"
    assert target["validation_total_r"] == -5.9364
    assert "do_not_relax_threshold_only" in target["recommended_repair_actions"]
    assert "time_slice_blackout_or_event_cluster_probe" in target["recommended_repair_actions"]
    assert "exit_mitigation_or_stop_loss_repair_probe" in target["recommended_repair_actions"]


def test_ml38_10_26_3_root_cause_fields_are_merged_into_configs_ranked(
    tmp_path: Path,
) -> None:
    summary = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2026-04-01",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv30_h12_long",
        "feature_version_used": "fv3_candle_ta_context",
        "gap_training_safe": True,
        "gap_severity_for_training": "OK",
        "candidate_results": [
            {
                "symbol": "SOLUSDT",
                "candidate_id": "c1",
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "worst_fold_root_cause": {
                    "diagnostic_status": "COMPLETED",
                    "fold_index": 1,
                    "validation_total_r": -5.9364,
                    "primary_root_cause": "large_negative_validation_total_r",
                },
                "fold_root_cause_count": 1,
                "primary_validation_root_cause_counts": {
                    "large_negative_validation_total_r": 1
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
                "candidate_status": "REJECTED",
                "score": 10.0,
            }
        ],
    }

    summary_path = _write_summary(tmp_path / "summary.json", summary)
    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    row = next(
        item
        for item in result["configs_ranked"]
        if item.get("config_id") == "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe"
    )
    assert row["worst_fold_root_cause"]["fold_index"] == 1
    assert row["fold_root_cause_count"] >= 0
