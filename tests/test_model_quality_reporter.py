import json

from app.evaluation.model_quality_reporter import ModelQualityReporter
from app.evaluation.model_quality_validator import validate_model_quality


def test_model_quality_reporter_full_report_contains_all_metrics() -> None:
    reporter = ModelQualityReporter()
    result = _result()

    payload = reporter.build_full_quality_report(result)

    assert payload["validator_name"] == "model_training_quality_validator"
    assert "quality_status" in payload
    assert "reasons" in payload
    assert "warnings" in payload
    assert "integration_status" in payload


def test_model_quality_reporter_compact_summary_contains_only_key_metrics() -> None:
    reporter = ModelQualityReporter()
    result = _result()

    payload = reporter.build_compact_quality_summary(result)

    assert payload["reason_count"] == 6
    assert payload["warning_count"] == 0
    assert "reasons" not in payload
    assert "integration_status" not in payload


def test_model_quality_reporter_json_serialization_works() -> None:
    reporter = ModelQualityReporter()
    result = _result()

    json.loads(reporter.full_report_to_json(result))
    json.loads(reporter.compact_summary_to_json(result))


def _result():
    return validate_model_quality(
        training_summary={
            "model_version": "mv_quality_candidate",
            "run_id": "train_mv_quality_candidate",
            "dataset_summary": {
                "dataset_rows": 2400,
                "train_rows": 1600,
                "validation_rows": 400,
                "test_rows": 400,
            },
            "test_metrics": {"accuracy": 0.41},
            "collapse_detected": False,
            "real_training_executed": True,
            "sample_mode": False,
        },
        baseline_summary={
            "baselines": {
                "majority_class": {"test": {"accuracy": 0.35}},
            }
        },
        probability_diagnostics={},
        calibration_summary={"calibration_status": "ACCEPTABLE"},
        profit_aware_summary={"profit_aware_status": "POSITIVE"},
        walk_forward_summary={
            "walk_forward_status": "STABLE",
            "summary": {"fold_count": 4, "total_test_signal_count": 120},
        },
        gate_policy_replay_summary={
            "gate_policy_replay_status": "ACCEPTABLE",
            "total_records": 24,
            "valid_records": 22,
            "invalid_records": 2,
        },
    )
