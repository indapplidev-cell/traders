from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics


def test_feature_quality_diagnostics_ml32_adds_weak_signal_and_group_summary() -> None:
    payload = FeatureQualityDiagnostics().analyze(
        [
            {
                "direction_label": "UP",
                "features_json": {
                    "trend_strength": 1.2,
                    "body_size": 1.0,
                    "volume_ratio_20": 1.1,
                    "mystery_signal": 5.0,
                },
            },
            {
                "direction_label": "DOWN",
                "features_json": {
                    "trend_strength": -1.0,
                    "body_size": 1.0,
                    "volume_ratio_20": None,
                    "mystery_signal": 5.0,
                },
            },
        ]
    )

    assert "weak_signal_detected" in payload
    assert "feature_group_summary" in payload
    assert "top_weak_features" in payload
    assert "top_candidate_features" in payload
    assert "missing_value_summary" in payload
