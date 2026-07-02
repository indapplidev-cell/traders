from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_2_FV3_TUNING_CONFIG_IDS
from app.labels.label_quality_grid import LabelQualityGridPlanner
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS


EXPECTED_LV33_IDS = {
    "lv33_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_probe",
    "lv33_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_adaptive_feature_guard_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_adaptive_feature_guard_exit45_probe",
}


def _row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "timestamp": "2026-05-25T00:00:00Z",
        "entry_path_quality_score": 0.80,
        "setup_quality_score": 0.70,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
        "market_regime": "trend_up",
        "signal_direction": "LONG",
    }
    payload.update(overrides)
    return payload


def test_ml38_10_29_evaluator_summary_is_enriched() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    filtered_rows, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=[
            _row(timestamp="2026-05-25T00:00:00Z", entry_path_quality_score=0.40),
            _row(timestamp="2026-05-25T01:00:00Z", stop_pressure_risk_score=0.80),
            _row(timestamp="2026-05-26T00:00:00Z", mae_pressure_risk_score=0.80),
            _row(timestamp="2026-05-28T00:00:00Z", market_regime="high_volatility"),
            _row(timestamp="2026-05-29T00:00:00Z"),
        ],
        enabled=True,
        profile="ADAPTIVE_FEATURE_GUARD_V2",
        rules={
            "min_entry_path_quality_score": 0.72,
            "min_setup_quality_score": 0.61,
            "max_stop_pressure_risk_score": 0.44,
            "max_mae_pressure_risk_score": 0.50,
            "blocked_regime_values": ["high_volatility", "unknown"],
        },
        target_dates=("2026-05-25", "2026-05-26", "2026-05-28"),
        date_blackout_used=False,
    )

    assert len(filtered_rows) == 1
    assert summary["diagnostic_version"] == "ml38.10.29"
    assert summary["enabled"] is True
    assert summary["input_signal_count"] == 5
    assert summary["removed_signal_count"] >= 4
    assert summary["output_signal_count"] >= 1
    assert summary["target_date_input_count"] >= 1
    assert summary["primary_removed_counts_by_reason"]
    assert summary["matched_removed_counts_by_reason"]
    assert summary["removed_counts_by_date"]
    assert summary["removed_counts_by_regime"]
    assert summary["removed_counts_by_entry_path_quality_bucket"]
    assert summary["removed_counts_by_stop_pressure_bucket"]
    assert summary["removed_signal_examples"]
    assert "market_regime" not in summary["missing_feature_counts"]


def test_ml38_10_29_label_grid_has_lv33_configs_and_all_are_research_only() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs = {item["config_id"]: item for item in grid["configs"]}

    for config_id in EXPECTED_LV33_IDS:
        cfg = configs[config_id]
        assert cfg["research_only_fold_repair_probe_enabled"] is True
        assert cfg["fold_repair_time_slice_blackout_enabled"] is False
        assert cfg["fold_repair_feature_filter_enabled"] is True
        assert (
            cfg["research_only_acceptance_block_reason"]
            == "research_only_adaptive_feature_regime_fold_repair_probe"
        )


def test_ml38_10_29_runtime_shortlists_registered() -> None:
    available_grid = {
        item["config_id"] for item in LabelQualityGridPlanner().build_grid()["configs"]
    }
    available_matrix = set(ML38_2_FV3_TUNING_CONFIG_IDS)

    assert EXPECTED_LV33_IDS <= available_grid
    assert EXPECTED_LV33_IDS <= available_matrix
    assert set(FAST_DEBUG_CONFIGS).issubset(available_grid)
    assert set(FAST_DEBUG_CONFIGS).issubset(available_matrix)
    assert set(QUICK_QUALITY_CONFIGS).issubset(available_grid)
    assert set(QUICK_QUALITY_CONFIGS).issubset(available_matrix)


def test_ml38_10_29_fold_feature_regime_repair_probe_diagnostics_readiness() -> None:
    candidate = {
        "symbol": "SOLUSDT",
        "config_id": "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_probe",
        "fold_repair_feature_filter_enabled": True,
        "fold_feature_regime_filter_summary": {
            "removed_signal_count": 3,
            "input_signal_count": 10,
            "removed_ratio": 0.3,
            "primary_removed_counts_by_reason": {"high_stop_pressure": 2},
            "matched_removed_counts_by_reason": {
                "high_stop_pressure": 2,
                "high_mae_pressure": 1,
            },
            "removed_counts_by_date": {"2026-05-25": 2},
            "passed_counts_by_date": {"2026-05-26": 1},
            "removed_counts_by_regime": {"high_volatility": 2},
        },
        "profit_total_r": 5.0,
        "walk_forward_total_r": 1.2,
    }

    result = FoldFeatureRegimeRepairProbe().analyze([candidate])
    assert result["diagnostic_version"] == "ml38.10.29"
    assert result["feature_filter_diagnostics"]["readiness"] == "DIAGNOSTICS_READY"
    assert result["feature_filter_diagnostics"]["aggregate_primary_removed_counts_by_reason"]

    nested_candidate = dict(candidate)
    nested_candidate.pop("fold_feature_regime_filter_summary")
    nested_candidate["profit_aware_diagnostics"] = {
        "best_gate": {
            "fold_feature_regime_filter_summary": {
                "removed_signal_count": 1,
                "input_signal_count": 10,
                "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
            }
        }
    }
    nested_result = FoldFeatureRegimeRepairProbe().analyze([nested_candidate])
    assert nested_result["feature_filter_diagnostics"]["readiness"] == "DIAGNOSTICS_READY"
    assert nested_result["feature_filter_diagnostics"][
        "aggregate_primary_removed_counts_by_reason"
    ] == {"low_entry_path_quality": 1}
