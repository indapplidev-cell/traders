from app.labels.regime_label_integration_status import RegimeLabelIntegrationStatus


def test_regime_label_integration_status_applied_true_only_when_all_requirements_are_met() -> None:
    payload = RegimeLabelIntegrationStatus().build_status(
        regime_specific_labeling_available=True,
        regime_features_attached=True,
        regime_feature_count=6,
        training_pipeline_supports_regime_labels=True,
    )

    assert payload["regime_specific_training_applied"] is True
    assert payload["missing_requirements"] == []


def test_regime_label_integration_status_reports_missing_requirements_when_not_applied() -> None:
    payload = RegimeLabelIntegrationStatus().build_status(
        regime_specific_labeling_available=False,
        regime_features_attached=False,
        regime_feature_count=0,
        training_pipeline_supports_regime_labels=False,
    )

    assert payload["regime_specific_training_applied"] is False
    assert payload["missing_requirements"]
