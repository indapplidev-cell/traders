import json

from app.evaluation.model_quality_validator import (
    INSUFFICIENT_REAL_HISTORY,
    NEEDS_MORE_DATA,
    QUALITY_APPROVED,
    QUALITY_REJECTED,
    validate_model_quality,
)


def test_model_quality_validator_can_approve_quality() -> None:
    result = validate_model_quality(
        training_summary=_training_summary(real_training_executed=True),
        baseline_summary=_baseline_summary(0.35),
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

    payload = result.to_dict()

    assert payload["quality_status"] == QUALITY_APPROVED
    assert payload["approved_for_traders_core_integration"] is True
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert payload["integration_status"]["orders_enabled"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_model_quality_validator_rejects_collapse() -> None:
    result = validate_model_quality(
        training_summary=_training_summary(collapse_detected=True, real_training_executed=True),
        baseline_summary=_baseline_summary(0.35),
        probability_diagnostics={},
        calibration_summary={"calibration_status": "ACCEPTABLE"},
        profit_aware_summary={"profit_aware_status": "POSITIVE"},
        walk_forward_summary={"walk_forward_status": "STABLE"},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE", "total_records": 24},
    )

    assert result.quality_status == QUALITY_REJECTED


def test_model_quality_validator_rejects_when_model_does_not_beat_baseline() -> None:
    result = validate_model_quality(
        training_summary=_training_summary(model_accuracy=0.37, real_training_executed=True),
        baseline_summary=_baseline_summary(0.38),
        probability_diagnostics={},
        calibration_summary={"calibration_status": "ACCEPTABLE"},
        profit_aware_summary={"profit_aware_status": "POSITIVE"},
        walk_forward_summary={"walk_forward_status": "STABLE"},
        gate_policy_replay_summary={"gate_policy_replay_status": "ACCEPTABLE", "total_records": 24},
    )

    assert result.quality_status == QUALITY_REJECTED


def test_model_quality_validator_detects_missing_history() -> None:
    result = validate_model_quality(
        training_summary={},
        baseline_summary={},
        probability_diagnostics={},
        calibration_summary={},
        profit_aware_summary={},
        walk_forward_summary={},
        gate_policy_replay_summary={},
    )

    assert result.quality_status == INSUFFICIENT_REAL_HISTORY


def test_model_quality_validator_marks_small_sample_as_needing_more_data() -> None:
    result = validate_model_quality(
        training_summary=_training_summary(dataset_rows=400, train_rows=250, val_rows=50, test_rows=100, real_training_executed=True),
        baseline_summary=_baseline_summary(0.35),
        probability_diagnostics={},
        calibration_summary={"calibration_status": "ACCEPTABLE"},
        profit_aware_summary={"profit_aware_status": "ACCEPTABLE"},
        walk_forward_summary={
            "walk_forward_status": "NEEDS_MORE_DATA",
            "summary": {"fold_count": 1, "total_test_signal_count": 12},
        },
        gate_policy_replay_summary={
            "gate_policy_replay_status": "SAMPLE_ONLY",
            "total_records": 5,
            "valid_records": 4,
            "invalid_records": 1,
        },
    )

    assert result.quality_status == NEEDS_MORE_DATA
    assert result.approved_for_live_trading is False
    assert result.approved_for_auto_activation is False


def _training_summary(
    *,
    dataset_rows: int = 2400,
    train_rows: int = 1600,
    val_rows: int = 400,
    test_rows: int = 400,
    model_accuracy: float = 0.41,
    collapse_detected: bool = False,
    real_training_executed: bool = False,
) -> dict[str, object]:
    return {
        "model_version": "mv_quality_candidate",
        "run_id": "train_mv_quality_candidate",
        "dataset_summary": {
            "dataset_rows": dataset_rows,
            "train_rows": train_rows,
            "validation_rows": val_rows,
            "test_rows": test_rows,
        },
        "test_metrics": {
            "accuracy": model_accuracy,
        },
        "collapse_detected": collapse_detected,
        "real_training_executed": real_training_executed,
        "sample_mode": False,
    }


def _baseline_summary(accuracy: float) -> dict[str, object]:
    return {
        "baselines": {
            "majority_class": {
                "test": {
                    "accuracy": accuracy,
                }
            }
        }
    }
