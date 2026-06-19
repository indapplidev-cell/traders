from app.diagnostics.label_mode_comparison_audit import LabelModeComparisonAudit


def test_label_mode_comparison_audit_detects_future_close_up_vs_first_touch_down_conflict() -> None:
    payload = LabelModeComparisonAudit().evaluate(
        [
            {
                "future_close_atr_label": "UP",
                "first_touch_tp_sl_label": "DOWN",
                "mfe_mae_dominance_label": "DOWN",
                "setup_aware_first_touch_label": "DOWN",
                "future_move_atr": -0.8,
                "first_touch_ambiguous": False,
                "has_setup_context": True,
            },
            {
                "future_close_atr_label": "FLAT",
                "first_touch_tp_sl_label": "UP",
                "mfe_mae_dominance_label": "UP",
                "setup_aware_first_touch_label": "UP",
                "future_move_atr": 0.6,
                "first_touch_ambiguous": False,
                "has_setup_context": True,
            },
        ]
    )

    assert payload["future_close_up_but_first_touch_down_count"] == 1
    assert payload["future_close_vs_first_touch_conflict_ratio"] > 0.0
    assert payload["future_close_flat_but_touch_event_count"] == 1
