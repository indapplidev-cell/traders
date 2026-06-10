"""JSON reporter для PredictionPayloadMappingPlan.

Модуль форматирует mapping plan будущего преобразования prediction payload
в GatePolicyInput. Он не импортирует prediction_service, predictor, БД
и traders-core.
"""

from __future__ import annotations

import json
from typing import Any

from app.gates.gate_policy_prediction_mapping_plan import (
    PredictionPayloadMappingPlan,
)


class GatePolicyPredictionMappingPlanReporter:
    """Сериализация prediction payload mapping plan."""

    def plan_to_dict(
        self,
        plan: PredictionPayloadMappingPlan | None = None,
    ) -> dict[str, Any]:
        """Преобразовать mapping plan в полный JSON-safe словарь."""

        selected_plan = plan or PredictionPayloadMappingPlan()
        payload = selected_plan.to_dict()

        return {
            "name": payload["name"],
            "version": payload["version"],
            "required_target_count": len(payload["required_target_fields"]),
            "optional_target_count": len(payload["optional_target_fields"]),
            "all_target_count": len(payload["all_target_fields"]),
            "all_source_count": len(payload["all_source_fields"]),
            "mapping_rule_count": len(payload["mapping_rules"]),
            "direction_rule_count": len(payload["direction_rules"]),
            "required_target_fields": payload["required_target_fields"],
            "optional_target_fields": payload["optional_target_fields"],
            "all_target_fields": payload["all_target_fields"],
            "all_source_fields": payload["all_source_fields"],
            "mapping_rules": payload["mapping_rules"],
            "direction_rules": payload["direction_rules"],
            "integration_status": payload["integration_status"],
        }

    def summary_to_dict(
        self,
        plan: PredictionPayloadMappingPlan | None = None,
    ) -> dict[str, Any]:
        """Преобразовать mapping plan в compact summary."""

        payload = self.plan_to_dict(plan)

        return {
            "name": payload["name"],
            "version": payload["version"],
            "required_target_count": payload["required_target_count"],
            "optional_target_count": payload["optional_target_count"],
            "all_target_count": payload["all_target_count"],
            "all_source_count": payload["all_source_count"],
            "mapping_rule_count": payload["mapping_rule_count"],
            "direction_rule_count": payload["direction_rule_count"],
            "required_target_fields": payload["required_target_fields"],
            "optional_target_fields": payload["optional_target_fields"],
            "all_source_fields": payload["all_source_fields"],
            "direction_outputs": [
                rule["output_direction"]
                for rule in payload["direction_rules"]
            ],
            "integration_status": payload["integration_status"],
        }

    def plan_to_json(
        self,
        plan: PredictionPayloadMappingPlan | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать полный mapping plan report в JSON."""

        return json.dumps(
            self.plan_to_dict(plan),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def summary_to_json(
        self,
        plan: PredictionPayloadMappingPlan | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать mapping plan summary в JSON."""

        return json.dumps(
            self.summary_to_dict(plan),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
