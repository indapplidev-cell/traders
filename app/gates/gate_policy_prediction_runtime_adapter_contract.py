"""Контракт будущего runtime adapter между prediction payload и GatePolicy.

Модуль валидирует форму runtime prediction payload, но не подключает
реальный prediction_service, predictor, БД, traders-core или live execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CONTRACT_NAME = "gate_policy_prediction_runtime_adapter_contract"
CONTRACT_VERSION = "ml20.1"

REQUIRED_PROBABILITY_FIELDS: tuple[str, ...] = (
    "prob_up",
    "prob_down",
    "prob_flat",
)

REQUIRED_NUMERIC_FIELDS: tuple[str, ...] = (
    "prob_up",
    "prob_down",
    "prob_flat",
    "confidence",
    "tp_before_sl_probability",
)

REQUIRED_CONTEXT_FIELDS: tuple[str, ...] = (
    "regime",
)

OPTIONAL_NUMERIC_FIELDS: tuple[str, ...] = (
    "risk_score",
    "expected_move_atr",
)

TRACEABILITY_FIELDS: tuple[str, ...] = (
    "model_version",
    "symbol",
    "interval",
)

FUTURE_GATE_POLICY_TARGET_FIELDS: tuple[str, ...] = (
    "direction",
    "confidence",
    "tp_before_sl_probability",
    "regime",
    "risk_score",
    "expected_move_atr",
    "model_version",
    "symbol",
    "interval",
)


@dataclass(frozen=True)
class RuntimeAdapterValidationIssue:
    """Одна проблема валидации runtime prediction payload."""

    field: str
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        """Преобразовать issue в JSON-safe словарь."""

        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class RuntimePredictionAdapterContractResult:
    """Результат contract validation для будущего runtime adapter."""

    contract_name: str
    contract_version: str
    is_valid: bool
    required_probability_fields: tuple[str, ...]
    required_numeric_fields: tuple[str, ...]
    required_context_fields: tuple[str, ...]
    optional_numeric_fields: tuple[str, ...]
    traceability_fields: tuple[str, ...]
    future_gate_policy_target_fields: tuple[str, ...]
    normalized_payload: dict[str, Any]
    metadata: dict[str, Any]
    issues: tuple[RuntimeAdapterValidationIssue, ...]
    runtime_adapter_implemented: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать contract result в JSON-safe словарь."""

        return {
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "is_valid": self.is_valid,
            "required_probability_fields": list(self.required_probability_fields),
            "required_numeric_fields": list(self.required_numeric_fields),
            "required_context_fields": list(self.required_context_fields),
            "optional_numeric_fields": list(self.optional_numeric_fields),
            "traceability_fields": list(self.traceability_fields),
            "future_gate_policy_target_fields": list(
                self.future_gate_policy_target_fields
            ),
            "normalized_payload": dict(self.normalized_payload),
            "metadata": dict(self.metadata),
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
            "issue_count": len(self.issues),
            "runtime_adapter_implemented": self.runtime_adapter_implemented,
        }


def _is_number(value: Any) -> bool:
    """Проверить, является ли значение числом, но не bool."""

    return isinstance(value, int | float) and not isinstance(value, bool)


def _normalize_optional_number(value: Any) -> float | None:
    """Нормализовать optional numeric value."""

    if value is None:
        return None

    if _is_number(value):
        return float(value)

    return None


def validate_runtime_prediction_payload_contract(
    payload: dict[str, Any],
) -> RuntimePredictionAdapterContractResult:
    """Проверить runtime prediction payload без реального adapter/inference."""

    issues: list[RuntimeAdapterValidationIssue] = []
    normalized_payload: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

    for field in REQUIRED_NUMERIC_FIELDS:
        if field not in payload:
            issues.append(
                RuntimeAdapterValidationIssue(
                    field=field,
                    code="missing_required_numeric_field",
                    message=f"Required numeric field is missing: {field}",
                )
            )
            continue

        value = payload[field]

        if not _is_number(value):
            issues.append(
                RuntimeAdapterValidationIssue(
                    field=field,
                    code="invalid_numeric_field",
                    message=f"Required numeric field is not numeric: {field}",
                )
            )
            continue

        if field in REQUIRED_PROBABILITY_FIELDS and float(value) < 0.0:
            issues.append(
                RuntimeAdapterValidationIssue(
                    field=field,
                    code="negative_probability",
                    message=f"Probability field cannot be negative: {field}",
                )
            )
            continue

        normalized_payload[field] = float(value)

    for field in REQUIRED_CONTEXT_FIELDS:
        value = payload.get(field)

        if value is None or str(value).strip() == "":
            issues.append(
                RuntimeAdapterValidationIssue(
                    field=field,
                    code="missing_required_context_field",
                    message=f"Required context field is missing: {field}",
                )
            )
            continue

        normalized_payload[field] = str(value)

    for field in OPTIONAL_NUMERIC_FIELDS:
        normalized_payload[field] = _normalize_optional_number(payload.get(field))

    for field in TRACEABILITY_FIELDS:
        metadata[field] = payload.get(field)
        normalized_payload[field] = payload.get(field)

    return RuntimePredictionAdapterContractResult(
        contract_name=CONTRACT_NAME,
        contract_version=CONTRACT_VERSION,
        is_valid=len(issues) == 0,
        required_probability_fields=REQUIRED_PROBABILITY_FIELDS,
        required_numeric_fields=REQUIRED_NUMERIC_FIELDS,
        required_context_fields=REQUIRED_CONTEXT_FIELDS,
        optional_numeric_fields=OPTIONAL_NUMERIC_FIELDS,
        traceability_fields=TRACEABILITY_FIELDS,
        future_gate_policy_target_fields=FUTURE_GATE_POLICY_TARGET_FIELDS,
        normalized_payload=normalized_payload,
        metadata=metadata,
        issues=tuple(issues),
        runtime_adapter_implemented=False,
    )


def build_runtime_adapter_contract_summary() -> dict[str, Any]:
    """Собрать compact summary контракта будущего runtime adapter."""

    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "required_probability_fields": list(REQUIRED_PROBABILITY_FIELDS),
        "required_numeric_fields": list(REQUIRED_NUMERIC_FIELDS),
        "required_context_fields": list(REQUIRED_CONTEXT_FIELDS),
        "optional_numeric_fields": list(OPTIONAL_NUMERIC_FIELDS),
        "traceability_fields": list(TRACEABILITY_FIELDS),
        "future_gate_policy_target_fields": list(FUTURE_GATE_POLICY_TARGET_FIELDS),
        "required_probability_count": len(REQUIRED_PROBABILITY_FIELDS),
        "required_numeric_count": len(REQUIRED_NUMERIC_FIELDS),
        "required_context_count": len(REQUIRED_CONTEXT_FIELDS),
        "optional_numeric_count": len(OPTIONAL_NUMERIC_FIELDS),
        "traceability_count": len(TRACEABILITY_FIELDS),
        "future_gate_policy_target_count": len(FUTURE_GATE_POLICY_TARGET_FIELDS),
        "integration_status": {
            "prediction_service_imported": False,
            "predictor_imported": False,
            "database_connected": False,
            "model_inference_connected": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "runtime_adapter_implemented": False,
        },
    }
