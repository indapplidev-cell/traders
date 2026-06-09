from app.diagnostics.direction_bias_diagnostics import DirectionBiasDiagnostics


def test_direction_bias_diagnostics_flags_no_short_signals() -> None:
    diagnostics = DirectionBiasDiagnostics()
    predictions = [
        {"predicted_label": "UP", "actual_label": "UP"},
        {"predicted_label": "UP", "actual_label": "DOWN"},
        {"predicted_label": "FLAT", "actual_label": "FLAT"},
    ]
    signals = [
        {"signal_direction": "LONG"},
        {"signal_direction": "LONG"},
    ]

    report = diagnostics.build_report(predictions=predictions, signal_rows=signals)

    assert "no_short_signals" in report["warnings"]
