from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def _runtime_rows(symbol: str) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "interval": "15m",
            "direction_label": "UP",
            "features_json": {
                "return_1": 0.01,
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
                "regime_unknown": 0.0,
            },
        },
        {
            "symbol": symbol,
            "interval": "15m",
            "direction_label": "DOWN",
            "features_json": {
                "return_1": -0.01,
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
                "regime_unknown": 0.0,
            },
        },
    ]


def test_real_feature_diagnostics_runtime_fallback_supports_multiple_symbols(monkeypatch) -> None:
    def fake_build_rows(self, **kwargs):
        return [], {"dataset_rows": 0}

    def fake_runtime_rows(self, *, config, label_config_payload):
        return (
            _runtime_rows(config.symbol),
            [],
            "runtime_regime_label_builder",
            {
                "regime_label_builder_available": True,
                "regime_label_builder_used_in_training": True,
                "regime_specific_labeling_available": True,
                "regime_specific_training_applied": True,
                "regime_label_config_used": {"trend_up": f"{label_config_payload['label_version']}_trend_up"},
                "label_distribution_by_regime": {"trend_up": {"UP": 1, "DOWN": 0, "FLAT": 0}},
                "missing_requirements": [],
                "warnings": [],
                "reason": None,
            },
        )

    monkeypatch.setattr("app.dataset.dataset_builder.DatasetBuilder.build_rows", fake_build_rows)
    monkeypatch.setattr(
        FeatureRegimeExperimentRunner,
        "_build_runtime_diagnostic_rows",
        fake_runtime_rows,
    )

    runner = FeatureRegimeExperimentRunner()
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        payload = runner._build_real_feature_diagnostics(
            config=FeatureRegimeExperimentConfig(
                symbol=symbol,
                interval="15m",
                start_date="2025-01-01",
            ),
            label_config_payload={
                "label_version": "lv2_h12_thr05_tp15_sl10",
                "horizon": 12,
                "threshold": 0.5,
                "take_profit_atr": 1.5,
                "stop_loss_atr": 1.0,
            },
        )
        assert payload["real_feature_diagnostics_used"] is True
        assert payload["row_count"] == 2
        assert payload["regime_feature_diagnostics"]["regime_data_available"] is True
        assert "dataset_rows_unavailable" not in payload["warnings"]

