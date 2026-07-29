"""Strict, fail-closed health classification with bounded structural evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .stability_models import (
    ClassificationReasonCode,
    RuntimeHealthClassification,
    SafeStructureDescriptor,
)


_TOP_LEVEL_ALLOWLIST = frozenset({"api_version", "data", "error", "generated_at"})
_HEALTH_FIELDS = (
    "status",
    "observed_at",
    "services",
    "timing_state",
    "reason_code",
    "operational",
    "ready",
    "acceptance_blocking",
)
_REQUIRED_CLASSIFIER_FIELDS = (
    "status",
    "observed_at",
    "services",
    "timing_state",
    "reason_code",
    "operational",
    "ready",
    "acceptance_blocking",
)
_PUBLIC_VALUE_FIELDS = frozenset(
    {
        "data.status",
        "data.timing_state",
        "data.reason_code",
        "data.operational",
        "data.ready",
        "data.acceptance_blocking",
    }
)
_PUBLIC_ENUM = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")
_STATUS_ENUM = frozenset(
    {"UNKNOWN", "OK", "STALE", "DEGRADED", "NOT_AVAILABLE", "ERROR", "OFFLINE"}
)
_TIMING_ENUM = frozenset(
    {"CURRENT", "WITHIN_GRACE", "DEADLINE_EXPIRED", "DEGRADED", "UNKNOWN"}
)


@dataclass(frozen=True, slots=True)
class HealthClassificationDecision:
    runtime_classification: RuntimeHealthClassification
    classification_reason_code: ClassificationReasonCode
    classifier_branch_id: str
    safe_structure_descriptor: SafeStructureDescriptor


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "other"


def _descriptor(
    payload: Any,
    *,
    json_parse_success: bool,
    parser_branch_id: str,
) -> SafeStructureDescriptor:
    top_level_keys: tuple[str, ...] = ()
    nested_paths: tuple[str, ...] = ()
    field_types: tuple[tuple[str, str], ...] = ()
    normalized_values: tuple[tuple[str, str], ...] = ()
    structural_items = [f"$:{_json_type(payload) if json_parse_success else 'invalid-json'}"]
    if isinstance(payload, dict):
        top_level_keys = tuple(sorted(set(payload).intersection(_TOP_LEVEL_ALLOWLIST)))
        top_level_types = tuple(
            (key, _json_type(payload[key])) for key in top_level_keys
        )
        structural_items.extend(f"{key}:{kind}" for key, kind in top_level_types)
        data = payload.get("data")
        if isinstance(data, dict):
            nested_paths = tuple(
                f"data.{field}" for field in _HEALTH_FIELDS if field in data
            )
            field_types = tuple(
                (path, _json_type(data[path.removeprefix("data.")]))
                for path in nested_paths
            )
            structural_items.extend(f"{path}:{kind}" for path, kind in field_types)
            public_values: list[tuple[str, str]] = []
            for path in nested_paths:
                if path not in _PUBLIC_VALUE_FIELDS:
                    continue
                value = data[path.removeprefix("data.")]
                if isinstance(value, bool):
                    public_values.append((path, str(value).lower()))
                elif isinstance(value, str):
                    normalized = value.strip().upper()
                    if _PUBLIC_ENUM.fullmatch(normalized):
                        public_values.append((path, normalized))
            normalized_values = tuple(public_values)
    digest_input = "\n".join(sorted(structural_items)).encode("ascii")
    return SafeStructureDescriptor(
        json_parse_success=json_parse_success,
        root_json_type=_json_type(payload) if json_parse_success else "invalid-json",
        top_level_keys=top_level_keys,
        nested_paths_present=nested_paths,
        field_types=field_types,
        normalized_public_values=normalized_values,
        parser_branch_id=parser_branch_id,
        structural_digest=hashlib.sha256(digest_input).hexdigest(),
    )


def _decision(
    classification: RuntimeHealthClassification,
    reason: ClassificationReasonCode,
    branch: str,
    descriptor: SafeStructureDescriptor,
) -> HealthClassificationDecision:
    return HealthClassificationDecision(classification, reason, branch, descriptor)


def classify_health_payload(payload: Any) -> HealthClassificationDecision:
    """Classify only the exact current response-model contract."""

    descriptor = _descriptor(
        payload,
        json_parse_success=True,
        parser_branch_id="PARSER_JSON_OK",
    )
    if not isinstance(payload, dict):
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.INVALID_HEALTH_ROOT_TYPE,
            "HEALTH_ROOT_NOT_OBJECT",
            descriptor,
        )
    if "api_version" not in payload or "generated_at" not in payload:
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.REQUIRED_HEALTH_FIELD_MISSING,
            "HEALTH_ENVELOPE_FIELD_MISSING",
            descriptor,
        )
    if not isinstance(payload["api_version"], str) or not isinstance(
        payload["generated_at"], str
    ):
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.HEALTH_FIELD_TYPE_MISMATCH,
            "HEALTH_ENVELOPE_FIELD_TYPE_MISMATCH",
            descriptor,
        )
    if payload["api_version"] != "v1":
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.UNKNOWN_HEALTH_ENUM,
            "HEALTH_API_VERSION_NOT_SUPPORTED",
            descriptor,
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.REQUIRED_HEALTH_FIELD_MISSING,
            "HEALTH_DATA_OBJECT_MISSING",
            descriptor,
        )
    missing = tuple(field for field in _REQUIRED_CLASSIFIER_FIELDS if field not in data)
    if missing:
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.REQUIRED_HEALTH_FIELD_MISSING,
            "HEALTH_REQUIRED_FIELD_MISSING",
            descriptor,
        )
    if any(
        not isinstance(data[field], str)
        for field in ("status", "observed_at", "timing_state", "reason_code")
    ) or any(
        not isinstance(data[field], bool)
        for field in ("operational", "ready", "acceptance_blocking")
    ) or not isinstance(data["services"], list):
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.HEALTH_FIELD_TYPE_MISMATCH,
            "HEALTH_REQUIRED_FIELD_TYPE_MISMATCH",
            descriptor,
        )

    status = data["status"].strip().upper()
    timing = data["timing_state"].strip().upper()
    reason_code = data["reason_code"].strip().upper()
    if (
        status not in _STATUS_ENUM
        or timing not in _TIMING_ENUM
        or not _PUBLIC_ENUM.fullmatch(reason_code)
    ):
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.UNKNOWN_HEALTH_ENUM,
            "HEALTH_ENUM_NOT_SUPPORTED",
            descriptor,
        )

    signals = (
        status,
        data["operational"],
        data["ready"],
        data["acceptance_blocking"],
    )
    contracts = {
        "CURRENT": ("OK", True, True, False),
        "WITHIN_GRACE": ("OK", True, True, False),
        "DEADLINE_EXPIRED": ("DEGRADED", False, False, True),
        "DEGRADED": ({"STALE", "DEGRADED", "NOT_AVAILABLE", "ERROR", "OFFLINE"}, False, False, True),
        "UNKNOWN": ("UNKNOWN", False, False, True),
    }
    expected = contracts[timing]
    status_matches = (
        status in expected[0] if isinstance(expected[0], set) else status == expected[0]
    )
    if not status_matches or signals[1:] != expected[1:]:
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.CONTRADICTORY_HEALTH_SIGNALS,
            "HEALTH_SIGNALS_CONTRADICT",
            descriptor,
        )

    classification = RuntimeHealthClassification(timing)
    if classification is RuntimeHealthClassification.UNKNOWN:
        return _decision(
            classification,
            ClassificationReasonCode.GENUINELY_UNKNOWN_RUNTIME_STATE,
            "HEALTH_SCHEMA_VALID_UNKNOWN_STATE",
            descriptor,
        )
    reasons = {
        RuntimeHealthClassification.CURRENT: ClassificationReasonCode.CLASSIFIED_CURRENT,
        RuntimeHealthClassification.WITHIN_GRACE: ClassificationReasonCode.CLASSIFIED_WITHIN_GRACE,
        RuntimeHealthClassification.DEADLINE_EXPIRED: ClassificationReasonCode.CLASSIFIED_DEADLINE_EXPIRED,
        RuntimeHealthClassification.DEGRADED: ClassificationReasonCode.CLASSIFIED_DEGRADED,
    }
    branches = {
        RuntimeHealthClassification.CURRENT: "HEALTH_CURRENT_CONTRACT",
        RuntimeHealthClassification.WITHIN_GRACE: "HEALTH_WITHIN_GRACE_CONTRACT",
        RuntimeHealthClassification.DEADLINE_EXPIRED: "HEALTH_DEADLINE_EXPIRED_CONTRACT",
        RuntimeHealthClassification.DEGRADED: "HEALTH_DEGRADED_CONTRACT",
    }
    return _decision(classification, reasons[classification], branches[classification], descriptor)


def classify_health_body(body: bytes) -> HealthClassificationDecision:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        descriptor = _descriptor(
            None,
            json_parse_success=False,
            parser_branch_id="PARSER_JSON_DECODE_FAILED",
        )
        return _decision(
            RuntimeHealthClassification.UNKNOWN,
            ClassificationReasonCode.HEALTH_JSON_PARSE_FAILED,
            "HEALTH_JSON_NOT_PARSEABLE",
            descriptor,
        )
    return classify_health_payload(payload)
