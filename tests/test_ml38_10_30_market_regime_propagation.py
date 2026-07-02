from __future__ import annotations

from app.diagnostics.diagnostics_service import DiagnosticsService
from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS


def test_diagnostics_service_derives_market_regime_payload_from_features_json():
    features_json = {
        "regime_trend_up": 1.0,
        "regime_trend_down": 0.0,
        "regime_range": 0.0,
        "regime_high_volatility": 1.0,
        "regime_low_volatility": 0.0,
        "regime_unknown": 0.0,
        "regime_volatility_expanding": 1.0,
        "regime_volatility_contracting": 0.0,
    }

    payload = DiagnosticsService._regime_payload_from_features(features_json)

    assert payload["market_regime"] == "trend_up"
    assert payload["regime_bucket"] == "trend_up"
    assert payload["feature_regime_bucket"] == "trend_up"
    assert payload["market_regime_source"] == "features_json_regime_flags"
    assert "trend_up" in payload["active_regime_flags"]
    assert "high_volatility" in payload["active_regime_flags"]
    assert "volatility_expanding" in payload["active_regime_flags"]
    assert payload["regime_high_volatility_active"] is True


def test_profit_feature_filter_blocks_active_high_volatility_regime():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "signal_direction": "LONG",
            "market_regime": "trend_up",
            "active_regime_flags": ["trend_up", "high_volatility"],
            "entry_path_quality_score": 0.80,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
        {
            "signal_date": "2026-06-10",
            "signal_direction": "LONG",
            "market_regime": "trend_up",
            "active_regime_flags": ["trend_up"],
            "entry_path_quality_score": 0.80,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_REGIME_GUARD",
        rules={
            "blocked_regime_values": ["high_volatility"],
            "missing_feature_policy": "pass_with_warning",
        },
        target_dates=("2026-06-09",),
        date_blackout_used=False,
    )

    assert len(filtered) == 1
    assert summary["removed_signal_count"] == 1
    assert summary["primary_removed_counts_by_reason"] == {"blocked_regime": 1}
    assert summary["removed_counts_by_regime"] == {"trend_up": 1}
    assert summary["removed_counts_by_active_regime_flag"]["high_volatility"] == 1
    assert summary["market_regime_missing_count"] == 0
    assert "market_regime" not in summary["missing_feature_counts"]


def test_profit_feature_filter_recovers_regime_from_features_json():
    evaluator = ProfitAwareEvaluatorV2()
    row = {
        "features_json": {
            "regime_trend_up": 0.0,
            "regime_trend_down": 0.0,
            "regime_range": 0.0,
            "regime_high_volatility": 1.0,
            "regime_low_volatility": 0.0,
            "regime_unknown": 0.0,
        }
    }

    assert evaluator._row_regime_value(row) == "high_volatility"
    assert "high_volatility" in evaluator._row_regime_values(row)


def test_fold_feature_probe_reports_market_regime_propagated():
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
            "fold_repair_feature_filter_enabled": True,
            "fold_feature_regime_filter_summary": {
                "input_signal_count": 10,
                "removed_signal_count": 2,
                "primary_removed_counts_by_reason": {"blocked_regime": 2},
                "removed_counts_by_regime": {"high_volatility": 2},
                "passed_counts_by_regime": {"trend_up": 8},
                "removed_counts_by_active_regime_flag": {"high_volatility": 2},
                "passed_counts_by_active_regime_flag": {"trend_up": 8},
                "regime_source_counts": {"features_json_regime_flags": 10},
                "missing_feature_counts": {},
            },
            "profit_factor": 1.1,
            "profit_total_r": 2.0,
            "walk_forward_total_r": 0.0,
        }
    ]

    result = FoldFeatureRegimeRepairProbe().analyze(candidates)
    diagnostics = result["feature_filter_diagnostics"]

    assert diagnostics["readiness"] == "DIAGNOSTICS_READY"
    assert diagnostics["regime_propagation_status"] == "MARKET_REGIME_PROPAGATED"
    assert diagnostics["missing_market_regime_count"] == 0
    assert diagnostics["aggregate_removed_counts_by_regime"] == {"high_volatility": 2}
    assert diagnostics["aggregate_regime_source_counts"] == {
        "features_json_regime_flags": 10
    }
    assert "aggregate_conditional_regime_ablation_board" in diagnostics
    assert "aggregate_per_regime_contribution_board" in diagnostics


def test_ml38_10_30_does_not_change_runtime_candidate_counts():
    assert len(FAST_DEBUG_CONFIGS) == 18
    assert len(QUICK_QUALITY_CONFIGS) == 38
