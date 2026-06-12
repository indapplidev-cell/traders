import json

from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics


def test_walk_forward_profit_diagnostics_computes_fold_extremes_and_recommendations() -> None:
    payload = WalkForwardProfitDiagnostics().analyze(
        symbol="BTCUSDT",
        feature_version="fv2",
        model_version="ml36_test_model",
        walk_forward_summary={
            "summary": {
                "fold_count": 4,
                "folds_with_selected_gate": 4,
                "folds_profitable_on_test": 1,
                "global_total_r": -2.4,
                "global_profit_factor": 0.96,
            },
            "folds": [
                {"fold_index": 0, "selected_gate": {"gate_type": "confidence", "threshold": 0.55}, "test_result": {"signal_count": 12, "resolved_signal_count": 12, "profit_factor": 1.08, "total_r": 0.9}},
                {"fold_index": 1, "selected_gate": {"gate_type": "confidence", "threshold": 0.55}, "test_result": {"signal_count": 3, "resolved_signal_count": 3, "profit_factor": 0.91, "total_r": -0.8}},
                {"fold_index": 2, "selected_gate": {"gate_type": "confidence", "threshold": 0.60}, "test_result": {"signal_count": 4, "resolved_signal_count": 4, "profit_factor": 0.88, "total_r": -1.1}},
                {"fold_index": 3, "selected_gate": {"gate_type": "margin", "threshold": 0.12}, "test_result": {"signal_count": 2, "resolved_signal_count": 2, "profit_factor": 0.72, "total_r": -1.4}},
            ],
        },
        profit_aware_summary={
            "gate_results": [
                {"gate_type": "confidence", "threshold": 0.55, "resolved_signal_count": 20, "profit_factor": 0.99, "total_r": -0.5},
                {"gate_type": "margin", "threshold": 0.12, "resolved_signal_count": 16, "profit_factor": 1.04, "total_r": 0.3},
            ]
        },
    )

    assert payload["fold_count"] == 4
    assert payload["profitable_fold_count"] == 1
    assert payload["unprofitable_fold_count"] == 3
    assert payload["best_fold"]["fold_index"] == 0
    assert payload["worst_fold"]["fold_index"] == 3
    assert payload["profit_aware_threshold_used"] == 0.12
    assert "Audit temporal stability because walk-forward profit factor is not yet above 1.0." in payload["recommendations"]
    assert "Review signal gating because some folds have too few test signals." in payload["recommendations"]
    json.dumps(payload, ensure_ascii=False, sort_keys=True)
