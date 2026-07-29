from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest import mock

import pytest

from app.observability.health_classifier import (
    classify_health_body,
    classify_health_payload,
)
from app.observability.stability_acceptance import evaluate_acceptance
from app.observability.stability_models import (
    ClassificationReasonCode,
    ObservationAggregates,
    RuntimeHealthClassification,
    SafeHttpResult,
    SampleTransport,
    ScheduleValidation,
)
from scripts import readonly_api_stability_observer as observer


FIXTURE = (
    Path(__file__).parent / "fixtures" / "readonly_api_health_unknown_minimal.json"
)


def payload(
    timing: str = "CURRENT",
    *,
    status: str | None = None,
    operational: bool | None = None,
    ready: bool | None = None,
    blocking: bool | None = None,
) -> dict:
    non_blocking = timing in {"CURRENT", "WITHIN_GRACE"}
    return {
        "api_version": "v1",
        "generated_at": "2026-07-28T20:00:00.000Z",
        "data": {
            "status": status
            or {
                "CURRENT": "OK",
                "WITHIN_GRACE": "OK",
                "DEADLINE_EXPIRED": "DEGRADED",
                "DEGRADED": "DEGRADED",
                "UNKNOWN": "UNKNOWN",
            }.get(timing, "OK"),
            "observed_at": "2026-07-28T20:00:00.000Z",
            "services": [],
            "timing_state": timing,
            "reason_code": (
                "BOUNDARY_WITHIN_GRACE" if timing == "WITHIN_GRACE" else timing
            ),
            "operational": non_blocking if operational is None else operational,
            "ready": non_blocking if ready is None else ready,
            "acceptance_blocking": (
                not non_blocking if blocking is None else blocking
            ),
        },
    }


def legacy_classification(value: object) -> RuntimeHealthClassification:
    if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
        return RuntimeHealthClassification.UNKNOWN
    data = value["data"]
    values = {
        str(data.get("timing_state", "")).upper(),
        str(data.get("reason_code", "")).upper(),
        str(data.get("status", "")).upper(),
    }
    if "DEADLINE_EXPIRED" in values or "DEADLINE_EXCEEDED" in values:
        return RuntimeHealthClassification.DEADLINE_EXPIRED
    if "WITHIN_GRACE" in values or "BOUNDARY_WITHIN_GRACE" in values:
        return RuntimeHealthClassification.WITHIN_GRACE
    if "CURRENT" in values:
        return RuntimeHealthClassification.CURRENT
    if values.intersection({"DEGRADED", "RECOVERING", "ERROR", "NOT_READY"}):
        return RuntimeHealthClassification.DEGRADED
    return RuntimeHealthClassification.UNKNOWN


def observation(*results: SafeHttpResult) -> ObservationAggregates:
    return ObservationAggregates(
        first_completed_monotonic_ns=1,
        last_completed_monotonic_ns=4_500_000_000_001,
        http_results=list(results),
    )


def result_for(decision) -> SafeHttpResult:
    return SafeHttpResult(
        "/api/v1/health",
        SampleTransport.SUCCESS,
        200,
        0.01,
        300,
        "application/json",
        runtime_classification=decision.runtime_classification,
        classification_reason_code=decision.classification_reason_code,
        classifier_branch_id=decision.classifier_branch_id,
        safe_structure_descriptor=decision.safe_structure_descriptor,
    )


def test_minimal_proven_path_fixture_was_generic_unknown_before_and_is_exact_after():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert legacy_classification(value) is RuntimeHealthClassification.UNKNOWN
    decision = classify_health_payload(value)
    assert decision.runtime_classification is RuntimeHealthClassification.UNKNOWN
    assert (
        decision.classification_reason_code
        is ClassificationReasonCode.GENUINELY_UNKNOWN_RUNTIME_STATE
    )
    assert decision.classifier_branch_id == "HEALTH_SCHEMA_VALID_UNKNOWN_STATE"


@pytest.mark.parametrize(
    ("timing", "expected", "reason", "branch"),
    [
        ("CURRENT", RuntimeHealthClassification.CURRENT, "CLASSIFIED_CURRENT", "HEALTH_CURRENT_CONTRACT"),
        ("WITHIN_GRACE", RuntimeHealthClassification.WITHIN_GRACE, "CLASSIFIED_WITHIN_GRACE", "HEALTH_WITHIN_GRACE_CONTRACT"),
        ("DEADLINE_EXPIRED", RuntimeHealthClassification.DEADLINE_EXPIRED, "CLASSIFIED_DEADLINE_EXPIRED", "HEALTH_DEADLINE_EXPIRED_CONTRACT"),
        ("DEGRADED", RuntimeHealthClassification.DEGRADED, "CLASSIFIED_DEGRADED", "HEALTH_DEGRADED_CONTRACT"),
    ],
)
def test_known_runtime_contracts(timing, expected, reason, branch):
    decision = classify_health_payload(payload(timing))
    assert decision.runtime_classification is expected
    assert decision.classification_reason_code.value == reason
    assert decision.classifier_branch_id == branch


def test_missing_required_field_is_fail_closed():
    value = payload()
    del value["data"]["ready"]
    decision = classify_health_payload(value)
    assert decision.classification_reason_code is ClassificationReasonCode.REQUIRED_HEALTH_FIELD_MISSING
    assert decision.runtime_classification is RuntimeHealthClassification.UNKNOWN


def test_wrong_field_type_is_fail_closed():
    value = payload()
    value["data"]["ready"] = 1
    decision = classify_health_payload(value)
    assert decision.classification_reason_code is ClassificationReasonCode.HEALTH_FIELD_TYPE_MISMATCH


def test_unknown_enum_is_fail_closed():
    decision = classify_health_payload(payload("FUTURE_STATE"))
    assert decision.classification_reason_code is ClassificationReasonCode.UNKNOWN_HEALTH_ENUM


def test_contradictory_indicators_are_fail_closed():
    decision = classify_health_payload(payload("CURRENT", ready=False))
    assert decision.classification_reason_code is ClassificationReasonCode.CONTRADICTORY_HEALTH_SIGNALS
    assert decision.runtime_classification is RuntimeHealthClassification.UNKNOWN


def test_invalid_root_json_type_is_fail_closed():
    decision = classify_health_payload([])
    assert decision.classification_reason_code is ClassificationReasonCode.INVALID_HEALTH_ROOT_TYPE
    assert decision.safe_structure_descriptor.root_json_type == "array"


def test_invalid_json_is_fail_closed_without_body_hash():
    decision = classify_health_body(b"{not-json")
    assert decision.classification_reason_code is ClassificationReasonCode.HEALTH_JSON_PARSE_FAILED
    assert decision.safe_structure_descriptor.json_parse_success is False
    assert decision.safe_structure_descriptor.root_json_type == "invalid-json"


def test_http_success_plus_parse_failure_is_explicit():
    class InvalidResponse:
        status = 200

        class Headers:
            @staticmethod
            def get_content_type():
                return "application/json"

        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        @staticmethod
        def read(_limit):
            return b"not-json"

    with mock.patch.object(observer.urllib.request, "urlopen", return_value=InvalidResponse()):
        sampled = observer.sample_http("http://127.0.0.1:8765", "/api/v1/health")
    assert sampled.numeric_http_status == 200
    assert sampled.transport is SampleTransport.PARSE_ERROR
    assert sampled.classification_reason_code is ClassificationReasonCode.HEALTH_JSON_PARSE_FAILED


def test_reason_code_field_is_not_free_text_primary_authority():
    value = payload("CURRENT")
    value["data"]["reason_code"] = "ANOTHER_PUBLIC_REASON"
    assert classify_health_payload(value).runtime_classification is RuntimeHealthClassification.CURRENT


def test_safe_descriptor_is_bounded_and_allowlisted():
    value = payload()
    value["secret"] = "must-not-appear"
    value["data"]["private"] = "must-not-appear"
    descriptor = classify_health_payload(value).safe_structure_descriptor
    assert len(descriptor.top_level_keys) <= 4
    assert len(descriptor.nested_paths_present) <= 8
    assert "secret" not in repr(descriptor)
    assert "private" not in repr(descriptor)


def test_no_full_payload_or_secret_derived_fields_are_retained():
    value = payload()
    value["data"]["private"] = "password=do-not-retain"
    sampled = result_for(classify_health_payload(value))
    rendered = repr(sampled).lower()
    assert "do-not-retain" not in rendered
    assert "password" not in rendered
    assert not hasattr(sampled, "payload")
    assert not hasattr(sampled, "safe_payload_hash")


def test_classifier_branch_id_is_deterministic():
    first = classify_health_payload(payload())
    second = classify_health_payload(payload())
    assert first.classifier_branch_id == second.classifier_branch_id


def test_structural_digest_is_deterministic():
    first = classify_health_payload(payload()).safe_structure_descriptor
    second = classify_health_payload(payload()).safe_structure_descriptor
    assert first.structural_digest == second.structural_digest


def test_structural_digest_changes_on_structural_change():
    first = classify_health_payload(payload()).safe_structure_descriptor
    changed = payload()
    del changed["data"]["services"]
    second = classify_health_payload(changed).safe_structure_descriptor
    assert first.structural_digest != second.structural_digest


def test_structural_digest_ignores_non_allowlisted_values():
    first_value = payload()
    first_value["data"]["private"] = "one"
    second_value = deepcopy(first_value)
    second_value["data"]["private"] = "two"
    second_value["other"] = {"changed": True}
    first = classify_health_payload(first_value).safe_structure_descriptor
    second = classify_health_payload(second_value).safe_structure_descriptor
    assert first.structural_digest == second.structural_digest


def test_acceptance_exposes_exact_unknown_reason():
    decision = classify_health_payload(json.loads(FIXTURE.read_text(encoding="utf-8")))
    accepted = evaluate_acceptance(observation(result_for(decision)), ScheduleValidation())
    assert accepted.reasons == (
        "RUNTIME_UNKNOWN:GENUINELY_UNKNOWN_RUNTIME_STATE:"
        "HEALTH_SCHEMA_VALID_UNKNOWN_STATE:/api/v1/health",
    )


def test_one_unknown_remains_fail_closed():
    decision = classify_health_payload(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert not evaluate_acceptance(
        observation(result_for(decision)), ScheduleValidation()
    ).accepted


def test_zero_unknown_can_pass_when_other_gates_pass():
    decision = classify_health_payload(payload())
    assert evaluate_acceptance(
        observation(result_for(decision)), ScheduleValidation()
    ).accepted


def test_historical_failed_window_is_not_reclassified():
    historical = SafeHttpResult(
        "/api/v1/health",
        SampleTransport.SUCCESS,
        200,
        0.01,
        0,
        None,
        runtime_classification=RuntimeHealthClassification.UNKNOWN,
        classification_reason_code=ClassificationReasonCode.GENUINELY_UNKNOWN_RUNTIME_STATE,
        classifier_branch_id="HISTORICAL_CONTEXT_NOT_RETAINED",
    )
    decision = evaluate_acceptance(observation(historical), ScheduleValidation())
    assert not decision.accepted
    assert "RUNTIME_UNKNOWN" in decision.reasons[0]


def test_evidence_model_excludes_traceback_raw_body_and_full_payload_digest():
    fields = SafeHttpResult.__dataclass_fields__
    assert "payload" not in fields
    assert "raw_body" not in fields
    assert "traceback" not in fields
    assert "safe_payload_hash" not in fields


def test_unknown_capture_keeps_exact_safe_schedule_context():
    class UnknownResponse:
        status = 200

        class Headers:
            @staticmethod
            def get_content_type():
                return "application/json"

        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        @staticmethod
        def read(_limit):
            return FIXTURE.read_bytes()

    with mock.patch.object(observer.urllib.request, "urlopen", return_value=UnknownResponse()):
        sampled = observer.sample_http(
            "http://127.0.0.1:8765",
            "/api/v1/health",
            sample_sequence_id=212,
            sample_phase=observer.PhaseName.BOUNDARY,
            sample_utc="2026-07-28T20:00:01.000000+00:00",
        )
    assert sampled.sample_sequence_id == 212
    assert sampled.sample_phase is observer.PhaseName.BOUNDARY
    assert sampled.sample_utc == "2026-07-28T20:00:01.000000+00:00"


def test_unknown_evidence_renderer_limit_is_fixed():
    assert observer.MAX_UNKNOWN_DETAILS == 20
    decision = classify_health_payload(
        json.loads(FIXTURE.read_text(encoding="utf-8"))
    )
    rendered, truncated = observer.render_unknown_details(
        [result_for(decision)] * 21
    )
    assert len(rendered) == 20
    assert truncated is True
