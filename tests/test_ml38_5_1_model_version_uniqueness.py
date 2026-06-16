from datetime import datetime, timezone

from app.training.model_version_builder import build_unique_model_version


def test_model_version_includes_symbol_interval_horizon_label_and_suffix() -> None:
    version = build_unique_model_version(
        model_name="candle_mlp",
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=8,
        label_version="lv2_h08_thr03_tp10_sl10",
        created_at=datetime(2026, 6, 16, 12, 23, 1, 697583, tzinfo=timezone.utc),
        unique_suffix="abc123",
    )

    assert version.startswith("ml_candle_mlp_v1_")
    assert "solusdt" in version
    assert "15m" in version
    assert "h8" in version
    assert "lv2_h08_thr03_tp10_sl10" in version
    assert "2026_06_16_122301_697583" in version
    assert "abc123" in version
    assert len(version) <= 100


def test_model_version_differs_for_parallel_symbols_with_same_timestamp_and_suffix() -> None:
    created_at = datetime(2026, 6, 16, 12, 23, 1, 697583, tzinfo=timezone.utc)

    btc_version = build_unique_model_version(
        model_name="candle_mlp",
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        label_version="lv2_h08_thr03_tp10_sl10",
        created_at=created_at,
        unique_suffix="same",
    )

    sol_version = build_unique_model_version(
        model_name="candle_mlp",
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=8,
        label_version="lv2_h08_thr03_tp10_sl10",
        created_at=created_at,
        unique_suffix="same",
    )

    assert btc_version != sol_version
