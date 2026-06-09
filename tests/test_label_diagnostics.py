from datetime import datetime, timezone

from app.diagnostics.label_diagnostics import LabelDiagnostics


def test_label_diagnostics_builds_expected_summary() -> None:
    diagnostics = LabelDiagnostics()
    labels = [
        _label("UP", True, 0.02, 1.0, 1.5, 0.4, datetime(2025, 1, 1, tzinfo=timezone.utc)),
        _label("DOWN", False, -0.01, -0.8, 1.2, 0.6, datetime(2025, 1, 2, tzinfo=timezone.utc)),
        _label("FLAT", None, 0.0, 0.1, 0.3, 0.2, datetime(2025, 1, 3, tzinfo=timezone.utc)),
    ]

    result = diagnostics.build_report(labels, "BTCUSDT", "15m", 8, "lv1")

    assert result["total_labels"] == 3
    assert result["direction_counts"]["UP"] == 1
    assert result["tp_before_sl_null_count"] == 1
    assert result["future_return_median"] == 0.0


def _label(direction_label, tp_before_sl, future_return, future_move_atr, favorable, adverse, open_time):
    return type(
        "LabelRow",
        (),
        {
            "direction_label": direction_label,
            "tp_before_sl": tp_before_sl,
            "future_return": future_return,
            "future_move_atr": future_move_atr,
            "max_favorable_move_atr": favorable,
            "max_adverse_move_atr": adverse,
            "candle_open_time": open_time,
        },
    )()
