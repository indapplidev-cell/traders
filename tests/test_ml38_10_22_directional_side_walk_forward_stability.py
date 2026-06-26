from __future__ import annotations

import json

from app.diagnostics.directional_side_walk_forward_stability import (
    DirectionalSideWalkForwardStabilityAnalyzer,
)
from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter


def _candidate(
    *,
    config_id: str,
    profile: str | None,
    allowed: list[str] | None,
    pf: float,
    total_r: float,
    wf_pf: float | None,
    wf_total_r: float | None,
    fold_count: int = 3,
    low_signal_fold_count: int = 0,
    total_wf_signals: int = 30,
) -> dict:
    walk_forward_verdict = "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY"
    walk_forward_status = "STABLE_ENOUGH_FOR_RESEARCH"
    if low_signal_fold_count > 0 or total_wf_signals < 20:
        walk_forward_verdict = "REJECT_LOW_SIGNAL_WALK_FORWARD"
        walk_forward_status = "LOW_SIGNAL_WALK_FORWARD"
    elif wf_pf is None or wf_total_r is None or wf_total_r <= 0.0:
        walk_forward_verdict = "REJECT_WALK_FORWARD_UNSTABLE"
        walk_forward_status = "WALK_FORWARD_UNSTABLE"

    return {
        "config_id": config_id,
        "candidate_status": "REJECTED",
        "score": 1.0,
        "label_config": {
            "directional_side_filter_profile": profile,
            "allowed_signal_directions": allowed or [],
        },
        "directional_side_filter_profile": profile,
        "allowed_signal_directions": allowed or [],
        "profit_factor": pf,
        "profit_total_r": total_r,
        "walk_forward_profit_factor": wf_pf,
        "walk_forward_total_r": wf_total_r,
        "walk_forward_global_total_r": wf_total_r,
        "resolved_signal_count": 100,
        "walk_forward_profit_diagnostics": {
            "diagnostic_name": "walk_forward_profit_diagnostics",
            "diagnostic_version": "ml38.10.23",
            "walk_forward_profit_factor": wf_pf,
            "walk_forward_total_r": wf_total_r,
            "fold_count": fold_count,
            "profitable_fold_count": 2,
            "low_signal_fold_count": low_signal_fold_count,
            "zero_signal_fold_count": 0,
            "total_resolved_signal_count": total_wf_signals,
            "min_resolved_signal_count": 5 if low_signal_fold_count == 0 else 1,
            "median_resolved_signal_count": 10,
            "max_resolved_signal_count": 15,
            "fold_signal_summary": {
                "fold_count": fold_count,
                "folds_with_gate": fold_count,
                "total_resolved_signal_count": total_wf_signals,
                "low_signal_fold_count": low_signal_fold_count,
                "zero_signal_fold_count": 0,
            },
            "fold_profit_summary": {
                "profitable_fold_count": 2,
                "profitable_fold_rate": 2 / 3,
            },
            "fold_snapshots": [
                {"fold_index": 1, "resolved_signal_count": 10, "profit_factor": 1.2, "total_r": 2.0},
                {"fold_index": 2, "resolved_signal_count": 10, "profit_factor": 1.1, "total_r": 1.0},
                {"fold_index": 3, "resolved_signal_count": 10, "profit_factor": 0.9, "total_r": -0.5},
            ],
            "walk_forward_stability_status": walk_forward_status,
            "walk_forward_stability_verdict": walk_forward_verdict,
            "walk_forward_stability_warnings": (
                ["walk_forward_has_low_signal_folds", "walk_forward_total_signal_count_too_low"]
                if low_signal_fold_count > 0 or total_wf_signals < 20
                else []
            ),
        },
    }


def test_ml38_10_22_walk_forward_profit_diagnostics_exposes_fold_signal_stability() -> None:
    diagnostics = WalkForwardProfitDiagnostics().analyze(
        symbol="SOLUSDT",
        feature_version="fv3_candle_ta_context",
        model_version="mv",
        profit_aware_summary={"summary": {"profit_factor": 1.2, "total_r": 3.0}},
        walk_forward_summary={
            "summary": {
                "fold_count": 3,
                "folds_with_selected_gate": 3,
                "folds_profitable_on_test": 2,
                "global_profit_factor": 1.1,
                "global_total_r": 4.0,
            },
            "folds": [
                {"fold_index": 1, "selected_gate": {"gate_type": "max_prob", "threshold": 0.5}, "test_result": {"resolved_signal_count": 8, "signal_count": 8, "profit_factor": 1.2, "total_r": 2.0}},
                {"fold_index": 2, "selected_gate": {"gate_type": "max_prob", "threshold": 0.5}, "test_result": {"resolved_signal_count": 7, "signal_count": 7, "profit_factor": 1.1, "total_r": 1.0}},
                {"fold_index": 3, "selected_gate": {"gate_type": "max_prob", "threshold": 0.5}, "test_result": {"resolved_signal_count": 6, "signal_count": 6, "profit_factor": 0.9, "total_r": -0.5}},
            ],
        },
    )
    assert diagnostics["diagnostic_version"] == "ml38.10.23"
    assert diagnostics["fold_signal_summary"]["total_resolved_signal_count"] == 21
    assert diagnostics["low_signal_fold_count"] == 0
    assert diagnostics["walk_forward_stability_verdict"] == "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY"
    assert len(diagnostics["fold_snapshots"]) == 3


def test_ml38_10_22_directional_side_stability_rejects_profitable_test_window_with_low_signal_wf() -> None:
    analyzer = DirectionalSideWalkForwardStabilityAnalyzer()
    payload = analyzer.analyze(
        [
            _candidate(
                config_id="lv26_both",
                profile=None,
                allowed=[],
                pf=0.89,
                total_r=-9.4,
                wf_pf=1.11,
                wf_total_r=14.75,
                total_wf_signals=60,
            ),
            _candidate(
                config_id="lv28_long_only",
                profile="long_only_research",
                allowed=["LONG"],
                pf=1.21,
                total_r=6.0,
                wf_pf=None,
                wf_total_r=0.0,
                low_signal_fold_count=2,
                total_wf_signals=4,
            ),
            _candidate(
                config_id="lv28_short_only",
                profile="short_only_research",
                allowed=["SHORT"],
                pf=0.71,
                total_r=-16.0,
                wf_pf=0.80,
                wf_total_r=-5.0,
                total_wf_signals=30,
            ),
        ]
    )
    assert payload["diagnostic_status"] == "COMPLETED"
    assert payload["side_profile_counts"]["LONG_ONLY"] == 1
    assert payload["best_research_side_profile"] == "LONG_ONLY"
    assert payload["best_research_verdict"] == "REJECT_LOW_SIGNAL_WALK_FORWARD"
    long_best = payload["stability_by_side_profile"]["LONG_ONLY"]
    assert long_best["profit_factor"] > 1.0
    assert long_best["walk_forward_stability_verdict"] == "REJECT_LOW_SIGNAL_WALK_FORWARD"
    assert "test_window_profitable_but_walk_forward_unstable" in payload["warnings"]


def test_ml38_10_22_multi_symbol_analysis_exports_directional_side_wf_stability(tmp_path) -> None:
    summary_path = tmp_path / "feature_regime_experiment_summary.json"
    both_candidate = _candidate(
        config_id="lv26_both",
        profile=None,
        allowed=[],
        pf=0.89,
        total_r=-9.4,
        wf_pf=1.11,
        wf_total_r=14.75,
        total_wf_signals=60,
    )
    long_candidate = _candidate(
        config_id="lv28_long_only",
        profile="long_only_research",
        allowed=["LONG"],
        pf=1.21,
        total_r=6.0,
        wf_pf=None,
        wf_total_r=0.0,
        low_signal_fold_count=2,
        total_wf_signals=4,
    )
    summary_path.write_text(
        json.dumps(
            {
                "symbol": "SOLUSDT",
                "interval": "15m",
                "start_date": "2025-01-01",
                "experiment_id": "ml38_10_22_test",
                "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
                "candidate_count": 2,
                "evaluated_candidate_count": 2,
                "failed_candidate_count": 0,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 2,
                "best_candidate_config_id": "lv28_long_only",
                "best_candidate_score": 1.0,
                "feature_version_used": "fv3_candle_ta_context",
                "configs_ranked": [
                    {"config_id": "lv28_long_only", "score": 1.0, "candidate_status": "REJECTED"},
                    {"config_id": "lv26_both", "score": 0.8, "candidate_status": "REJECTED"},
                ],
                "candidate_results": [both_candidate, long_candidate],
                "failed_gates_summary": {"walk_forward_gate": 1},
                "walk_forward_summary": {},
                "profit_summary": {},
                "gap_quality_summary": {},
                "recommendations": [],
            }
        ),
        encoding="utf-8",
    )
    analysis = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])
    assert "directional_side_walk_forward_stability" in analysis
    stability = analysis["directional_side_walk_forward_stability"]
    assert stability["diagnostic_status"] == "COMPLETED"
    assert stability["best_research_verdict"] == "REJECT_LOW_SIGNAL_WALK_FORWARD"
    assert analysis["configs_ranked"]
    assert "walk_forward_stability_verdict" in analysis["configs_ranked"][0]

    reporter = MultiSymbolFeatureRegimeReporter()
    markdown_path = tmp_path / "analysis.md"
    reporter.write_analysis_markdown(analysis, markdown_path)
    md_text = markdown_path.read_text(encoding="utf-8")
    assert "Directional side walk-forward stability" in md_text
