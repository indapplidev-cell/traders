from types import SimpleNamespace

from app.diagnostics.regime_segment_diagnostics import RegimeSegmentDiagnostics


def test_regime_segment_diagnostics_counts_segment_metrics() -> None:
    diagnostics = RegimeSegmentDiagnostics()
    rows = [
        SimpleNamespace(
            direction_label="UP",
            features_json={
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
                "regime_volatility_expanding": 1.0,
                "regime_volatility_contracting": 0.0,
                "ema_stack_bullish": 1.0,
                "ema_stack_bearish": 0.0,
                "close_above_ema_200": 1.0,
            },
        ),
        SimpleNamespace(
            direction_label="DOWN",
            features_json={
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
                "regime_volatility_expanding": 0.0,
                "regime_volatility_contracting": 1.0,
                "ema_stack_bullish": 0.0,
                "ema_stack_bearish": 1.0,
                "close_above_ema_200": 0.0,
            },
        ),
    ]

    report = diagnostics.build_report(
        dataset_rows=rows,
        long_evaluator=lambda segment_rows: {"total_r": float(len(segment_rows))},
        short_evaluator=lambda segment_rows: {"total_r": -float(len(segment_rows))},
        ema_baseline_evaluator=lambda segment_rows: {
            "total_r": 2.0 if segment_rows else 0.0,
            "global_profit_factor": 1.2 if segment_rows else None,
            "signal_count": len(segment_rows),
        },
    )

    trend_up = report["segments"]["regime_trend_up"]
    close_below = report["segments"]["close_below_ema_200"]

    assert trend_up["row_count"] == 1
    assert trend_up["actual_counts"] == {"UP": 1, "DOWN": 0, "FLAT": 0}
    assert trend_up["better_side"] == "LONG"
    assert "too_few_rows" in trend_up["warnings"]
    assert close_below["row_count"] == 1
    assert close_below["actual_counts"]["DOWN"] == 1
