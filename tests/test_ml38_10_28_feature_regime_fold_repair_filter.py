from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def test_ml38_10_28_lv32_configs_registered_and_research_only() -> None:
    expected = {
        "lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe",
        "lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
        "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe",
        "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
        "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_feature_guard_probe",
        "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_strict_feature_guard_exit45_probe",
    }
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    matrix = ML382FV3TuningMatrix().build()
    matrix_ids = {item["config_id"] for item in matrix["configs"]}

    assert expected <= set(configs_by_id)
    assert expected <= matrix_ids

    for config_id in expected:
        payload = configs_by_id[config_id]
        assert payload["research_only_fold_repair_probe_enabled"] is True
        assert (
            payload["research_only_acceptance_block_reason"]
            == "research_only_feature_regime_fold_repair_probe"
        )
        assert payload["fold_repair_feature_filter_enabled"] is True
        assert payload["fold_repair_time_slice_blackout_enabled"] is False
        assert payload["fold_repair_blackout_dates"] == []


def test_ml38_10_28_runtime_counts() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(
            ["--quick-quality", "--quick-quality-symbol", "SOLUSDT"]
        )
    )

    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 20
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 42
    assert fast_wrapper._expected_candidate_count() == 40
    assert quick_wrapper._expected_candidate_count() == 42


def _row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "predicted_label": "UP",
        "entry_path_original_predicted_label": "UP",
        "entry_path_filtered_predicted_label": "UP",
        "actual_label": "UP",
        "prob_up": 0.85,
        "prob_down": 0.05,
        "prob_flat": 0.10,
        "confidence": 0.85,
        "margin": 0.75,
        "directional_edge": 0.70,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [{"high": 101.4, "low": 99.9, "close": 101.0}],
        "future_move_atr": 1.0,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": False,
        "entry_path_filter_block_reason": None,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_filter_mae_threshold": 0.52,
        "entry_path_quality_score": 0.80,
        "setup_quality_score": 0.70,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
        "market_regime": "trend_up",
        "timestamp": "2026-05-25T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_ml38_10_28_feature_filter_removes_by_features_not_dates() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    result = evaluator.evaluate_single_gate(
        predictions=[
            _row(timestamp="2026-05-25T00:00:00Z"),
            _row(timestamp="2026-05-26T00:00:00Z", stop_pressure_risk_score=0.80),
            _row(timestamp="2026-05-28T00:00:00Z", mae_pressure_risk_score=0.80),
            _row(timestamp="2026-05-29T00:00:00Z", entry_path_quality_score=0.40),
            _row(timestamp="2026-05-30T00:00:00Z", market_regime="high_volatility"),
        ],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.5,
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        research_only_fold_repair_probe_enabled=True,
        fold_repair_probe_profile="LONG_ONLY_FEATURE_GUARD",
        fold_repair_feature_filter_enabled=True,
        fold_repair_feature_filter_profile="FEATURE_GUARD_V1",
        fold_repair_feature_filter_rules={
            "min_entry_path_quality_score": 0.74,
            "min_setup_quality_score": 0.62,
            "max_stop_pressure_risk_score": 0.42,
            "max_mae_pressure_risk_score": 0.48,
            "blocked_regime_values": ["high_volatility"],
        },
    )

    summary = result["summary"]["fold_feature_regime_filter_summary"]
    assert summary["enabled"] is True
    assert summary["date_blackout_used"] is False
    assert summary["removed_signal_count"] == 4
    assert summary["output_signal_count"] == 1
    assert summary["removed_counts_by_reason"]["high_stop_pressure"] == 1
    assert summary["removed_counts_by_reason"]["high_mae_pressure"] == 1
    assert summary["removed_counts_by_reason"]["low_entry_path_quality"] == 1
    assert summary["removed_counts_by_reason"]["blocked_regime"] == 1


def test_ml38_10_28_feature_regime_probe_board_compares_against_date_blackout() -> None:
    result = FoldFeatureRegimeRepairProbe().analyze(
        [
            {
                "symbol": "SOLUSDT",
                "config_id": "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
                "candidate_id": "feature",
                "candidate_status": "REJECTED",
                "fold_repair_feature_filter_enabled": True,
                "fold_repair_feature_filter_profile": "FEATURE_GUARD_V1_EXIT45",
                "fold_repair_probe_profile": "LONG_ONLY_FEATURE_GUARD_EXIT45",
                "profit_factor": 1.2,
                "profit_total_r": 4.0,
                "walk_forward_profit_factor": 1.01,
                "walk_forward_total_r": 1.0,
                "failed_gates": ["research_only_fold_1_exit_time_slice_repair_probe_gate"],
                "profit_aware_diagnostics": {
                    "fold_feature_regime_filter_summary": {"removed_signal_count": 3}
                },
            },
            {
                "symbol": "SOLUSDT",
                "config_id": "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
                "candidate_id": "date",
                "candidate_status": "REJECTED",
                "fold_repair_time_slice_blackout_enabled": True,
                "profit_factor": 1.4,
                "profit_total_r": 9.8,
                "walk_forward_profit_factor": 1.09,
                "walk_forward_total_r": 3.5,
                "profit_aware_diagnostics": {
                    "fold_time_slice_blackout_summary": {"removed_signal_count": 20}
                },
            },
        ]
    )

    assert result["diagnostic_name"] == "fold_feature_regime_repair_probe"
    assert result["feature_regime_probe_candidate_count"] == 1
    assert result["date_blackout_probe_candidate_count"] == 1
    assert result["best_feature_regime_probe"]["config_id"].startswith("lv32_")
    assert result["best_date_blackout_probe"]["config_id"].startswith("lv31_")
    assert "do_not_accept_lv32" in result["warnings"]


def test_ml38_10_28_configs_ranked_preserves_feature_filter_fields() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
        "best_candidate_score": 1.0,
        "feature_version_used": "fv4_book_setup_context",
        "gap_training_safe": True,
        "gap_severity_for_training": "OK",
        "warnings": [],
        "reasons_why_best_still_rejected": [],
        "candidate_results": [
            {
                "candidate_id": "c1",
                "config_id": "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
                "candidate_status": "REJECTED",
                "status": "COMPLETED",
                "score": 1.0,
                "failed_gates": [
                    "research_only_fold_1_exit_time_slice_repair_probe_gate"
                ],
                "fold_repair_feature_filter_enabled": True,
                "fold_repair_feature_filter_profile": "FEATURE_GUARD_V1_EXIT45",
                "fold_repair_feature_filter_rules": {
                    "max_stop_pressure_risk_score": 0.42
                },
                "fold_feature_regime_filter_summary": {"removed_signal_count": 3},
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
                "candidate_id": "c1",
                "score": 1.0,
                "candidate_status": "REJECTED",
            }
        ],
    }

    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(summary)
    row = result["configs_ranked"][0]
    assert row["fold_repair_feature_filter_enabled"] is True
    assert row["fold_repair_feature_filter_profile"] == "FEATURE_GUARD_V1_EXIT45"
    assert (
        row["fold_repair_feature_filter_rules"]["max_stop_pressure_risk_score"]
        == 0.42
    )
    assert row["fold_feature_regime_filter_summary"]["removed_signal_count"] == 3
