from pathlib import Path

from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.evaluation.signal_gate_evaluator import SignalGateEvaluator


def test_profit_eval_v2_returns_null_profit_factor_when_no_signals(tmp_path: Path) -> None:
    evaluator = ProfitAwareEvaluatorV2(
        reports_dir=tmp_path,
        signal_gate_evaluator=SignalGateEvaluator(reports_dir=tmp_path),
    )
    predictions = [
        {
            "actual_label": "UP",
            "predicted_label": "FLAT",
            "prob_up": 0.33,
            "prob_down": 0.33,
            "prob_flat": 0.34,
            "confidence": 0.34,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.5,
            "future_candles": [{"high": 101.0, "low": 99.0, "close": 100.0}],
        }
    ]

    result = evaluator.evaluate(
        model_version="mv1",
        predictions=predictions,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
    )

    row = next(item for item in result["gate_results"] if item["gate_type"] == "directional_edge" and item["threshold"] == 0.05)
    assert row["signal_count"] == 0
    assert row["profit_factor"] is None
    assert row["avg_r"] is None
    assert row["reject_reason"] == "no_signals"


def test_profit_eval_v2_counts_long_short_and_applies_costs(tmp_path: Path) -> None:
    evaluator = ProfitAwareEvaluatorV2(
        reports_dir=tmp_path,
        signal_gate_evaluator=SignalGateEvaluator(reports_dir=tmp_path),
    )
    predictions = [
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.60,
            "prob_down": 0.20,
            "prob_flat": 0.20,
            "confidence": 0.60,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.5,
            "future_candles": [{"high": 116.0, "low": 99.0, "close": 114.0}],
        },
        {
            "actual_label": "DOWN",
            "predicted_label": "DOWN",
            "prob_up": 0.20,
            "prob_down": 0.60,
            "prob_flat": 0.20,
            "confidence": 0.60,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.4,
            "future_candles": [{"high": 111.0, "low": 96.0, "close": 110.0}],
        },
    ]

    result = evaluator.evaluate(
        model_version="mv1",
        predictions=predictions,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
    )

    row = next(item for item in result["gate_results"] if item["gate_type"] == "directional_edge" and item["threshold"] == 0.2)
    assert row["signal_count"] == 2
    assert row["long_count"] == 1
    assert row["short_count"] == 1
    assert row["win_count"] == 1
    assert row["loss_count"] == 1
    assert row["profit_factor"] > 1.0


def test_profit_eval_v2_same_candle_default_is_conservative_sl(tmp_path: Path) -> None:
    evaluator = ProfitAwareEvaluatorV2(
        reports_dir=tmp_path,
        signal_gate_evaluator=SignalGateEvaluator(reports_dir=tmp_path),
    )
    predictions = [
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.60,
            "prob_down": 0.20,
            "prob_flat": 0.20,
            "confidence": 0.60,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.2,
            "future_candles": [{"high": 116.0, "low": 89.0, "close": 110.0}],
        }
    ]

    result = evaluator.evaluate(
        model_version="mv1",
        predictions=predictions,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
    )

    row = next(item for item in result["gate_results"] if item["gate_type"] == "directional_edge" and item["threshold"] == 0.2)
    assert row["loss_count"] == 1
    assert row["ambiguous_count"] == 0
    assert row["same_candle_policy"] == "conservative"
