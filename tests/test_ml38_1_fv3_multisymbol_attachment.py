from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.diagnostics.real_feature_diagnostics_service import RealFeatureDiagnosticsService
from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def test_ml38_1_runtime_diagnostic_rows_build_fv3_features_when_persisted_rows_are_missing(
    monkeypatch,
) -> None:
    candles = _build_base_candles(260)

    monkeypatch.setattr(
        "app.experiments.feature_regime_experiment_runner.get_session",
        lambda: nullcontext(object()),
    )
    monkeypatch.setattr(
        "app.experiments.feature_regime_experiment_runner.CandleRepository.get_all",
        lambda self, symbol, interval: candles,
    )
    monkeypatch.setattr(
        "app.experiments.feature_regime_experiment_runner.FeatureRepository.get_all",
        lambda self, symbol, interval, feature_version: [],
    )
    monkeypatch.setattr(
        "app.experiments.feature_regime_experiment_runner.RegimeLabelBuilder.build",
        _fake_regime_label_builder_result,
    )

    runner = FeatureRegimeExperimentRunner()
    rows, warnings, source, regime_status = runner._build_runtime_diagnostic_rows(
        config=FeatureRegimeExperimentConfig(
            symbol="ETHUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv3_candle_ta_context",
        ),
        label_config_payload={
            "label_version": "lv2_h12_thr05_tp15_sl10",
            "horizon": 12,
            "threshold": 0.5,
            "take_profit_atr": 1.5,
            "stop_loss_atr": 1.0,
        },
    )

    assert rows
    assert warnings == []
    assert source.startswith("runtime_feature_builder")
    assert RealFeatureDiagnosticsService.FV3_REQUIRED_FEATURES.issubset(rows[-1].features_json)
    assert regime_status["reason"] is None


def _build_base_candles(count: int) -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        open_price = 100.0 + (index * 0.35)
        close_price = open_price + 0.55
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=15 * index),
                open=open_price,
                high=close_price + 0.9,
                low=open_price - 0.7,
                close=close_price,
                volume=1000.0 + (index * 4.0),
                taker_buy_base_volume=(1000.0 + (index * 4.0)) * 0.56,
            )
        )
    return candles


def _fake_regime_label_builder_result(self, *, candles, symbol, interval, feature_rows, base_config):
    records = []
    for feature_row in feature_rows[:-12]:
        records.append(
            SimpleNamespace(
                candle_open_time=feature_row.candle_open_time,
                label_version=base_config.label_version,
                horizon_candles=base_config.horizon_candles,
                direction_label="UP",
                tp_before_sl=True,
                future_return=0.01,
                future_move_atr=0.2,
                max_favorable_move_atr=0.3,
                max_adverse_move_atr=0.1,
            )
        )
    return SimpleNamespace(
        records=records,
        warnings=[],
        missing_requirements=[],
        to_dict=lambda: {
            "regime_label_builder_status": "built",
            "regime_label_builder_used_in_training": True,
            "regime_specific_training_applied": True,
            "missing_requirements": [],
            "warnings": [],
            "reason": None,
        },
    )
