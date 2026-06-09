from datetime import datetime, timezone
from types import SimpleNamespace

from app.diagnostics.meta_label_diagnostics import MetaLabelDiagnostics
from app.meta_label.meta_label_models import MetaLabelRecord


def test_meta_label_diagnostics_builds_distribution_and_regime_stats() -> None:
    diagnostics = MetaLabelDiagnostics()
    feature_rows = [
        SimpleNamespace(
            candle_open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            features_json={
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
                "regime_volatility_expanding": 0.0,
                "regime_volatility_contracting": 1.0,
                "ema_stack_bullish": 1.0,
                "ema_stack_bearish": 0.0,
                "close_above_ema_200": 1.0,
                "feature_alpha": 2.0,
            },
        ),
        SimpleNamespace(
            candle_open_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
            features_json={
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
                "regime_volatility_expanding": 0.0,
                "regime_volatility_contracting": 1.0,
                "ema_stack_bullish": 1.0,
                "ema_stack_bearish": 0.0,
                "close_above_ema_200": 1.0,
                "feature_alpha": -1.0,
            },
        ),
    ]
    meta_labels = [
        MetaLabelRecord(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=feature_rows[0].candle_open_time,
            feature_version="fv2_regime",
            label_version="meta_ema_9_21_tp15_sl10",
            horizon_candles=16,
            ema_signal_direction="LONG",
            ema_signal_strength_atr=0.8,
            meta_label="WIN",
            meta_target_win=1,
            meta_trade_r=1.47,
            meta_same_candle_ambiguous=False,
        ),
        MetaLabelRecord(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=feature_rows[1].candle_open_time,
            feature_version="fv2_regime",
            label_version="meta_ema_9_21_tp15_sl10",
            horizon_candles=16,
            ema_signal_direction="SHORT",
            ema_signal_strength_atr=-0.8,
            meta_label="LOSS",
            meta_target_win=0,
            meta_trade_r=-1.03,
            meta_same_candle_ambiguous=False,
        ),
    ]

    report = diagnostics.build_report(
        feature_rows=feature_rows,
        meta_labels=meta_labels,
        feature_version="fv2_regime",
        label_version="meta_ema_9_21_tp15_sl10",
    )

    assert report["meta_label_distribution"]["WIN"] == 1
    assert report["meta_label_distribution"]["LOSS"] == 1
    assert report["win_rate_by_regime"]["regime_trend_up"] == 0.5
    assert report["top_features_by_win_loss_separation"][0]["feature_name"] == "feature_alpha"
