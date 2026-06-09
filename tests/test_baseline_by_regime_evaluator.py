from pathlib import Path
from types import SimpleNamespace

from app.baseline.baseline_by_regime_evaluator import BaselineByRegimeEvaluator
from app.validation.walk_forward_splitter import WalkForwardConfig


def test_baseline_by_regime_selects_best_baseline_by_segment(tmp_path: Path) -> None:
    evaluator = BaselineByRegimeEvaluator(
        reports_dir=tmp_path,
        walk_forward_splitter=FakeWalkForwardSplitter(),
        profit_evaluator_v2=FakeProfitEvaluatorV2(),
    )
    rows = [
        SimpleNamespace(
            features_json={
                "ema_9": 3.0,
                "ema_21": 2.0,
                "ema_50": 1.0,
                "return_1": 1.0,
                "ema_stack_bullish": 1.0,
                "ema_stack_bearish": 0.0,
                "close_above_ema_200": 1.0,
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
                "regime_volatility_expanding": 0.0,
                "regime_volatility_contracting": 1.0,
                "ema_stack_bearish": 0.0,
            },
        ),
        SimpleNamespace(
            features_json={
                "ema_9": 1.0,
                "ema_21": 2.0,
                "ema_50": 3.0,
                "return_1": -1.0,
                "ema_stack_bullish": 0.0,
                "ema_stack_bearish": 1.0,
                "close_above_ema_200": 0.0,
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
                "regime_volatility_expanding": 1.0,
                "regime_volatility_contracting": 0.0,
            },
        ),
    ]

    report = evaluator.evaluate(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp15_sl10",
        dataset_rows=rows,
        config=WalkForwardConfig("expanding", 1, 1, 1, 1, 1),
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        fee_r=0.02,
        slippage_r=0.01,
        same_candle_policy="conservative",
        prediction_row_builder=lambda test_rows, labels: [{"predicted_label": label} for label in labels],
    )

    assert report["best_baseline_overall"]["baseline_name"] == "always_long"
    assert report["best_baseline_by_regime"]["regime_trend_up"]["baseline_name"] == "ema_9_21_direction"
    assert "regime_trend_up" in report["regimes_where_ema_9_21_works"]


class FakeWalkForwardSplitter:
    def build_plan(self, dataset_rows, config):
        return [{"fold_index": 1, "test_start": "a", "test_end": "b"}]

    def apply_fold(self, dataset_rows, fold):
        return {"train": [], "validation": [], "test": list(dataset_rows)}


class FakeProfitEvaluatorV2:
    def evaluate_single_gate(self, predictions, gate_type, threshold, **kwargs):
        total_r = 0.0
        long_count = 0
        short_count = 0
        for prediction in predictions:
            if prediction["predicted_label"] == "UP":
                total_r += 2.0
                long_count += 1
            elif prediction["predicted_label"] == "DOWN":
                total_r -= 1.0
                short_count += 1
        return {
            "summary": {
                "signal_count": len(predictions),
                "resolved_signal_count": len(predictions),
                "gross_profit_r": max(total_r, 0.0),
                "gross_loss_r": abs(min(total_r, 0.0)),
                "total_r": total_r,
                "global_profit_factor": 2.0 if total_r > 0 else 0.5,
                "profit_factor": 2.0 if total_r > 0 else 0.5,
                "expectancy_r": (total_r / len(predictions)) if predictions else None,
                "win_count": long_count,
                "long_count": long_count,
                "short_count": short_count,
                "max_drawdown_r": 0.0,
                "long_total_r": float(long_count * 2.0),
                "short_total_r": float(short_count * -1.0),
            }
        }
