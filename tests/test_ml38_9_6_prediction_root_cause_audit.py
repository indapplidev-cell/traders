from app.diagnostics.prediction_root_cause_audit import PredictionRootCauseAuditor


def test_prediction_root_cause_audit_detects_up_collapse() -> None:
    actual = ["DOWN"] * 30 + ["FLAT"] * 20 + ["UP"] * 30
    predicted = ["UP"] * 80
    probabilities = [{"DOWN": 0.10, "FLAT": 0.05, "UP": 0.85} for _ in range(80)]

    audit = PredictionRootCauseAuditor().build(
        actual_labels=actual,
        predicted_labels=predicted,
        probability_rows=probabilities,
        split_names=["test"] * 80,
        regime_labels=["trend_up"] * 80,
        symbol="SOLUSDT",
        config_id="synthetic_up_collapse",
        decision_source="unit_test",
    )

    assert audit["diagnostic_name"] == "prediction_root_cause_audit"
    assert audit["diagnostic_version"] == "ml38_9_6"
    assert audit["diagnostic_only"] is True
    assert audit["actual_distribution"]["ratios"]["DOWN"] == 0.375
    assert audit["predicted_distribution"]["ratios"]["UP"] == 1.0
    assert audit["confusion_matrix"]["row_ratios"]["DOWN"]["UP"] == 1.0
    assert audit["up_collapse_signature"]["actual_down_predicted_up_ratio"] == 1.0
    assert "actual_down_rows_mapped_to_up" in audit["warnings"]
    assert "predicted_up_often_actual_down_or_flat" in audit["warnings"]


def test_prediction_root_cause_audit_reports_split_drift() -> None:
    actual = ["UP"] * 10 + ["DOWN"] * 10
    predicted = ["UP"] * 20
    probabilities = [{"DOWN": 0.2, "FLAT": 0.1, "UP": 0.7} for _ in range(20)]
    splits = ["train"] * 10 + ["test"] * 10

    audit = PredictionRootCauseAuditor().build(
        actual_labels=actual,
        predicted_labels=predicted,
        probability_rows=probabilities,
        split_names=splits,
    )

    assert audit["split_drift"]["available"] is True
    assert audit["split_drift"]["splits"]["train"]["ratios"]["UP"] == 1.0
    assert audit["split_drift"]["splits"]["test"]["ratios"]["DOWN"] == 1.0
