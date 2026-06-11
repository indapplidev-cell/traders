"""JSON reporter для prediction runtime adapter contract.

Модуль форматирует контракт будущего runtime adapter, но не подключает
реальный prediction_service, predictor, БД, traders-core или live execution.
"""

from __future__ import annotations

import json
from typing import Any

from app.gates.gate_policy_prediction_runtime_adapter_contract import (
    CONTRACT_NAME,
    CONTRACT_VERSION,
    build_runtime_adapter_contract_summary,
    validate_runtime_prediction_payload_contract,
)


class GatePolicyPredictionRuntimeAdapterContractReporter:
    """Сериализация prediction runtime adapter contract."""

    def contract_to_dict(self) -> dict[str, Any]:
        """Преобразовать runtime adapter contract в полный JSON-safe report."""

        summary = build_runtime_adapter_contract_summary()

        return {
            "contract_name": summary["contract_name"],
            "contract_version": summary["contract_version"],
            "required_probability_count": summary["required_probability_count"],
            "required_numeric_count": summary["required_numeric_count"],
            "required_context_count": summary["required_context_count"],
            "optional_numeric_count": summary["optional_numeric_count"],
            "traceability_count": summary["traceability_count"],
            "future_gate_policy_target_count": summary[
                "future_gate_policy_target_count"
            ],
            "required_probability_fields": summary["required_probability_fields"],
            "required_numeric_fields": summary["required_numeric_fields"],
            "required_context_fields": summary["required_context_fields"],
            "optional_numeric_fields": summary["optional_numeric_fields"],
            "traceability_fields": summary["traceability_fields"],
            "future_gate_policy_target_fields": summary[
                "future_gate_policy_target_fields"
            ],
            "validation_policy": {
                "missing_required_numeric_field": "error",
                "invalid_numeric_field": "error",
                "negative_probability": "error",
                "missing_required_context_field": "error",
                "invalid_optional_numeric_field": "normalize_to_none",
            },
            "integration_status": summary["integration_status"],
        }

    def summary_to_dict(self) -> dict[str, Any]:
        """Преобразовать runtime adapter contract в compact summary."""

        payload = self.contract_to_dict()

        return {
            "contract_name": payload["contract_name"],
            "contract_version": payload["contract_version"],
            "required_probability_count": payload["required_probability_count"],
            "required_numeric_count": payload["required_numeric_count"],
            "required_context_count": payload["required_context_count"],
            "optional_numeric_count": payload["optional_numeric_count"],
            "traceability_count": payload["traceability_count"],
            "future_gate_policy_target_count": payload[
                "future_gate_policy_target_count"
            ],
            "required_numeric_fields": payload["required_numeric_fields"],
            "required_context_fields": payload["required_context_fields"],
            "optional_numeric_fields": payload["optional_numeric_fields"],
            "traceability_fields": payload["traceability_fields"],
            "future_gate_policy_target_fields": payload[
                "future_gate_policy_target_fields"
            ],
            "runtime_adapter_implemented": payload["integration_status"][
                "runtime_adapter_implemented"
            ],
            "integration_status": payload["integration_status"],
        }

    def validation_to_dict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Преобразовать validation result для raw prediction payload в report."""

        result = validate_runtime_prediction_payload_contract(payload)
        result_payload = result.to_dict()

        return {
            "contract_name": result_payload["contract_name"],
            "contract_version": result_payload["contract_version"],
            "is_valid": result_payload["is_valid"],
            "issue_count": result_payload["issue_count"],
            "issues": result_payload["issues"],
            "normalized_payload": result_payload["normalized_payload"],
            "metadata": result_payload["metadata"],
            "runtime_adapter_implemented": result_payload[
                "runtime_adapter_implemented"
            ],
        }

    def contract_to_json(self, *, indent: int | None = 2) -> str:
        """Преобразовать full contract report в JSON."""

        return json.dumps(
            self.contract_to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def summary_to_json(self, *, indent: int | None = 2) -> str:
        """Преобразовать compact contract summary в JSON."""

        return json.dumps(
            self.summary_to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def validation_to_json(
        self,
        payload: dict[str, Any],
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать validation report в JSON."""

        return json.dumps(
            self.validation_to_dict(payload),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )


def build_runtime_adapter_contract_report() -> dict[str, Any]:
    """Собрать полный report контракта будущего runtime adapter."""

    return GatePolicyPredictionRuntimeAdapterContractReporter().contract_to_dict()


def build_runtime_adapter_contract_report_summary() -> dict[str, Any]:
    """Собрать compact summary report контракта будущего runtime adapter."""

    return GatePolicyPredictionRuntimeAdapterContractReporter().summary_to_dict()


assert CONTRACT_NAME == "gate_policy_prediction_runtime_adapter_contract"
assert CONTRACT_VERSION == "ml20.1"
