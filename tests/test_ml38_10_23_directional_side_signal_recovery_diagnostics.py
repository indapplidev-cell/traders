from __future__ import annotations

from app.diagnostics.directional_side_signal_recovery_diagnostics import (
    DirectionalSideSignalRecoveryDiagnostics,
)
from app.diagnostics.directional_side_walk_forward_stability import (
    DirectionalSideWalkForwardStabilityAnalyzer,
)
from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _fold(
    *,
    fold_index: int,
    original: int,
    filtered: int,
    resolved: int,
    profile: str = "long_only_research",
) -> dict:
    return {
        "fold_index": fold_index,
        "selected_gate": {"gate_type": "max_prob", "threshold": 0.5},
        "gate_reject_reason": None,
        "validation_gate_results": [
            {
                "gate_type": "max_prob",
                "threshold": 0.5,
                "signal_count": filtered,
                "resolved_signal_count": resolved,
                "profit_factor": None,
                "total_r": 0.0,
                "directional_side_filter_summary": {
                    "profile": profile,
                    "active": True,
                    "original_signal_count": original,
                    "filtered_signal_count": filtered,
                    "removed_signal_count": max(0, original - filtered),
                    "removed_short_count": max(0, original - filtered),
                    "removed_long_count": 0,
                    "allowed_signal_directions": ["LONG"],
                },
            }
        ],
        "test_result": {
            "signal_count": filtered,
            "resolved_signal_count": resolved,
            "profit_factor": None,
            "total_r": 0.0,
            "directional_side_filter_summary": {
                "profile": profile,
                "active": True,
                "original_signal_count": original,
                "filtered_signal_count": filtered,
                "removed_signal_count": max(0, original - filtered),
                "removed_short_count": max(0, original - filtered),
                "removed_long_count": 0,
                "allowed_signal_directions": ["LONG"],
            },
        },
    }


def _walk_forward_summary(*folds: dict) -> dict:
    return {
        "directional_side_filter_profile": "long_only_research",
        "folds": list(folds),
        "summary": {
            "fold_count": len(folds),
            "folds_with_selected_gate": len(folds),
            "folds_profitable_on_test": 0,
            "global_profit_factor": None,
            "global_total_r": 0.0,
            "total_test_signal_count": sum(
                int((fold.get("test_result") or {}).get("resolved_signal_count", 0) or 0)
                for fold in folds
            ),
        },
    }


def test_ml38_10_23_signal_recovery_distinguishes_removed_all_vs_zero_resolved() -> None:
    removed_all_payload = DirectionalSideSignalRecoveryDiagnostics().analyze(
        walk_forward_summary=_walk_forward_summary(
            _fold(fold_index=0, original=10, filtered=0, resolved=0),
            _fold(fold_index=1, original=8, filtered=3, resolved=3),
        )
    )
    assert removed_all_payload["diagnostic_version"] == "ml38.10.26"
    assert removed_all_payload["side_filter_removed_all_fold_count"] == 1
    assert removed_all_payload["low_signal_fold_count"] == 2
    assert (
        removed_all_payload["primary_signal_loss_reason_counts"][
            "side_filter_removed_all_signals"
        ]
        == 1
    )

    zero_resolved_payload = DirectionalSideSignalRecoveryDiagnostics().analyze(
        walk_forward_summary=_walk_forward_summary(
            _fold(fold_index=0, original=0, filtered=0, resolved=0),
            _fold(fold_index=1, original=7, filtered=7, resolved=7),
        )
    )
    assert (
        zero_resolved_payload["primary_signal_loss_reason_counts"][
            "selected_gate_zero_resolved_signals"
        ]
        == 1
    )
    assert zero_resolved_payload["side_filter_removed_all_fold_count"] == 0


def test_ml38_10_23_walk_forward_profit_diagnostics_adds_signal_recovery_payload() -> None:
    diagnostics = WalkForwardProfitDiagnostics().analyze(
        symbol="SOLUSDT",
        feature_version="fv3_candle_ta_context",
        model_version="mv",
        profit_aware_summary={"summary": {"profit_factor": 1.2, "total_r": 3.0}},
        walk_forward_summary=_walk_forward_summary(
            _fold(fold_index=0, original=10, filtered=0, resolved=0),
            _fold(fold_index=1, original=8, filtered=3, resolved=3),
        ),
    )

    recovery = diagnostics["directional_side_signal_recovery_diagnostics"]
    assert recovery["diagnostic_name"] == "directional_side_signal_recovery_diagnostics"
    assert diagnostics["directional_side_signal_recovery_status"] == (
        "SIDE_FILTER_REMOVED_SIGNAL_EVIDENCE"
    )
    assert diagnostics["side_filter_removed_all_fold_count"] == 1


def test_ml38_10_23_walk_forward_stability_carries_signal_recovery_fields() -> None:
    walk_forward_diagnostics = WalkForwardProfitDiagnostics().analyze(
        symbol="SOLUSDT",
        feature_version="fv3_candle_ta_context",
        model_version="mv",
        profit_aware_summary={"summary": {"profit_factor": 1.2, "total_r": 3.0}},
        walk_forward_summary=_walk_forward_summary(
            _fold(fold_index=0, original=10, filtered=0, resolved=0),
            _fold(fold_index=1, original=8, filtered=3, resolved=3),
        ),
    )
    analyzer = DirectionalSideWalkForwardStabilityAnalyzer()
    payload = analyzer.analyze(
        [
            {
                "config_id": "lv28_long_only",
                "candidate_status": "REJECTED",
                "score": 1.0,
                "label_config": {
                    "directional_side_filter_profile": "long_only_research",
                    "allowed_signal_directions": ["LONG"],
                },
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "directional_side_filter_summary": {
                    "profile": "long_only_research",
                    "original_signal_count": 18,
                    "filtered_signal_count": 3,
                    "removed_signal_count": 15,
                },
                "profit_factor": 1.21,
                "profit_total_r": 6.0,
                "walk_forward_profit_factor": None,
                "walk_forward_total_r": 0.0,
                "walk_forward_global_total_r": 0.0,
                "resolved_signal_count": 3,
                "walk_forward_profit_diagnostics": walk_forward_diagnostics,
            }
        ]
    )

    row = payload["comparison_board"][0]
    assert row["directional_side_signal_recovery_status"] == "SIDE_FILTER_REMOVED_SIGNAL_EVIDENCE"
    assert row["directional_side_signal_recovery_verdict"] == "CHECK_SIDE_FILTER_STRICTNESS"
    assert row["side_filter_removed_all_fold_count"] == 1
    assert row["signal_recovery_total_removed_signal_count"] == 15


def test_ml38_10_23_multi_symbol_recovery_payload_extracts_fields() -> None:
    payload = MultiSymbolFeatureRegimeAnalyzer._directional_side_signal_recovery_payload(
        {
            "walk_forward_profit_diagnostics": {
                "directional_side_signal_recovery_diagnostics": {
                    "diagnostic_status": "SIDE_FILTER_REMOVED_SIGNAL_EVIDENCE",
                    "verdict": "CHECK_SIDE_FILTER_STRICTNESS",
                    "primary_signal_loss_reason_counts": {
                        "side_filter_removed_all_signals": 1,
                    },
                    "side_filter_removed_all_fold_count": 1,
                    "raw_signal_available_but_filtered_out_count": 1,
                    "threshold_too_strict_fold_count": 0,
                    "total_original_signal_count": 18,
                    "total_filtered_signal_count": 3,
                    "total_removed_signal_count": 15,
                }
            }
        }
    )

    assert payload["directional_side_signal_recovery_status"] == (
        "SIDE_FILTER_REMOVED_SIGNAL_EVIDENCE"
    )
    assert payload["directional_side_signal_recovery_verdict"] == "CHECK_SIDE_FILTER_STRICTNESS"
    assert payload["primary_signal_loss_reason_counts"] == {
        "side_filter_removed_all_signals": 1
    }
    assert payload["signal_recovery_total_original_signal_count"] == 18
    assert payload["signal_recovery_total_filtered_signal_count"] == 3
    assert payload["signal_recovery_total_removed_signal_count"] == 15
