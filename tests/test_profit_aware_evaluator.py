from pathlib import Path

from app.evaluation.profit_aware_evaluator import ProfitAwareEvaluator


def test_profit_eval_counts_tp_first_sl_first_and_neither(tmp_path: Path) -> None:
    evaluator = ProfitAwareEvaluator(reports_dir=tmp_path)
    predictions = [
        {
            "predicted_label": "UP",
            "confidence": 0.6,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.4,
            "future_candles": [{"high": 116.0, "low": 99.0, "close": 114.0}],
        },
        {
            "predicted_label": "UP",
            "confidence": 0.6,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": -0.8,
            "future_candles": [{"high": 105.0, "low": 89.0, "close": 90.0}],
        },
        {
            "predicted_label": "DOWN",
            "confidence": 0.6,
            "current_close": 100.0,
            "atr_14": 10.0,
            "future_move_atr": 0.2,
            "future_candles": [{"high": 104.0, "low": 96.0, "close": 102.0}],
        },
    ]

    result = evaluator.evaluate("mv1", predictions, take_profit_atr=1.5, stop_loss_atr=1.0, confidence_thresholds=[0.5])
    row = result["thresholds"][0]

    assert row["win_count"] == 1
    assert row["loss_count"] == 1
    assert row["neither_count"] == 1

