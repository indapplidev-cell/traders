from types import SimpleNamespace

from app.diagnostics.opportunity_diagnostics import OpportunityDiagnostics


def test_opportunity_diagnostics_reports_rates_and_gates() -> None:
    rows = [
        SimpleNamespace(
            opportunity_label=1,
            opportunity_direction="UP",
            setup_type="nison_context",
            tp_before_sl=True,
            future_move_atr=0.9,
            max_adverse_move_atr=0.2,
            features_json={"regime_trend_up": 1.0},
            direction_label="UP",
            setup_quality_score=0.8,
            label_ambiguity_score=0.2,
            setup_expected_move_atr=1.0,
            setup_invalidation_distance_atr=0.3,
        ),
        SimpleNamespace(
            opportunity_label=0,
            opportunity_direction="NONE",
            setup_type="no_setup",
            tp_before_sl=None,
            future_move_atr=0.1,
            max_adverse_move_atr=0.2,
            features_json={"regime_range": 1.0},
            direction_label="FLAT",
            setup_quality_score=0.2,
            label_ambiguity_score=0.8,
            setup_expected_move_atr=0.1,
            setup_invalidation_distance_atr=0.2,
        ),
    ]

    payload = OpportunityDiagnostics().evaluate(rows, train_rows=rows)

    assert payload["row_count"] == 2
    assert payload["opportunity_rate"] == 0.5
    assert payload["no_trade_rate"] == 0.5
    assert "always_no_trade_baseline" in payload["baseline_results"]
    assert "first_touch_setup_baseline" in payload["baseline_results"]
    assert payload["opportunity_collapse_gate"]["passed"] is True
    assert payload["no_trade_dominance_gate"]["passed"] is True
    assert payload["setup_edge_gate"]["passed"] is True
