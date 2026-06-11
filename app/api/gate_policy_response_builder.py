from __future__ import annotations

from typing import Any

from app.gates.gate_policy_prediction_runtime_binding import (
    bind_prediction_service_result_to_gate_policy,
)


GATE_POLICY_API_SOURCE = "ml21_runtime_binding"


def build_gate_policy_api_block_from_prediction_payload(
    prediction_payload: dict[str, Any],
    *,
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build API gate_policy block from a prediction payload using ML21 binding."""

    try:
        binding_result = bind_prediction_service_result_to_gate_policy(
            prediction_payload,
            request_payload=request_payload,
        )
        binding_payload = binding_result.to_dict()
        return {
            "enabled": True,
            "source": GATE_POLICY_API_SOURCE,
            "is_valid": binding_payload["is_valid"],
            "direction": binding_payload["direction"],
            "gate_policy_payload": binding_payload["gate_policy_payload"],
            "gate_policy_decision": binding_payload["gate_policy_decision"],
            "issues": binding_payload["issues"],
            "issue_count": binding_payload["issue_count"],
            "integration_status": binding_payload["integration_status"],
        }
    except Exception as exc:
        return build_safe_gate_policy_api_block_from_error(exc)


def build_safe_gate_policy_api_block_from_error(error: Exception) -> dict[str, Any]:
    """Build a safe gate_policy block when binding fails unexpectedly."""

    issue = {
        "field": "gate_policy",
        "code": "gate_policy_binding_error",
        "message": str(error) or error.__class__.__name__,
        "severity": "error",
    }
    return {
        "enabled": True,
        "source": GATE_POLICY_API_SOURCE,
        "is_valid": False,
        "direction": "NONE",
        "gate_policy_payload": None,
        "gate_policy_decision": None,
        "issues": [issue],
        "issue_count": 1,
        "integration_status": {
            "prediction_service_bound": True,
            "runtime_adapter_used": True,
            "gate_policy_service_used": False,
            "database_connected": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
        },
    }
