from types import SimpleNamespace

from app.diagnostics.feature_label_separability_audit import FeatureLabelSeparabilityAudit


def test_feature_label_separability_audit_handles_empty_rows() -> None:
    payload = FeatureLabelSeparabilityAudit().evaluate([])

    assert payload["diagnostic_name"] == "feature_label_separability_audit"
    assert payload["global_separability_rating"] == "UNAVAILABLE"
    assert payload["row_count"] == 0


def test_feature_label_separability_audit_detects_strong_up_down_difference() -> None:
    rows = [
        SimpleNamespace(direction_label="UP", features_json={"trend_strength": 1.2, "volume_ratio_20": 1.4}),
        SimpleNamespace(direction_label="UP", features_json={"trend_strength": 1.1, "volume_ratio_20": 1.3}),
        {"direction_label": "DOWN", "features_json": {"trend_strength": -1.0, "volume_ratio_20": 0.7}},
        {"direction_label": "DOWN", "features_json": {"trend_strength": -1.2, "volume_ratio_20": 0.6}},
        {"direction_label": "FLAT", "features_json": {"trend_strength": 0.05, "volume_ratio_20": 1.0}},
        {"direction_label": "FLAT", "features_json": {"trend_strength": 0.02, "volume_ratio_20": 0.95}},
    ]

    payload = FeatureLabelSeparabilityAudit().evaluate(rows)

    assert payload["row_count"] == 6
    assert payload["global_separability_rating"] in {"GOOD", "WATCH"}
    assert payload["top_separating_features"][0]["feature_name"] == "trend_strength"
    assert payload["top_separating_features"][0]["up_down_effect_size"] is not None

