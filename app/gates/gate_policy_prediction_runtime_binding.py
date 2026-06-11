"""PredictionService to GatePolicy runtime binding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any

from app.gates.gate_policy_adapter import GatePolicyEvaluationAdapter
from app.gates.gate_policy_models import GatePolicyInput
from app.gates.gate_policy_prediction_runtime_adapter import (
    GatePolicyPredictionRuntimeAdapter,
)
from app.gates.gate_policy_reporter import GatePolicyReporter
from app.gates.gate_policy_service import GatePolicyService


BINDING_NAME = "gate_policy_prediction_runtime_binding"
BINDING_VERSION = "ml21.1"


@dataclass(frozen=True)
class GatePolicyPredictionRuntimeBindingIssue:
    """One binding issue."""

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
class GatePolicyPredictionRuntimeBindingResult:
    """Unified runtime binding result."""

    binding_name: str
    binding_version: str
    is_valid: bool
    direction: str
    prediction_payload: dict[str, Any]
    adapter_result: dict[str, Any] | None
    gate_policy_payload: dict[str, Any] | None
    gate_policy_input_snapshot: dict[str, Any]
    gate_policy_decision: dict[str, Any]
    issues: tuple[GatePolicyPredictionRuntimeBindingIssue, ...]
    integration_status: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_name": self.binding_name,
            "binding_version": self.binding_version,
            "is_valid": self.is_valid,
            "direction": self.direction,
            "prediction_payload": self.prediction_payload,
            "adapter_result": self.adapter_result,
            "gate_policy_payload": self.gate_policy_payload,
            "gate_policy_input_snapshot": self.gate_policy_input_snapshot,
            "gate_policy_decision": self.gate_policy_decision,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
            "integration_status": dict(self.integration_status),
        }


class PredictionServiceGatePolicyRuntimeBinding:
    """Bind prediction runtime payloads or PredictionService results to GatePolicy."""

    def __init__(
        self,
        *,
        prediction_service: Any | None = None,
        runtime_adapter: GatePolicyPredictionRuntimeAdapter | None = None,
        gate_policy_adapter: GatePolicyEvaluationAdapter | None = None,
        gate_policy_service: GatePolicyService | None = None,
        gate_policy_reporter: GatePolicyReporter | None = None,
    ) -> None:
        self._prediction_service = prediction_service
        self._runtime_adapter = runtime_adapter or GatePolicyPredictionRuntimeAdapter()
        self._gate_policy_adapter = gate_policy_adapter or GatePolicyEvaluationAdapter()
        self._gate_policy_service = gate_policy_service or GatePolicyService()
        self._gate_policy_reporter = gate_policy_reporter or GatePolicyReporter()

    def bind_prediction_payload_to_gate_policy(
        self,
        payload: dict[str, Any],
    ) -> GatePolicyPredictionRuntimeBindingResult:
        normalized_payload = self._normalize_object(payload)
        return self._bind(
            prediction_payload=normalized_payload,
            prediction_service_bound=False,
        )

    def bind_from_prediction_service_result(
        self,
        prediction_result: Any,
        *,
        request_payload: Mapping[str, Any] | None = None,
    ) -> GatePolicyPredictionRuntimeBindingResult:
        normalized_request_payload = self._normalize_object(request_payload or {})
        normalized_prediction_payload = self._normalize_prediction_payload(
            prediction_result,
            normalized_request_payload,
        )
        return self._bind(
            prediction_payload=normalized_prediction_payload,
            prediction_service_bound=True,
        )

    def bind_from_service_request(
        self,
        request_payload: Mapping[str, Any],
    ) -> GatePolicyPredictionRuntimeBindingResult:
        normalized_request_payload = self._normalize_object(request_payload)

        if self._prediction_service is None:
            return self._build_service_unavailable_result(normalized_request_payload)

        prediction_result = self._prediction_service.predict(normalized_request_payload)
        return self.bind_from_prediction_service_result(
            prediction_result,
            request_payload=normalized_request_payload,
        )

    def _bind(
        self,
        *,
        prediction_payload: dict[str, Any],
        prediction_service_bound: bool,
    ) -> GatePolicyPredictionRuntimeBindingResult:
        adapter_result = self._runtime_adapter.adapt_prediction_payload_for_gate_policy(
            prediction_payload
        )
        issues = [
            self._binding_issue_from_adapter_issue(issue)
            for issue in adapter_result.issues
        ]

        if adapter_result.is_valid and adapter_result.gate_policy_payload is not None:
            gate_policy_payload = self._json_safe(dict(adapter_result.gate_policy_payload))
            gate_policy_input = self._gate_policy_adapter.from_mapping(gate_policy_payload)
        else:
            gate_policy_payload = None
            issues.append(
                GatePolicyPredictionRuntimeBindingIssue(
                    field="gate_policy_payload",
                    code="gate_policy_payload_unavailable",
                    message=(
                        "GatePolicy payload was not created because runtime adapter "
                        "validation failed."
                    ),
                )
            )
            gate_policy_input = self._gate_policy_adapter.from_mapping(
                self._build_safe_reject_payload(prediction_payload)
            )

        gate_policy_decision = self._gate_policy_service.evaluate(gate_policy_input)

        return GatePolicyPredictionRuntimeBindingResult(
            binding_name=BINDING_NAME,
            binding_version=BINDING_VERSION,
            is_valid=adapter_result.is_valid,
            direction=adapter_result.direction,
            prediction_payload=self._json_safe(dict(prediction_payload)),
            adapter_result=self._json_safe(adapter_result.to_dict()),
            gate_policy_payload=gate_policy_payload,
            gate_policy_input_snapshot=self._gate_policy_input_to_dict(gate_policy_input),
            gate_policy_decision=self._gate_policy_reporter.result_to_dict(
                gate_policy_decision
            ),
            issues=tuple(issues),
            integration_status=self._integration_status(
                prediction_service_bound=prediction_service_bound
            ),
        )

    def _build_service_unavailable_result(
        self,
        request_payload: dict[str, Any],
    ) -> GatePolicyPredictionRuntimeBindingResult:
        gate_policy_input = self._gate_policy_adapter.from_mapping(
            self._build_safe_reject_payload(request_payload)
        )
        gate_policy_decision = self._gate_policy_service.evaluate(gate_policy_input)
        issues = (
            GatePolicyPredictionRuntimeBindingIssue(
                field="prediction_service",
                code="prediction_service_unavailable",
                message="PredictionService instance is required for service request mode.",
            ),
        )
        return GatePolicyPredictionRuntimeBindingResult(
            binding_name=BINDING_NAME,
            binding_version=BINDING_VERSION,
            is_valid=False,
            direction="NONE",
            prediction_payload=self._json_safe(dict(request_payload)),
            adapter_result=None,
            gate_policy_payload=None,
            gate_policy_input_snapshot=self._gate_policy_input_to_dict(gate_policy_input),
            gate_policy_decision=self._gate_policy_reporter.result_to_dict(
                gate_policy_decision
            ),
            issues=issues,
            integration_status=self._integration_status(
                prediction_service_bound=False
            ),
        )

    def _normalize_prediction_payload(
        self,
        prediction_result: Any,
        request_payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._normalize_object(prediction_result)
        context = self._normalize_object(payload.get("context", request_payload.get("context", {})))

        regime = (
            payload.get("regime")
            or payload.get("market_regime")
            or payload.get("detected_regime")
            or context.get("regime")
            or context.get("market_regime")
            or context.get("detected_regime")
        )
        if regime is not None:
            payload.setdefault("regime", regime)

        for field in ("symbol", "interval", "model_version", "horizon_candles"):
            if payload.get(field) is None and request_payload.get(field) is not None:
                payload[field] = request_payload[field]

        return payload

    def _build_safe_reject_payload(
        self,
        prediction_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "direction": "NONE",
            "confidence": 0.0,
            "tp_before_sl_probability": 0.0,
            "regime": (
                prediction_payload.get("regime")
                or prediction_payload.get("market_regime")
                or "unknown"
            ),
            "risk_score": None,
            "expected_move_atr": None,
            "model_version": prediction_payload.get("model_version"),
            "symbol": prediction_payload.get("symbol"),
            "interval": prediction_payload.get("interval"),
        }

    @staticmethod
    def _integration_status(*, prediction_service_bound: bool) -> dict[str, bool]:
        return {
            "prediction_service_bound": prediction_service_bound,
            "runtime_adapter_used": True,
            "gate_policy_service_used": True,
            "database_connected": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
        }

    def _binding_issue_from_adapter_issue(
        self,
        issue: Any,
    ) -> GatePolicyPredictionRuntimeBindingIssue:
        return GatePolicyPredictionRuntimeBindingIssue(
            field=str(issue.field),
            code=str(issue.code),
            message=str(issue.message),
            severity=str(issue.severity),
        )

    def _gate_policy_input_to_dict(
        self,
        gate_policy_input: GatePolicyInput,
    ) -> dict[str, Any]:
        return {
            "regime": gate_policy_input.regime,
            "direction": self._enum_or_string_value(gate_policy_input.direction),
            "confidence": gate_policy_input.confidence,
            "tp_before_sl_probability": gate_policy_input.tp_before_sl_probability,
            "risk_score": gate_policy_input.risk_score,
            "expected_move_atr": gate_policy_input.expected_move_atr,
            "model_total_r": gate_policy_input.model_total_r,
            "baseline_total_r": gate_policy_input.baseline_total_r,
            "model_profit_factor": gate_policy_input.model_profit_factor,
            "baseline_profit_factor": gate_policy_input.baseline_profit_factor,
            "sample_count": gate_policy_input.sample_count,
            "metadata": self._json_safe(dict(gate_policy_input.metadata)),
        }

    def _normalize_object(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}

        if isinstance(value, Mapping):
            return {
                str(key): self._json_safe(item)
                for key, item in value.items()
            }

        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._normalize_object(value.model_dump())

        if hasattr(value, "dict") and callable(value.dict):
            return self._normalize_object(value.dict())

        if is_dataclass(value) and not isinstance(value, type):
            return self._normalize_object(asdict(value))

        if hasattr(value, "__dict__"):
            return self._normalize_object(
                {
                    key: item
                    for key, item in vars(value).items()
                    if not key.startswith("_")
                }
            )

        return {"value": self._json_safe(value)}

    def _json_safe(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, Mapping):
            return {
                str(key): self._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]

        if is_dataclass(value) and not isinstance(value, type):
            return self._json_safe(asdict(value))

        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._json_safe(value.model_dump())

        if hasattr(value, "dict") and callable(value.dict):
            return self._json_safe(value.dict())

        return str(value)

    @staticmethod
    def _enum_or_string_value(value: Any) -> str:
        if isinstance(value, Enum):
            return str(value.value)

        return str(value)


def bind_prediction_payload_to_gate_policy(
    payload: dict[str, Any],
) -> GatePolicyPredictionRuntimeBindingResult:
    """Bind a raw prediction payload to GatePolicy."""

    return PredictionServiceGatePolicyRuntimeBinding().bind_prediction_payload_to_gate_policy(
        payload
    )


def bind_prediction_service_result_to_gate_policy(
    prediction_result: Any,
    *,
    request_payload: Mapping[str, Any] | None = None,
) -> GatePolicyPredictionRuntimeBindingResult:
    """Bind a PredictionService result to GatePolicy."""

    return PredictionServiceGatePolicyRuntimeBinding().bind_from_prediction_service_result(
        prediction_result,
        request_payload=request_payload,
    )
