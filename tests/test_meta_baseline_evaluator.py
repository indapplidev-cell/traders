from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.meta_label.meta_baseline_evaluator import MetaBaselineEvaluator
from app.meta_label.meta_label_models import MetaDatasetRow
from app.validation.walk_forward_splitter import WalkForwardConfig


def test_meta_baseline_evaluator_counts_take_all_ema_signals(tmp_path: Path) -> None:
    evaluator = MetaBaselineEvaluator(
        reports_dir=tmp_path,
        walk_forward_splitter=FakeWalkForwardSplitter(),
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        _row(start, "LONG", 1.0, 1),
        _row(start + timedelta(minutes=15), "SHORT", -1.0, 0),
        _row(start + timedelta(minutes=30), "LONG", 1.2, 1),
    ]

    report = evaluator.evaluate(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
        dataset_rows=rows,
        config=WalkForwardConfig("expanding", 1, 1, 1, 1, 1),
    )

    take_all = report["baselines"]["take_all_ema_signals"]["summary"]
    assert take_all["signal_count"] == 3
    assert take_all["long_count"] == 2
    assert take_all["short_count"] == 1
    assert report["best_baseline_overall"] == "take_only_long_ema"


class FakeWalkForwardSplitter:
    def build_plan(self, dataset_rows, config):
        return [{"fold_index": 1, "test_start": "a", "test_end": "b"}]

    def apply_fold(self, dataset_rows, fold):
        return {"train": [], "validation": [], "test": list(dataset_rows)}


def _row(open_time, direction: str, trade_r: float, target: int) -> MetaDatasetRow:
    return MetaDatasetRow(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
        horizon_candles=16,
        features_json={"regime_trend_up": 1.0, "regime_trend_down": 0.0, "regime_high_volatility": 0.0, "regime_low_volatility": 1.0},
        ema_signal_direction=direction,
        ema_signal_strength_atr=0.5,
        meta_trade_r=trade_r,
        meta_target_win=target,
    )
