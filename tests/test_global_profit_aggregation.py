from pathlib import Path

from app.diagnostics.direction_bias_diagnostics import DirectionBiasDiagnostics
from app.validation.gate_selector import GateSelector
from app.validation.walk_forward_evaluator import WalkForwardEvaluator
from app.validation.walk_forward_splitter import WalkForwardConfig


def test_walk_forward_summary_uses_global_profit_aggregation(tmp_path: Path) -> None:
    evaluator = WalkForwardEvaluator(
        reports_dir=tmp_path,
        walk_forward_splitter=TwoFoldSplitter(),
        gate_selector=GateSelector(),
        profit_evaluator_v2=TwoFoldProfitEvaluator(),
        direction_bias_diagnostics=DirectionBiasDiagnostics(),
    )
    dataset_rows = [type("Row", (), {"candle_open_time": index})() for index in range(8)]

    def prediction_builder(rows):
        return [
            {
                "actual_label": "UP",
                "predicted_label": "UP",
                "prob_up": 0.6,
                "prob_down": 0.2,
                "prob_flat": 0.2,
                "confidence": 0.6,
            }
            for _ in rows
        ]

    result = evaluator.evaluate(
        model_version="mv1",
        label_version="lv1",
        dataset_rows=dataset_rows,
        prediction_builder=prediction_builder,
        config=WalkForwardConfig("expanding", 1, 1, 1, 1, 1),
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
    )

    summary = result["summary"]
    assert summary["global_gross_profit_r"] == 12.0
    assert summary["global_gross_loss_r"] == 4.0
    assert summary["global_profit_factor"] == 3.0
    assert summary["global_total_r"] == 8.0
    assert summary["global_expectancy_r"] == 2.0


class TwoFoldSplitter:
    def build_plan(self, dataset_rows, config):
        return [
            {
                "fold_index": 1,
                "train_start": "2025-01-01T00:00:00+00:00",
                "train_end": "2025-01-02T00:00:00+00:00",
                "validation_start": "2025-01-02T00:00:00+00:00",
                "validation_end": "2025-01-03T00:00:00+00:00",
                "test_start": "2025-01-03T00:00:00+00:00",
                "test_end": "2025-01-04T00:00:00+00:00",
                "train_rows": 2,
                "validation_rows": 2,
                "test_rows": 2,
            },
            {
                "fold_index": 2,
                "train_start": "2025-01-01T00:00:00+00:00",
                "train_end": "2025-01-03T00:00:00+00:00",
                "validation_start": "2025-01-03T00:00:00+00:00",
                "validation_end": "2025-01-04T00:00:00+00:00",
                "test_start": "2025-01-04T00:00:00+00:00",
                "test_end": "2025-01-05T00:00:00+00:00",
                "train_rows": 4,
                "validation_rows": 2,
                "test_rows": 2,
            },
        ]

    def apply_fold(self, dataset_rows, fold):
        if fold["fold_index"] == 1:
            return {"train": dataset_rows[:2], "validation": dataset_rows[2:4], "test": dataset_rows[4:6]}
        return {"train": dataset_rows[:4], "validation": dataset_rows[4:6], "test": dataset_rows[6:8]}


class TwoFoldProfitEvaluator:
    def __init__(self) -> None:
        self._test_call_index = 0

    def evaluate_predictions(self, **kwargs):
        return {
            "gate_results": [
                {
                    "gate_type": "directional_edge",
                    "threshold": 0.05,
                    "signal_count": 35,
                    "profit_factor": 1.5,
                    "total_r": 4.0,
                    "expectancy_r": 0.2,
                    "long_count": 30,
                    "short_count": 5,
                    "max_drawdown_r": 2.0,
                }
            ]
        }

    def evaluate_single_gate(self, predictions, gate_type, threshold, **kwargs):
        self._test_call_index += 1
        if self._test_call_index == 1:
            return {
                "summary": {
                    "gate_type": gate_type,
                    "threshold": threshold,
                    "signal_count": 2,
                    "resolved_signal_count": 2,
                    "profit_factor": float("inf"),
                    "gross_profit_r": 10.0,
                    "gross_loss_r": 0.0,
                    "total_r": 10.0,
                    "expectancy_r": 5.0,
                    "win_count": 2,
                    "loss_count": 0,
                    "neither_count": 0,
                    "long_count": 2,
                    "short_count": 0,
                },
                "signal_rows": [{"signal_direction": "LONG"} for _ in predictions],
                "outcomes": [{"result": "TP", "net_r": 5.0}, {"result": "TP", "net_r": 5.0}],
            }
        return {
            "summary": {
                "gate_type": gate_type,
                "threshold": threshold,
                "signal_count": 2,
                "resolved_signal_count": 2,
                "profit_factor": 0.5,
                "gross_profit_r": 2.0,
                "gross_loss_r": 4.0,
                "total_r": -2.0,
                "expectancy_r": -1.0,
                "win_count": 1,
                "loss_count": 1,
                "neither_count": 0,
                "long_count": 2,
                "short_count": 0,
            },
            "signal_rows": [{"signal_direction": "LONG"} for _ in predictions],
            "outcomes": [{"result": "TP", "net_r": 2.0}, {"result": "SL", "net_r": -4.0}],
        }
