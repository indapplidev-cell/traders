"""Runtime adapter between prediction payloads and GatePolicy-compatible payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.gates.gate_policy_prediction_runtime_adapter_contract import (
    RuntimeAdapterValidationIssue,
    validate_runtime_prediction_payload_contract,
)


ADAPTER_NAME = "gate_policy_prediction_runtime_adapter"
ADAPTER_VERSION = "ml21.1"


@dataclass(frozen=True)
class GatePolicyPredictionRuntimeAdapterIssue:
    """One runtime adapter issue."""

    field: str
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class GatePolicyPredictionRuntimeAdapterResult:
    """JSON-safe runtime adapter result."""

    adapter_name: str
    adapter_version: str
    is_valid: bool
    direction: str
    normalized_prediction_payload: dict[str, Any]
    gate_policy_payload: dict[str, Any] | None
    metadata: dict[str, Any]
    issues: tuple[GatePolicyPredictionRuntimeAdapterIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "is_valid": self.is_valid,
            "direction": self.direction,
            "normalized_prediction_payload": dict(self.normalized_prediction_payload),
            "gate_policy_payload": (
                dict(self.gate_policy_payload)
                if self.gate_policy_payload is not None
                else None
            ),
            "metadata": dict(self.metadata),
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
        }


class GatePolicyPredictionRuntimeAdapter:
    """Adapt runtime prediction payloads for GatePolicy."""

    def adapt_prediction_payload_for_gate_policy(
        self,
        payload: dict[str, Any],
    ) -> GatePolicyPredictionRuntimeAdapterResult:
        contract_result = validate_runtime_prediction_payload_contract(payload)
        issues = [
            self._issue_from_contract_issue(item)
            for item in contract_result.issues
        ]

        if not contract_result.is_valid:
            return GatePolicyPredictionRuntimeAdapterResult(
                adapter_name=ADAPTER_NAME,
                adapter_version=ADAPTER_VERSION,
                is_valid=False,
                direction="NONE",
                normalized_prediction_payload=dict(contract_result.normalized_payload),
                gate_policy_payload=None,
                metadata=dict(contract_result.metadata),
                issues=tuple(issues),
            )

        direction, direction_issue = self._resolve_direction(contract_result.normalized_payload)
        if direction_issue is not None:
            issues.append(direction_issue)

        gate_policy_payload = {
            "direction": direction,
            "confidence": contract_result.normalized_payload["confidence"],
            "tp_before_sl_probability": contract_result.normalized_payload[
                "tp_before_sl_probability"
            ],
            "regime": contract_result.normalized_payload["regime"],
            "risk_score": contract_result.normalized_payload["risk_score"],
            "expected_move_atr": contract_result.normalized_payload["expected_move_atr"],
            "model_version": contract_result.normalized_payload.get("model_version"),
            "symbol": contract_result.normalized_payload.get("symbol"),
            "interval": contract_result.normalized_payload.get("interval"),
        }

        return GatePolicyPredictionRuntimeAdapterResult(
            adapter_name=ADAPTER_NAME,
            adapter_version=ADAPTER_VERSION,
            is_valid=True,
            direction=direction,
            normalized_prediction_payload=dict(contract_result.normalized_payload),
            gate_policy_payload=gate_policy_payload,
            metadata=dict(contract_result.metadata),
            issues=tuple(issues),
        )

    def _resolve_direction(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, GatePolicyPredictionRuntimeAdapterIssue | None]:
        probabilities = {
            "LONG": float(payload["prob_up"]),
            "SHORT": float(payload["prob_down"]),
            "FLAT": float(payload["prob_flat"]),
        }
        max_probability = max(probabilities.values())
        winners = [
            direction
            for direction, probability in probabilities.items()
            if probability == max_probability
        ]

        if len(winners) != 1:
            return (
                "NONE",
                GatePolicyPredictionRuntimeAdapterIssue(
                    field="direction",
                    code="tied_probabilities",
                    message="Direction is NONE because prediction probabilities are tied.",
                    severity="warning",
                ),
            )

        return winners[0], None

    @staticmethod
    def _issue_from_contract_issue(
        issue: RuntimeAdapterValidationIssue,
    ) -> GatePolicyPredictionRuntimeAdapterIssue:
        return GatePolicyPredictionRuntimeAdapterIssue(
            field=issue.field,
            code=issue.code,
            message=issue.message,
            severity=issue.severity,
        )


def adapt_prediction_payload_for_gate_policy(
    payload: dict[str, Any],
) -> GatePolicyPredictionRuntimeAdapterResult:
    """Adapt a prediction payload for GatePolicy."""

    return GatePolicyPredictionRuntimeAdapter().adapt_prediction_payload_for_gate_policy(
        payload
    )
