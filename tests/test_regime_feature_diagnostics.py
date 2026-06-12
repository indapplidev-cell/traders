import json

from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics


def test_regime_feature_diagnostics_works_in_degraded_mode() -> None:
    payload = RegimeFeatureDiagnostics().analyze(
        [
            {
                "direction_label": "UP",
                "features_json": {"trend_strength": 1.0, "volume_ratio_20": 1.2},
            }
        ]
    )

    assert payload["regime_data_available"] is False
    assert payload["label_distribution_by_regime"] == {}
    assert payload["recommendations"]
    assert json.dumps(payload)


def test_regime_feature_diagnostics_works_with_sample_regimes() -> None:
    payload = RegimeFeatureDiagnostics().analyze(
        [
            {
                "direction_label": "UP",
                "features_json": {
                    "trend_strength": 1.2,
                    "regime_trend_up": 1.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 1.0,
                },
            },
            {
                "direction_label": "DOWN",
                "features_json": {
                    "trend_strength": -1.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 1.0,
                    "regime_range": 0.0,
                    "regime_high_volatility": 1.0,
                    "regime_low_volatility": 0.0,
                },
            },
            {
                "direction_label": "FLAT",
                "features_json": {
                    "trend_strength": 0.0,
                    "regime_trend_up": 0.0,
                    "regime_trend_down": 0.0,
                    "regime_range": 1.0,
                    "regime_high_volatility": 0.0,
                    "regime_low_volatility": 1.0,
                },
            },
        ]
    )

    assert payload["regime_data_available"] is True
    assert "trend_up" in payload["label_distribution_by_regime"]
    assert "unknown" in payload["feature_quality_by_regime"]
    assert payload["recommendations"]
    assert json.dumps(payload)
