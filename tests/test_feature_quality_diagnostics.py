from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics


def test_feature_quality_diagnostics_flags_weak_features_and_ranks_signal() -> None:
    payload = FeatureQualityDiagnostics().analyze(
        [
            {
                "direction_label": "UP",
                "features_json": {"trend_strength": 1.2, "volatility": 0.55, "flat_bias": 0.1},
            },
            {
                "direction_label": "UP",
                "features_json": {"trend_strength": 1.0, "volatility": 0.58, "flat_bias": 0.1},
            },
            {
                "direction_label": "DOWN",
                "features_json": {"trend_strength": -1.1, "volatility": 0.61, "flat_bias": 0.1},
            },
            {
                "direction_label": "DOWN",
                "features_json": {"trend_strength": -0.8, "volatility": None, "flat_bias": 0.1},
            },
            {
                "direction_label": "FLAT",
                "features_json": {"trend_strength": 0.05, "volatility": 0.20, "flat_bias": 0.1},
            },
        ]
    )

    assert payload["diagnostic_version"] == "ml30"
    assert payload["feature_count"] == 3
    assert payload["constant_feature_count"] == 1
    assert payload["high_missing_feature_count"] == 1
    assert payload["low_variance_feature_count"] >= 1
    assert payload["top_candidate_features"][0]["feature_name"] == "trend_strength"
    assert "constant_features_detected" in payload["weak_feature_warnings"]
    assert "high_missing_features_detected" in payload["weak_feature_warnings"]


def test_feature_quality_diagnostics_handles_empty_rows() -> None:
    payload = FeatureQualityDiagnostics().analyze([])

    assert payload["row_count"] == 0
    assert payload["feature_count"] == 0
    assert payload["feature_signal_score"] == 0.0
