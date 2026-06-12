import json

from app.cli.commands import build_feature_regime_integration_preview_payload
from app.labels.regime_label_integration_status import RegimeLabelIntegrationStatus


def test_regime_feature_integration_preview_reports_attached_fields() -> None:
    payload = build_feature_regime_integration_preview_payload()

    assert payload["feature_version_available"] is True
    assert payload["feature_version_used"] == "fv2"
    assert payload["regime_features_attached"] is True
    assert payload["regime_feature_count"] >= 6
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_missing_regime_feature_requirements_are_reported_when_unavailable() -> None:
    payload = RegimeLabelIntegrationStatus().build_status(
        regime_specific_labeling_available=True,
        regime_features_attached=False,
        regime_feature_count=0,
        training_pipeline_supports_regime_labels=False,
    )

    assert payload["regime_specific_training_applied"] is False
    assert "regime_features_not_attached" in payload["missing_requirements"]
