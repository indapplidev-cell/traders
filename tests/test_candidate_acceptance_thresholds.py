from app.evaluation.candidate_acceptance_thresholds import (
    default_candidate_acceptance_thresholds,
)


def test_candidate_acceptance_thresholds_default_values_and_gap_policy() -> None:
    thresholds = default_candidate_acceptance_thresholds()

    assert thresholds.to_dict()["min_accuracy_edge"] == 0.005
    assert thresholds.to_dict()["max_predicted_class_share"] == 0.70
    assert thresholds.gap_severity_allowed("OK") is True
    assert thresholds.gap_severity_allowed("MODERATE") is True
    assert thresholds.gap_severity_allowed("HIGH") is False
