from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.experiments.feature_regime_experiment_reporter import (
    FeatureRegimeExperimentReporter,
)
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def test_compact_fold_feature_summary_preserves_counts_and_filters_service_keys():
    summary = {
        "diagnostic_name": "fold_feature_regime_filter_summary",
        "diagnostic_version": "ml38.10.29",
        "enabled": True,
        "profile": "ADAPTIVE_FEATURE_GUARD_V2",
        "input_signal_count": 82,
        "output_signal_count": 81,
        "removed_signal_count": 1,
        "removed_ratio": 1 / 82,
        "primary_removed_counts_by_reason": {
            "_key_count": 8,
            "_keys_truncated": 0,
            "low_entry_path_quality": 1,
        },
        "removed_counts_by_date": {"2026-06-09": 1},
        "removed_counts_by_regime": {"missing": 1},
        "missing_feature_counts": {"market_regime": 82},
        "conditional_regime_rule_eligible_counts": {
            "high_volatility_low_entry_quality": 2,
        },
        "conditional_regime_ablation_board": [
            {
                "rule_id": "high_volatility_low_entry_quality",
                "eligible_count": 2,
                "removed_count": 1,
                "passed_count": 1,
                "effect_label": "REMOVAL_HELPFUL",
            }
        ],
        "per_regime_contribution_board": [
            {
                "market_regime": "missing",
                "removed_total_r": -1.0,
                "passed_total_r": 0.0,
                "effect_label": "REMOVAL_HELPFUL",
            }
        ],
        "removed_signal_examples": [{"signal_date": "2026-06-09"} for _ in range(8)],
    }

    compact = FeatureRegimeExperimentReporter._compact_fold_feature_summary(summary)

    assert compact["removed_signal_count"] == 1
    assert compact["primary_removed_counts_by_reason"] == {"low_entry_path_quality": 1}
    assert compact["removed_counts_by_date"] == {"2026-06-09": 1}
    assert compact["removed_counts_by_regime"] == {"missing": 1}
    assert compact["missing_feature_counts"] == {"market_regime": 82}
    assert "conditional_regime_ablation_board" in compact
    assert "per_regime_contribution_board" in compact
    assert len(compact["removed_signal_examples"]) == 5
    assert compact["removed_signal_examples_truncated"] is True
    assert "_key_count" not in compact["primary_removed_counts_by_reason"]


def test_compact_ranked_result_exposes_feature_filter_counts():
    reporter = FeatureRegimeExperimentReporter()
    row = {
        "config_id": "lv33_h12_test",
        "profit_aware_diagnostics": {
            "best_gate": {
                "fold_feature_regime_filter_summary": {
                    "enabled": True,
                    "input_signal_count": 82,
                    "output_signal_count": 81,
                    "removed_signal_count": 1,
                    "removed_ratio": 1 / 82,
                    "primary_removed_counts_by_reason": {"low_entry_path_quality": 1},
                    "removed_counts_by_date": {"2026-06-09": 1},
                    "removed_counts_by_regime": {"missing": 1},
                    "missing_feature_counts": {"market_regime": 82},
                }
            }
        },
    }

    compact = reporter._compact_ranked_result(row)

    assert compact["fold_feature_regime_filter_summary"]["removed_signal_count"] == 1
    assert compact["feature_filter_removed_signal_count"] == 1
    assert compact["feature_filter_removed_ratio"] == 1 / 82
    assert compact["primary_removed_counts_by_reason"] == {"low_entry_path_quality": 1}
    assert compact["removed_counts_by_date"] == {"2026-06-09": 1}
    assert compact["removed_counts_by_regime"] == {"missing": 1}
    assert compact["missing_feature_counts"] == {"market_regime": 82}


def test_analyzer_treats_key_count_only_dict_as_placeholder():
    assert MultiSymbolFeatureRegimeAnalyzer._is_empty_or_compact_placeholder(
        {"_key_count": 0, "_keys_truncated": False}
    )
    assert not MultiSymbolFeatureRegimeAnalyzer._is_empty_or_compact_placeholder(
        {"removed_signal_count": 1}
    )


def test_analyzer_extracts_fold_feature_summary_from_profit_best_gate():
    payload = {
        "profit_aware_diagnostics": {
            "best_gate": {
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 1,
                    "removed_counts_by_date": {"2026-06-09": 1},
                }
            }
        }
    }

    summary = MultiSymbolFeatureRegimeAnalyzer._fold_feature_summary_from_payload(payload)

    assert summary["removed_signal_count"] == 1
    assert summary["removed_counts_by_date"] == {"2026-06-09": 1}


def test_fold_feature_probe_aggregates_dates_regimes_missing_features_and_ignores_service_keys():
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
            "fold_repair_feature_filter_enabled": True,
            "fold_feature_regime_filter_summary": {
                "input_signal_count": 82,
                "removed_signal_count": 1,
                "primary_removed_counts_by_reason": {
                    "_key_count": 8,
                    "_keys_truncated": 0,
                    "low_entry_path_quality": 1,
                },
                "matched_removed_counts_by_reason": {
                    "low_entry_path_quality": 1,
                },
                "removed_counts_by_date": {"2026-06-09": 1},
                "passed_counts_by_date": {"2026-06-10": 10},
                "removed_counts_by_regime": {"missing": 1},
                "passed_counts_by_regime": {"missing": 81},
                "missing_feature_counts": {"market_regime": 82},
            },
            "profit_factor": 1.37,
            "profit_total_r": 9.04,
            "walk_forward_total_r": 0.0,
        }
    ]

    result = FoldFeatureRegimeRepairProbe().analyze(candidates)
    diagnostics = result["feature_filter_diagnostics"]

    assert diagnostics["readiness"] == "DIAGNOSTICS_READY"
    assert diagnostics["active_filter_candidate_count"] == 1
    assert diagnostics["aggregate_primary_removed_counts_by_reason"] == {
        "low_entry_path_quality": 1
    }
    assert diagnostics["aggregate_removed_counts_by_date"] == {"2026-06-09": 1}
    assert diagnostics["aggregate_removed_counts_by_regime"] == {"missing": 1}
    assert diagnostics["aggregate_missing_feature_counts"] == {"market_regime": 82}
    assert "_key_count" not in diagnostics["aggregate_primary_removed_counts_by_reason"]
