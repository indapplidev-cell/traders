from app.diagnostics.profit_exit_root_cause_audit import ProfitExitRootCauseAudit


def _long_signal_row(*, high: float, low: float, close: float = 100.0) -> dict:
    return {
        "signal_direction": "LONG",
        "current_close": close,
        "atr_14": 1.0,
        "confidence": 0.80,
        "margin": 0.20,
        "directional_edge": 0.40,
        "tp_before_sl": False,
        "future_candles": [
            {"high": high, "low": low, "close": close},
        ],
    }


def test_ml38_10_13_profit_exit_audit_detects_stop_pressure() -> None:
    signal_rows = [
        _long_signal_row(high=100.4, low=98.8),
        _long_signal_row(high=100.6, low=98.7),
        _long_signal_row(high=100.5, low=98.6),
    ]
    outcomes = [
        {"result": "SL", "raw_r": -1.0, "net_r": -1.03},
        {"result": "SL", "raw_r": -1.0, "net_r": -1.03},
        {"result": "SL", "raw_r": -1.0, "net_r": -1.03},
    ]

    audit = ProfitExitRootCauseAudit().analyze(
        signal_rows=signal_rows,
        outcomes=outcomes,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
        gate_type="max_prob",
        threshold=0.50,
    )

    assert audit["diagnostic_name"] == "profit_exit_root_cause_audit"
    assert audit["diagnostic_version"] == "ml38.10.13"
    assert audit["audit_status"] == "COMPLETED"
    assert audit["root_cause_status"] == "STOP_PRESSURE_DOMINANT"
    assert audit["primary_root_cause"] == "stop_loss_hit"
    assert audit["root_cause_counts"]["stop_loss_hit"] == 3
    assert audit["avg_mae_to_stop_loss"] >= 1.0
    assert "audit_stop_loss_distance_and_mae_distribution" in audit["recommendations"]


def test_ml38_10_13_profit_exit_audit_detects_insufficient_mfe() -> None:
    signal_rows = [
        _long_signal_row(high=100.3, low=99.7),
        _long_signal_row(high=100.4, low=99.8),
        _long_signal_row(high=100.2, low=99.9),
    ]
    outcomes = [
        {"result": "NEITHER", "raw_r": -0.10, "net_r": -0.13},
        {"result": "NEITHER", "raw_r": -0.05, "net_r": -0.08},
        {"result": "NEITHER", "raw_r": -0.02, "net_r": -0.05},
    ]

    audit = ProfitExitRootCauseAudit().analyze(
        signal_rows=signal_rows,
        outcomes=outcomes,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
        gate_type="max_prob",
        threshold=0.50,
    )

    assert audit["root_cause_status"] == "TARGET_TOO_AMBITIOUS_OR_ENTRY_TOO_LATE"
    assert audit["primary_root_cause"] == "insufficient_mfe_to_target"
    assert audit["root_cause_counts"]["insufficient_mfe_to_target"] == 3
    assert "audit_take_profit_distance_against_mfe_distribution" in audit["recommendations"]
