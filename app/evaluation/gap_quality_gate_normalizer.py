from __future__ import annotations

from typing import Any


SAFE_GAP_SEVERITIES = {"OK", "SAFE", "MINOR"}
UNSAFE_GAP_SEVERITIES = {"HIGH", "CRITICAL"}


def normalize_gap_severity(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if not normalized:
        return None
    aliases = {
        "SAFE": "OK",
    }
    return aliases.get(normalized, normalized)


def gap_quality_gate_is_safe(
    *,
    gap_severity_for_training: Any,
    gap_training_safe: bool | None,
) -> bool:
    severity = normalize_gap_severity(gap_severity_for_training)
    return bool(gap_training_safe is True and severity in SAFE_GAP_SEVERITIES)


def gap_quality_gate_should_fail(
    *,
    gap_severity_for_training: Any,
    gap_training_safe: bool | None,
) -> bool:
    severity = normalize_gap_severity(gap_severity_for_training)
    return bool(gap_training_safe is False or severity in UNSAFE_GAP_SEVERITIES)


def normalize_gap_quality_gate(
    *,
    gap_severity_for_training: Any,
    gap_training_safe: bool | None,
    failed_gates: list[str] | tuple[str, ...] | None,
    passed_gates: list[str] | tuple[str, ...] | None,
) -> tuple[list[str], list[str]]:
    failed = _dedupe_strings(failed_gates)
    passed = _dedupe_strings(passed_gates)
    gate_name = "gap_quality_gate"

    if gap_quality_gate_is_safe(
        gap_severity_for_training=gap_severity_for_training,
        gap_training_safe=gap_training_safe,
    ):
        failed = [item for item in failed if item != gate_name]
        if gate_name not in passed:
            passed.append(gate_name)
    elif gap_quality_gate_should_fail(
        gap_severity_for_training=gap_severity_for_training,
        gap_training_safe=gap_training_safe,
    ):
        passed = [item for item in passed if item != gate_name]
        if gate_name not in failed:
            failed.append(gate_name)

    failed_set = set(failed)
    passed = [item for item in passed if item not in failed_set]
    return failed, passed


def _dedupe_strings(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if values is None:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        item = str(value)
        if item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized
