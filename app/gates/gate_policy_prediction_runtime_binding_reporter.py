"""Reporter for PredictionService to GatePolicy runtime binding."""

from __future__ import annotations

import json
from typing import Any

from app.gates.gate_policy_prediction_runtime_binding import (
    BINDING_NAME,
    BINDING_VERSION,
    GatePolicyPredictionRuntimeBindingResult,
)


class GatePolicyPredictionRuntimeBindingReporter:
    """Serialize runtime binding summaries and results."""

    def summary_to_dict(self) -> dict[str, Any]:
        return {
            "binding_name": BINDING_NAME,
            "binding_version": BINDING_VERSION,
            "uses_prediction_service": True,
            "uses_runtime_adapter": True,
            "uses_gate_policy_service": True,
            "supports_payload_mode": True,
            "supports_service_result_mode": True,
            "database_connected": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
        }

    def full_report_to_dict(
        self,
        result: GatePolicyPredictionRuntimeBindingResult | None = None,
    ) -> dict[str, Any]:
        payload = {
            "summary": self.summary_to_dict(),
        }
        if result is not None:
            payload["result"] = self.result_to_dict(result)
        return payload

    def result_to_dict(
        self,
        result: GatePolicyPredictionRuntimeBindingResult,
    ) -> dict[str, Any]:
        return result.to_dict()

    def summary_to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.summary_to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def full_report_to_json(
        self,
        result: GatePolicyPredictionRuntimeBindingResult | None = None,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.full_report_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def result_to_json(
        self,
        result: GatePolicyPredictionRuntimeBindingResult,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )


def build_gate_policy_prediction_runtime_binding_summary() -> dict[str, Any]:
    """Build runtime binding summary."""

    return GatePolicyPredictionRuntimeBindingReporter().summary_to_dict()
