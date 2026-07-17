from types import SimpleNamespace
from app.engine_observation.observation_status import evaluate_verdict


def arguments():
    thresholds = SimpleNamespace(missing_fail_ratio=.01, missing_warning_ratio=0,
        freshness_fail_ratio=.05, freshness_warning_ratio=.01, completion_warning_ratio=.99,
        latency_fail_ms=900000, latency_warning_ms=300000)
    return dict(coverage={"aggregate": {"expected_windows": 100, "missing_windows": 0,
        "duplicate_windows": 0, "completion_ratio": 1}}, integrity={"checks": {"orphan_result_rows": 0,
        "invalid_transitions": 0, "negative_duration": 0, "stale_reservations": 0}},
        safety={"violation_count": 0}, latency={"future_boundary_processing_count": 0,
        "aggregate": {"end_to_end_latency_ms": {"p95": 1000}}}, freshness_skip_count=0,
        error_count=0, sync_state={"non_ok_rows": 0, "severe_rows": 0}, thresholds=thresholds)


def test_no_plan_dominance_is_not_a_failure():
    verdict, _, _ = evaluate_verdict(**arguments())
    assert verdict == "OBSERVATION_PASSED"


def test_safety_violation_fails():
    args = arguments(); args["safety"] = {"violation_count": 1}
    assert evaluate_verdict(**args)[0] == "OBSERVATION_FAILED"
