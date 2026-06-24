from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2


def _prediction_row(*, high: float, low: float, close: float = 100.0) -> dict:
    return {
        "predicted_label": "UP",
        "actual_label": "UP",
        "prob_up": 0.80,
        "prob_down": 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "current_close": close,
        "atr_14": 1.0,
        "future_move_atr": 0.0,
        "max_favorable_move_atr": max(0.0, high - close),
        "max_adverse_move_atr": max(0.0, close - low),
        "tp_before_sl": False,
        "features_json": {},
        "future_candles": [
            {"high": high, "low": low, "close": close},
        ],
    }


def test_ml38_10_13_profit_aware_evaluator_attaches_exit_root_cause_audit() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    predictions = [
        _prediction_row(high=100.4, low=98.8),
        _prediction_row(high=100.6, low=98.7),
        _prediction_row(high=100.5, low=98.6),
    ]

    result = evaluator.evaluate_single_gate(
        predictions=predictions,
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
    )

    summary = result["summary"]
    audit = summary["profit_exit_root_cause_audit"]
    assert audit["diagnostic_name"] == "profit_exit_root_cause_audit"
    assert audit["audit_status"] == "COMPLETED"
    assert audit["primary_root_cause"] == "stop_loss_hit"
    assert audit["resolved_signal_count"] == 3


def test_ml38_10_13_profit_aware_evaluator_exposes_best_gate_summary_audit() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    predictions = [
        _prediction_row(high=100.4, low=98.8),
        _prediction_row(high=100.6, low=98.7),
        _prediction_row(high=100.5, low=98.6),
    ]

    payload = evaluator.evaluate_predictions(
        predictions=predictions,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
    )

    assert payload["gate_results"]
    assert payload["summary"]
    assert payload["profit_exit_root_cause_audit"]
    assert payload["profit_exit_root_cause_audit"]["diagnostic_version"] == "ml38.10.17"
