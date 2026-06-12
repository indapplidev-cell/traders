import json

from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer


def test_feature_group_quality_groups_by_name_and_detects_warnings() -> None:
    payload = FeatureGroupQualityScorer().analyze(
        [
            {
                "direction_label": "UP",
                "features_json": {
                    "body_size": 1.0,
                    "atr_14": 2.0,
                    "volume_ratio_20": 1.2,
                    "rsi_14": 60.0,
                    "mystery_signal": 5.0,
                },
            },
            {
                "direction_label": "DOWN",
                "features_json": {
                    "body_size": 1.0,
                    "atr_14": 2.0,
                    "volume_ratio_20": None,
                    "rsi_14": 40.0,
                    "mystery_signal": 5.0,
                },
            },
        ]
    )

    groups = {item["group_name"]: item for item in payload["groups"]}

    assert "price_action" in groups
    assert "volatility" in groups
    assert "volume" in groups
    assert "momentum" in groups
    assert "unknown" in groups
    assert groups["unknown"]["constant_feature_count"] >= 1
    assert groups["volume"]["missing_rate"] > 0.0
    assert json.dumps(payload)
