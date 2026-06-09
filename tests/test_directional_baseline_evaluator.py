from types import SimpleNamespace

from app.baseline.directional_baseline_evaluator import DirectionalBaselineEvaluator
from app.validation.walk_forward_splitter import WalkForwardConfig


def test_directional_baseline_evaluator_aggregates_global_profit_and_flags_missing_direction(tmp_path) -> None:
    evaluator = DirectionalBaselineEvaluator(
        reports_dir=tmp_path,
        walk_forward_splitter=FakeWalkForwardSplitter(),
        profit_evaluator_v2=FakeProfitEvaluator(),
    )
    dataset_rows = [
        _dataset_row("UP", 0.01, 12.0, 10.0),
        _dataset_row("DOWN", -0.01, 8.0, 10.0),
        _dataset_row("UP", 0.02, 13.0, 10.0),
        _dataset_row("DOWN", -0.02, 7.0, 10.0),
    ]

    report = evaluator.evaluate(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv1",
        label_version="lv1",
        dataset_rows=dataset_rows,
        config=WalkForwardConfig("expanding", 1, 1, 1, 1, 1),
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
        prediction_row_builder=lambda rows, labels: [{"predicted_label": label} for label in labels],
        require_both_directions=True,
    )

    assert report["best_baseline"]["name"] == "always_long"
    summary = report["baselines"]["always_long"]["summary"]
    assert summary["global_profit_factor"] == 2.0
    assert summary["global_total_r"] == 2.0
    assert "no_short_signals" in summary["warnings"]


class FakeWalkForwardSplitter:
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
                "validation_rows": 0,
                "test_rows": 2,
            }
        ]

    def apply_fold(self, dataset_rows, fold):
        return {"train": dataset_rows[:2], "validation": [], "test": dataset_rows[2:]}


class FakeProfitEvaluator:
    def evaluate_single_gate(self, predictions, **kwargs):
        predicted_label = predictions[0]["predicted_label"] if predictions else "FLAT"
        if predicted_label == "UP":
            return {
                "summary": {
                    "gross_profit_r": 4.0,
                    "gross_loss_r": 2.0,
                    "profit_factor": 2.0,
                    "total_r": 2.0,
                    "resolved_signal_count": 2,
                    "win_count": 1,
                    "loss_count": 1,
                    "neither_count": 0,
                    "signal_count": 2,
                    "long_count": 2,
                    "short_count": 0,
                },
                "signal_rows": predictions,
                "outcomes": [{"result": "TP", "net_r": 4.0}, {"result": "SL", "net_r": -2.0}],
            }
        if predicted_label == "DOWN":
            return {
                "summary": {
                    "gross_profit_r": 0.0,
                    "gross_loss_r": 3.0,
                    "profit_factor": 0.0,
                    "total_r": -3.0,
                    "resolved_signal_count": 2,
                    "win_count": 0,
                    "loss_count": 2,
                    "neither_count": 0,
                    "signal_count": 2,
                    "long_count": 0,
                    "short_count": 2,
                },
                "signal_rows": predictions,
                "outcomes": [{"result": "SL", "net_r": -1.0}, {"result": "SL", "net_r": -2.0}],
            }
        return {
            "summary": {
                "gross_profit_r": 0.0,
                "gross_loss_r": 0.0,
                "profit_factor": None,
                "total_r": 0.0,
                "resolved_signal_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "neither_count": 0,
                "signal_count": 0,
                "long_count": 0,
                "short_count": 0,
            },
            "signal_rows": [],
            "outcomes": [],
        }


def _dataset_row(direction_label: str, return_1: float, ema_9: float, ema_21: float) -> SimpleNamespace:
    return SimpleNamespace(
        direction_label=direction_label,
        features_json={"return_1": return_1, "ema_9": ema_9, "ema_21": ema_21},
    )
