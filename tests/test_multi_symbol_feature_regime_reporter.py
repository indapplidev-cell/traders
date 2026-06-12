import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


def test_multi_symbol_feature_regime_reporter_writes_json_and_markdown(tmp_path: Path) -> None:
    reporter = MultiSymbolFeatureRegimeReporter()
    payload = {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "experiment_count": 3,
        "candidate_count": 3,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 3,
        "best_symbol": "BTCUSDT",
        "best_candidate_config_id": "lv2_h08_thr04_tp10_sl10",
        "best_candidate_score": -2.003547,
        "symbol_results": [
            {
                "symbol": "BTCUSDT",
                "best_candidate_score": -2.003547,
                "baseline_edge": 0.018072,
                "profit_factor": 1.009218,
                "walk_forward_profit_factor": 0.972727,
                "real_feature_diagnostics_used": True,
                "regime_features_attached": True,
                "failed_gates": ["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
            }
        ],
        "feature_version_summary": {"feature_versions_by_symbol": {"BTCUSDT": "fv2"}},
        "gap_training_safety_summary": {
            "gap_severity_by_symbol": {"BTCUSDT": "OK"},
            "effective_gap_count_by_symbol": {"BTCUSDT": 0},
        },
        "regime_integration_summary": {
            "regime_training_applied_by_symbol": {"BTCUSDT": False},
            "regime_specific_training_applied_any": False,
        },
        "walk_forward_summary": {"all_failed": True},
        "profit_aware_summary": {"profit_aware_failed_count": 2},
        "collapse_summary": {"all_failed": True},
        "all_feature_version_fv2": True,
        "all_gap_training_safe": True,
        "all_real_feature_diagnostics_used": False,
        "symbols_missing_real_diagnostics": ["ETHUSDT", "SOLUSDT"],
        "symbols_missing_regime_features": ["ETHUSDT", "SOLUSDT"],
        "recommendations": ["Do not activate model; no accepted candidates were produced."],
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "orders_enabled": False,
        "traders_core_connected": False,
    }

    json_path = tmp_path / "multi_symbol_feature_regime_analysis.json"
    markdown_path = tmp_path / "multi_symbol_feature_regime_analysis.md"

    reporter.write_analysis_json(payload, json_path)
    reporter.write_analysis_markdown(payload, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["best_symbol"] == "BTCUSDT"
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# ML35 Multi-Symbol Feature/Regime Analysis" in markdown
    assert "Symbol Comparison Table" in markdown
    assert "Recommendations" in markdown
    assert "Safety" in markdown

