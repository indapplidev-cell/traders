from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.diagnostics.feature_diagnostics_v2 import FeatureDiagnosticsV2
from app.features.feature_models import feature_names_for_version


def test_feature_diagnostics_v2_reports_nulls_variance_missing_and_separation() -> None:
    analyzer = FeatureDiagnosticsV2()
    feature_names = feature_names_for_version("fv2_regime")
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    labels = ["UP", "DOWN", "FLAT"]
    close_distances = [2.0, -2.0, 0.0]

    for index, label in enumerate(labels):
        features = {name: 1.0 for name in feature_names}
        features["close_minus_ema_21_atr"] = close_distances[index]
        features["regime_trend_up"] = None if index == 0 else 1.0
        features["regime_trend_down"] = float(index)
        if index == 1:
            del features["regime_range"]
        rows.append(
            SimpleNamespace(
                candle_open_time=start_at + timedelta(minutes=15 * index),
                features_json=features,
            )
        )

    labels_by_open_time = {
        row.candle_open_time: SimpleNamespace(direction_label=label)
        for row, label in zip(rows, labels)
    }

    report = analyzer.build_report(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp15_sl10",
        feature_rows=rows,
        labels_by_open_time=labels_by_open_time,
    )

    assert report["feature_count"] == len(feature_names)
    assert "feature_null_ratio_gt_0_20:regime_trend_up" in report["warnings"]
    assert "feature_zero_variance:body_size" in report["warnings"]
    assert "feature_missing:regime_range" in report["warnings"]
    assert "low_up_down_separation:body_size" in report["warnings"]
    assert report["feature_stats"]["close_minus_ema_21_atr"]["class_means"]["UP"] == 2.0
    assert report["feature_stats"]["close_minus_ema_21_atr"]["class_means"]["DOWN"] == -2.0
    assert report["top_up_down_separation_features"][0]["feature_name"] == "close_minus_ema_21_atr"
