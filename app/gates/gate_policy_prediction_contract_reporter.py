"""JSON-репортёр для GatePolicy prediction payload contract.

Модуль форматирует контракт будущего prediction/evaluation payload.
Он не запускает модель, не читает БД и не подключается к traders-core.
"""

from __future__ import annotations

import json
from typing import Any

from app.gates.gate_policy_prediction_contract import (
    GatePolicyPredictionPayloadContract,
)


class GatePolicyPredictionContractReporter:
    """Сериализация GatePolicy prediction payload contract."""

    def contract_to_dict(
        self,
        contract: GatePolicyPredictionPayloadContract | None = None,
    ) -> dict[str, Any]:
        """Преобразовать контракт в расширенный JSON-safe словарь."""

        selected_contract = contract or GatePolicyPredictionPayloadContract()
        base_payload = selected_contract.to_dict()

        field_aliases = base_payload["field_aliases"]
        required_fields = base_payload["required_fields"]
        optional_fields = base_payload["optional_fields"]
        direction_aliases = base_payload["direction_aliases"]
        known_regime_values = base_payload["known_regime_values"]

        return {
            "contract_name": "gate_policy_prediction_payload",
            "version": "ml16.1",
            "required_count": len(required_fields),
            "optional_count": len(optional_fields),
            "all_field_count": len(required_fields) + len(optional_fields),
            "alias_field_count": len(field_aliases),
            "direction_alias_count": len(direction_aliases),
            "known_regime_count": len(known_regime_values),
            "required_fields": required_fields,
            "optional_fields": optional_fields,
            "field_aliases": field_aliases,
            "direction_aliases": direction_aliases,
            "known_regime_values": known_regime_values,
            "integration_status": {
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }

    def contract_summary_to_dict(
        self,
        contract: GatePolicyPredictionPayloadContract | None = None,
    ) -> dict[str, Any]:
        """Преобразовать контракт в короткую сводку."""

        payload = self.contract_to_dict(contract)

        return {
            "contract_name": payload["contract_name"],
            "version": payload["version"],
            "required_count": payload["required_count"],
            "optional_count": payload["optional_count"],
            "all_field_count": payload["all_field_count"],
            "alias_field_count": payload["alias_field_count"],
            "direction_alias_count": payload["direction_alias_count"],
            "known_regime_count": payload["known_regime_count"],
            "integration_status": payload["integration_status"],
        }

    def contract_to_json(
        self,
        contract: GatePolicyPredictionPayloadContract | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать контракт в JSON-строку."""

        return json.dumps(
            self.contract_to_dict(contract),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def contract_summary_to_json(
        self,
        contract: GatePolicyPredictionPayloadContract | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать короткую сводку контракта в JSON-строку."""

        return json.dumps(
            self.contract_summary_to_dict(contract),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
