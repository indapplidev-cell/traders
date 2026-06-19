from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.experiments.feature_regime_experiment_runner import FeatureRegimeExperimentRunner
from app.features.feature_builder import FeatureBuilder
from app.features.feature_models import feature_names_for_version


def test_fv4_feature_version_is_registered_and_diagnostics_expose_setup_context_counts() -> None:
    names = feature_names_for_version("fv4_book_setup_context")

    assert "doji_score" in names
    assert "nison_reversal_context_score" in names
    assert "alt_trend_continuation_long_score" in names
    assert "path_8_high_low_expansion_atr" in names
    assert "htf_1h_trend_score" in names

    records = FeatureBuilder().build(
        _build_candles(64),
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv4_book_setup_context",
    )
    rows = [
        {"direction_label": "UP", "features_json": dict(record.features_json)}
        for record in records[-20:]
    ]
    diagnostics = RealFeatureDiagnosticsService().analyze(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv4_book_setup_context",
        label_version="lv11_h12_thr06_tp12_sl12_fv4",
        rows=rows,
        source="test",
    )

    assert diagnostics["book_setup_context_features_attached"] is True
    assert diagnostics["fv4_feature_count"] == len(names)
    assert diagnostics["book_setup_context_feature_count"] > 0
    assert diagnostics["nison_feature_count"] > 0
    assert diagnostics["altunina_feature_count"] > 0
    assert diagnostics["path_context_feature_count"] > 0
    assert diagnostics["htf_context_feature_count"] == 0
    assert diagnostics["missing_context_feature_count"] == 6
    assert diagnostics["higher_timeframe_context_available"] is False
    assert diagnostics["higher_timeframe_context_reason"] == "not_integrated_yet"

    preview = FeatureRegimeExperimentRunner().build_preview()
    assert preview["feature_version_default"] == "fv4_book_setup_context"
    assert "fv4_book_setup_context" in preview["feature_versions_available"]


def _build_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.5)
        close_price = open_price + (0.8 if index % 5 else -0.1)
        high_price = max(open_price, close_price) + 1.0
        low_price = min(open_price, close_price) - 0.8
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=15 * index),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=1000.0 + (index * 7.0),
                taker_buy_base_volume=(1000.0 + (index * 7.0)) * 0.57,
            )
        )
    return candles
