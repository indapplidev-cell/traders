from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def _fv3_runtime_rows(symbol: str) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "interval": "15m",
            "direction_label": "UP",
            "features_json": {
                "doji_score": 0.1,
                "hammer_score": 0.7,
                "trend_slope_long": 1.5,
                "distance_to_support": 0.5,
                "bollinger_position": 0.4,
                "stochastic_k": 45.0,
                "volume_zscore": 0.8,
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
                "doji_score": 0.0,
                "hammer_score": 0.2,
                "trend_slope_long": -1.2,
                "distance_to_support": 0.7,
                "bollinger_position": 0.3,
                "stochastic_k": 35.0,
                "volume_zscore": -0.4,
                "regime_trend_up": 0.0,
                "regime_trend_down": 1.0,
                "regime_range": 0.0,
                "regime_high_volatility": 1.0,
                "regime_low_volatility": 0.0,
                "regime_unknown": 0.0,
            },
        },
    ]


def test_ml38_1_real_diagnostics_falls_back_from_partial_dataset_rows_without_silent_fv3_success(
    monkeypatch,
) -> None:
    def fake_build_rows(self, **kwargs):
        return (
            [
                {
                    "direction_label": "UP",
                    "features_json": {
                        "regime_trend_up": 1.0,
                        "regime_trend_down": 0.0,
                    },
                }
            ],
            {"dataset_rows": 1},
        )

    def fake_runtime_rows(self, *, config, label_config_payload):
        return (
            _fv3_runtime_rows(config.symbol),
            [],
            "runtime_regime_label_builder",
            {
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
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
    payload = runner._build_real_feature_diagnostics(
        config=FeatureRegimeExperimentConfig(
            symbol="SOLUSDT",
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

    assert payload["source"] == "runtime_regime_label_builder"
    assert payload["real_feature_diagnostics_used"] is True
    assert payload["row_count"] == 2
    assert payload["candle_ta_context_features_attached"] is True
    assert payload["regime_feature_diagnostics"]["regime_data_available"] is True
    assert "dataset_rows_missing_requested_feature_attachment" in payload["warnings"]
