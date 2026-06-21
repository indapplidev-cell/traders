from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics


def _exit_audit(primary: str, total_r: float) -> dict:
    return {
        "diagnostic_name": "profit_exit_root_cause_audit",
        "diagnostic_version": "ml38.10.13",
        "audit_status": "COMPLETED",
        "primary_root_cause": primary,
        "root_cause_status": "STOP_PRESSURE_DOMINANT",
        "resolved_signal_count": 10,
        "total_r": total_r,
    }


def test_ml38_10_13_profit_aware_diagnostics_include_exit_root_cause_audit() -> None:
    profit_summary = {
        "summary": {
            "gate_type": "max_prob",
            "threshold": 0.5,
            "profit_factor": 0.8,
            "total_r": -12.0,
            "profit_exit_root_cause_audit": _exit_audit("stop_loss_hit", -12.0),
        },
        "gate_results": [],
    }

    diagnostics = WalkForwardProfitDiagnostics().build_profit_aware_diagnostics(
        profit_aware_summary=profit_summary
    )

    assert diagnostics["profit_exit_root_cause_audit"]["primary_root_cause"] == "stop_loss_hit"
    assert diagnostics["profit_aware_profit_factor"] == 0.8
    assert diagnostics["profit_aware_total_r"] == -12.0


def test_ml38_10_13_walk_forward_diagnostics_aggregate_exit_root_cause_audits() -> None:
    walk_summary = {
        "summary": {
            "fold_count": 2,
            "folds_profitable_on_test": 0,
            "folds_with_selected_gate": 2,
            "global_profit_factor": 0.8,
            "global_total_r": -20.0,
        },
        "folds": [
            {
                "fold_index": 0,
                "test_result": {
                    "signal_count": 10,
                    "resolved_signal_count": 10,
                    "profit_factor": 0.7,
                    "total_r": -12.0,
                    "profit_exit_root_cause_audit": _exit_audit("stop_loss_hit", -12.0),
                },
            },
            {
                "fold_index": 1,
                "test_result": {
                    "signal_count": 8,
                    "resolved_signal_count": 8,
                    "profit_factor": 0.9,
                    "total_r": -8.0,
                    "profit_exit_root_cause_audit": _exit_audit("stop_loss_hit", -8.0),
                },
            },
        ],
    }

    diagnostics = WalkForwardProfitDiagnostics().analyze(
        symbol="SOLUSDT",
        feature_version="fv3",
        model_version="model-test",
        walk_forward_summary=walk_summary,
        profit_aware_summary={"summary": {}},
    )

    summary = diagnostics["walk_forward_profit_exit_root_cause_summary"]
    assert summary["audit_status"] == "COMPLETED"
    assert summary["fold_audit_count"] == 2
    assert summary["dominant_primary_root_cause"] == "stop_loss_hit"
    assert summary["primary_root_cause_counts"]["stop_loss_hit"] == 2
