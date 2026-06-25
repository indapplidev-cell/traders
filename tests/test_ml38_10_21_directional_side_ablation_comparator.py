from __future__ import annotations

from app.diagnostics.directional_side_ablation_comparator import (
    DirectionalSideAblationComparator,
)
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.labels.label_quality_grid import LabelQualityGridConfig


def _candidate(
    *,
    config_id: str,
    side_profile: str | None,
    profit_factor: float,
    profit_total_r: float,
    walk_forward_profit_factor: float = 1.0,
    walk_forward_total_r: float = 0.0,
    resolved_signal_count: int = 8,
    removed_signal_count: int = 0,
    removed_signal_rate: float = 0.0,
    long_total_r: float = 0.0,
    short_total_r: float = 0.0,
) -> dict[str, object]:
    allowed = {
        "long_only_research": ["LONG"],
        "short_only_research": ["SHORT"],
        "suppress_short_research": ["LONG"],
        None: [],
    }[side_profile]
    return {
        "config_id": config_id,
        "candidate_status": "REJECTED",
        "status": "COMPLETED",
        "profit_factor": profit_factor,
        "profit_total_r": profit_total_r,
        "walk_forward_profit_factor": walk_forward_profit_factor,
        "walk_forward_total_r": walk_forward_total_r,
        "walk_forward_global_total_r": walk_forward_total_r,
        "resolved_signal_count": resolved_signal_count,
        "signal_count": resolved_signal_count,
        "directional_side_filter_profile": side_profile,
        "allowed_signal_directions": allowed,
        "directional_side_filter_summary": {
            "profile": side_profile or "both_directions",
            "research_only": side_profile is not None,
            "removed_signal_count": removed_signal_count,
            "removed_signal_rate": removed_signal_rate,
            "allowed_signal_directions": allowed or ["LONG", "SHORT"],
        },
        "directional_edge_bias_audit": {
            "direction_balance_ratio": 0.60,
            "directional_profit_skew_r": long_total_r - short_total_r,
            "directional_profit_skew_ratio": 0.25,
            "long_total_r": long_total_r,
            "short_total_r": short_total_r,
            "long_avg_r": None if resolved_signal_count == 0 else long_total_r / max(resolved_signal_count, 1),
            "short_avg_r": None if resolved_signal_count == 0 else short_total_r / max(resolved_signal_count, 1),
        },
        "long_total_r": long_total_r,
        "short_total_r": short_total_r,
        "long_avg_r": None if resolved_signal_count == 0 else long_total_r / max(resolved_signal_count, 1),
        "short_avg_r": None if resolved_signal_count == 0 else short_total_r / max(resolved_signal_count, 1),
        "direction_balance_ratio": 0.60,
        "directional_profit_skew_r": long_total_r - short_total_r,
        "directional_profit_skew_ratio": 0.25,
    }


def test_ml38_10_21_comparator_detects_side_profiles() -> None:
    comparator = DirectionalSideAblationComparator()
    payload = comparator.compare(
        [
            _candidate(config_id="both", side_profile=None, profit_factor=0.9, profit_total_r=-1.0),
            _candidate(
                config_id="long",
                side_profile="long_only_research",
                profit_factor=1.1,
                profit_total_r=2.0,
            ),
            _candidate(
                config_id="short",
                side_profile="short_only_research",
                profit_factor=0.7,
                profit_total_r=-3.0,
            ),
            _candidate(
                config_id="noshort",
                side_profile="suppress_short_research",
                profit_factor=1.0,
                profit_total_r=1.0,
            ),
        ]
    )

    assert payload["diagnostic_version"] == "ml38.10.21"
    assert payload["side_profile_counts"]["LONG_ONLY"] == 1
    assert payload["side_profile_counts"]["SHORT_ONLY"] == 1
    assert payload["side_profile_counts"]["SUPPRESS_SHORT"] == 1
    assert payload["side_profile_counts"]["BOTH_DIRECTIONS"] == 1


def test_ml38_10_21_long_only_improvement_is_research_only() -> None:
    comparator = DirectionalSideAblationComparator()
    payload = comparator.compare(
        [
            _candidate(
                config_id="both",
                side_profile=None,
                profit_factor=0.89,
                profit_total_r=-9.4,
                walk_forward_profit_factor=0.91,
                walk_forward_total_r=-6.2,
            ),
            _candidate(
                config_id="long",
                side_profile="long_only_research",
                profit_factor=1.15,
                profit_total_r=3.7,
                walk_forward_profit_factor=1.05,
                walk_forward_total_r=1.4,
            ),
            _candidate(
                config_id="short",
                side_profile="short_only_research",
                profit_factor=0.69,
                profit_total_r=-16.7,
                walk_forward_profit_factor=0.72,
                walk_forward_total_r=-11.0,
            ),
        ]
    )

    assert payload["diagnostic_status"] == "SIDE_ABLATION_IMPROVES_PROFIT_BUT_RESEARCH_ONLY"
    assert "research_only_side_suppression_not_live_ready" in payload["warnings"]
    assert "do_not_accept_long_only_without_multisymbol_confirmation" in payload["recommendations"]


def test_ml38_10_21_multi_symbol_analyzer_payload_includes_comparator() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2026-04-01",
        "candidate_count": 2,
        "evaluated_candidate_count": 2,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 2,
        "best_candidate_config_id": "lv28_long",
        "feature_version_used": "fv4_book_setup_context",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 100,
        "regime_features_attached": True,
        "regime_feature_count": 10,
        "candle_ta_context_features_attached": True,
        "candle_ta_context_feature_count": 5,
        "gap_training_safe": True,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "warnings": [],
        "candidate_results": [
            _candidate(
                config_id="lv27_both",
                side_profile=None,
                profit_factor=0.95,
                profit_total_r=-2.0,
                walk_forward_total_r=-1.0,
            ),
            _candidate(
                config_id="lv28_long",
                side_profile="long_only_research",
                profit_factor=1.10,
                profit_total_r=2.3,
                walk_forward_total_r=1.2,
            ),
        ],
        "configs_ranked": [
            {
                **_candidate(
                    config_id="lv27_both",
                    side_profile=None,
                    profit_factor=0.95,
                    profit_total_r=-2.0,
                    walk_forward_total_r=-1.0,
                ),
                "score": 0.1,
            },
            {
                **_candidate(
                    config_id="lv28_long",
                    side_profile="long_only_research",
                    profit_factor=1.10,
                    profit_total_r=2.3,
                    walk_forward_total_r=1.2,
                ),
                "score": 0.2,
            },
        ],
        "failed_gates": [],
        "passed_gates": [],
        "flat_bias_summary": {},
        "down_blindness_summary": {},
        "baseline_edge_summary": {},
        "label_mode_comparison_audit": {},
        "flat_subtype_audit": {},
        "setup_aware_label_diagnostics": {},
        "schwager_robustness_decision_board": {},
        "recommendations": [],
    }

    analyzer = MultiSymbolFeatureRegimeAnalyzer()
    analyzer.load_summary = lambda source: source  # type: ignore[method-assign]
    analysis = analyzer.analyze([summary])  # type: ignore[arg-type]

    comparator = analysis["directional_side_ablation_comparator"]
    assert "directional_side_ablation_comparator" in analysis
    assert "comparison_board" in comparator
    assert "best_by_side_profile" in comparator
    assert "long_only_vs_both_delta" in comparator


def test_ml38_10_21_candidate_warnings_for_side_filter() -> None:
    runner = LabelGridExperimentRunner()
    quality_payload = {
        "quality_status": "QUALITY_REJECTED",
        "candidate_selection": {
            "candidate_status": "REJECTED",
            "warnings": [],
            "recommendations": [],
            "failed_gates": [],
            "passed_gates": [],
        },
        "quality_gates_summary": {},
        "probability_diagnostics": {},
        "collapse_diagnostics_v2": {},
        "regime_label_builder_status": {
            "regime_label_builder_status": "ready",
        },
        "walk_forward_profit_diagnostics": {},
        "profit_aware_diagnostics": {
            "summary": {
                "directional_side_filter_summary": {
                    "profile": "suppress_short_research",
                    "allowed_signal_directions": ["LONG"],
                    "research_only": True,
                },
                "directional_edge_bias_audit": {},
            }
        },
        "feature_config": {"feature_version": "fv4_book_setup_context"},
    }
    label_config = LabelQualityGridConfig(
        config_id="lv28_test",
        label_version="lv28_test",
        horizon=12,
        threshold=0.6,
        take_profit_atr=1.2,
        stop_loss_atr=1.5,
        flat_threshold=0.6,
        description="test",
        risk_note="test",
        directional_side_filter_profile="suppress_short_research",
        allowed_signal_directions=("LONG",),
    )

    result = runner._build_candidate_result(
        label_config=label_config,
        quality_payload=quality_payload,
        class_distribution={},
        gate_policy_summary={},
    )

    assert "directional_side_filter_is_research_only" in result.warnings
    assert "short_side_suppression_not_live_ready" in result.warnings
