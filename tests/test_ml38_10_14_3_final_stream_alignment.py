from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.evaluation.signal_gate_evaluator import SignalGateEvaluator


def _prediction(
    *,
    label: str,
    actual: str,
    blocked: bool,
    reason: str | None = None,
    quality: float = 0.80,
    stop: float = 0.20,
) -> dict[str, object]:
    return {
        "predicted_label": label,
        "actual_label": actual,
        "prob_up": 0.80 if label == "UP" else 0.10,
        "prob_down": 0.80 if label == "DOWN" else 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [{"high": 101.2, "low": 99.2}],
        "future_move_atr": 1.0,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": blocked,
        "entry_path_filter_block_reason": reason,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_original_predicted_label": label,
        "entry_path_quality_score": quality,
        "stop_pressure_risk_score": stop,
    }


def test_ml38_10_14_3_signal_gate_can_compare_raw_and_filtered_streams() -> None:
    evaluator = SignalGateEvaluator()
    rows = [
        _prediction(label="UP", actual="UP", blocked=False),
        _prediction(label="UP", actual="FLAT", blocked=True, reason="high_stop_pressure", stop=0.90),
    ]

    raw = evaluator.select_signals(rows, "max_prob", 0.50, apply_entry_path_filter=False)
    filtered = evaluator.select_signals(rows, "max_prob", 0.50, apply_entry_path_filter=True)

    assert raw["signal_count"] == 2
    assert filtered["signal_count"] == 1
    assert filtered["skipped_entry_path_filter_count"] == 1


def test_ml38_10_14_3_profit_audit_is_aligned_with_final_signal_stream() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    rows = [
        _prediction(label="UP", actual="UP", blocked=False),
        _prediction(label="UP", actual="FLAT", blocked=True, reason="high_stop_pressure", stop=0.90),
        _prediction(label="DOWN", actual="UP", blocked=True, reason="low_entry_quality", quality=0.20),
    ]

    payload = evaluator.evaluate_single_gate(
        predictions=rows,
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.0,
    )
    summary = payload["summary"]["entry_path_prediction_filter_summary"]
    stop_audit = payload["summary"]["stop_pressure_effectiveness_audit"]

    assert summary["audit_stream"] == "final_profit_aware_gate_signal_stream"
    assert summary["original_final_signal_count"] == 3
    assert summary["filtered_final_signal_count"] == 1
    assert summary["blocked_final_signal_count"] == 2
    assert summary["stream_consistency_ok"] is True
    assert stop_audit["diagnostic_version"] == "ml38.10.16"
    assert stop_audit["stream_consistency_ok"] is True
    assert stop_audit["blocked_by_high_stop_pressure_count"] == 1
