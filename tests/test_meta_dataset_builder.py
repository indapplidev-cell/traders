from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.features.feature_models import feature_names_for_version
from app.meta_label.meta_dataset_builder import MetaDatasetBuilder
from app.meta_label.meta_label_models import MetaLabelRecord


def test_meta_dataset_builder_excludes_non_trainable_labels_and_tracks_ratios() -> None:
    builder = MetaDatasetBuilder()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        _feature_row(start + timedelta(minutes=index), float(index + 1))
        for index in range(5)
    ]
    meta_labels = [
        _meta_row(feature_rows[0].candle_open_time, "WIN", 1, "LONG", 1.0),
        _meta_row(feature_rows[1].candle_open_time, "LOSS", 0, "SHORT", -1.0),
        _meta_row(feature_rows[2].candle_open_time, "NO_TRADE", None, "FLAT", None),
        _meta_row(feature_rows[3].candle_open_time, "AMBIGUOUS", None, "LONG", None),
        _meta_row(feature_rows[4].candle_open_time, "NO_EXIT", None, "SHORT", 0.1),
    ]

    rows, summary = builder.build_rows(
        feature_rows=feature_rows,
        meta_labels=meta_labels,
        feature_version="fv2_regime",
    )

    assert len(rows) == 2
    assert summary["positive_class_ratio"] == 0.5
    assert summary["negative_class_ratio"] == 0.5
    assert summary["excluded_no_trade"] == 1
    assert summary["excluded_ambiguous"] == 1
    assert summary["excluded_no_exit"] == 1
    assert summary["meta_dataset_valid"] is False


def _feature_row(open_time, base_value: float):
    return SimpleNamespace(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        features_json={name: base_value for name in feature_names_for_version("fv2_regime")},
    )


def _meta_row(open_time, meta_label: str, target, direction: str, trade_r):
    return MetaLabelRecord(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=open_time,
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
        horizon_candles=16,
        ema_signal_direction=direction,
        ema_signal_strength_atr=0.5 if direction == "LONG" else -0.5,
        meta_label=meta_label,
        meta_target_win=target,
        meta_trade_r=trade_r,
        meta_same_candle_ambiguous=False,
    )
