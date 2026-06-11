from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.api.gate_policy_response_builder import (
    build_gate_policy_api_block_from_prediction_payload,
)


EVALUATOR_NAME = "gate_policy_replay_evaluator"
EVALUATOR_VERSION = "ml23.1"


@dataclass(frozen=True)
class GatePolicyReplayEvaluationRecord:
    index: int
    is_valid: bool
    direction: str
    gate_policy_payload: dict[str, Any] | None
    gate_policy_decision: dict[str, Any] | None
    issues: tuple[dict[str, Any], ...]
    issue_count: int
    integration_status: dict[str, bool]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "is_valid": self.is_valid,
            "direction": self.direction,
            "gate_policy_payload": self.gate_policy_payload,
            "gate_policy_decision": self.gate_policy_decision,
            "issues": [dict(item) for item in self.issues],
            "issue_count": self.issue_count,
            "integration_status": dict(self.integration_status),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class GatePolicyReplayEvaluationSummary:
    evaluator_name: str
    evaluator_version: str
    total_records: int
    valid_records: int
    invalid_records: int
    valid_ratio: float
    invalid_ratio: float
    direction_counts: dict[str, int]
    gate_policy_allowed_count: int
    gate_policy_blocked_count: int
    gate_policy_none_count: int
    issue_counts: dict[str, int]
    top_issue_codes: list[str]
    sample_size: int
    integration_status: dict[str, bool]
    records: tuple[GatePolicyReplayEvaluationRecord, ...]

    def to_dict(self, *, include_records: bool = True) -> dict[str, Any]:
        payload = {
            "evaluator_name": self.evaluator_name,
            "evaluator_version": self.evaluator_version,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "valid_ratio": self.valid_ratio,
            "invalid_ratio": self.invalid_ratio,
            "direction_counts": dict(self.direction_counts),
            "gate_policy_allowed_count": self.gate_policy_allowed_count,
            "gate_policy_blocked_count": self.gate_policy_blocked_count,
            "gate_policy_none_count": self.gate_policy_none_count,
            "issue_counts": dict(self.issue_counts),
            "top_issue_codes": list(self.top_issue_codes),
            "sample_size": self.sample_size,
            "integration_status": dict(self.integration_status),
        }
        if include_records:
            payload["records"] = [record.to_dict() for record in self.records]
        return payload


class GatePolicyReplayEvaluator:
    """Evaluate replay prediction payloads through GatePolicy."""

    def evaluate(
        self,
        prediction_payloads: list[dict[str, Any]],
    ) -> GatePolicyReplayEvaluationSummary:
        records: list[GatePolicyReplayEvaluationRecord] = []
        direction_counts = {
            "LONG": 0,
            "SHORT": 0,
            "FLAT": 0,
            "NONE": 0,
        }
        issue_counts: Counter[str] = Counter()
        gate_policy_allowed_count = 0
        gate_policy_blocked_count = 0
        gate_policy_none_count = 0

        for index, payload in enumerate(prediction_payloads):
            gate_policy_block = build_gate_policy_api_block_from_prediction_payload(payload)
            record = self._build_record(index=index, payload=payload, gate_policy_block=gate_policy_block)
            records.append(record)

            direction = record.direction if record.direction in direction_counts else "NONE"
            direction_counts[direction] += 1

            if direction == "NONE":
                gate_policy_none_count += 1

            if self._is_allowed(record.gate_policy_decision):
                gate_policy_allowed_count += 1
            else:
                gate_policy_blocked_count += 1

            for issue in record.issues:
                code = str(issue.get("code", "unknown_issue"))
                issue_counts[code] += 1

        total_records = len(records)
        valid_records = sum(int(record.is_valid) for record in records)
        invalid_records = total_records - valid_records

        return GatePolicyReplayEvaluationSummary(
            evaluator_name=EVALUATOR_NAME,
            evaluator_version=EVALUATOR_VERSION,
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            valid_ratio=(valid_records / total_records) if total_records else 0.0,
            invalid_ratio=(invalid_records / total_records) if total_records else 0.0,
            direction_counts=direction_counts,
            gate_policy_allowed_count=gate_policy_allowed_count,
            gate_policy_blocked_count=gate_policy_blocked_count,
            gate_policy_none_count=gate_policy_none_count,
            issue_counts=dict(issue_counts),
            top_issue_codes=[
                item[0]
                for item in sorted(
                    issue_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            sample_size=total_records,
            integration_status={
                "runtime_binding_used": True,
                "gate_policy_used": True,
                "prediction_service_required": False,
                "database_connected": False,
                "database_writes": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
                "orders_enabled": False,
            },
            records=tuple(records),
        )

    def _build_record(
        self,
        *,
        index: int,
        payload: dict[str, Any],
        gate_policy_block: dict[str, Any],
    ) -> GatePolicyReplayEvaluationRecord:
        metadata = {
            field: payload[field]
            for field in ("timestamp", "symbol", "interval", "model_version")
            if payload.get(field) is not None
        }
        return GatePolicyReplayEvaluationRecord(
            index=index,
            is_valid=bool(gate_policy_block["is_valid"]),
            direction=str(gate_policy_block["direction"]),
            gate_policy_payload=gate_policy_block.get("gate_policy_payload"),
            gate_policy_decision=gate_policy_block.get("gate_policy_decision"),
            issues=tuple(dict(item) for item in gate_policy_block.get("issues", [])),
            issue_count=int(gate_policy_block.get("issue_count", 0)),
            integration_status=dict(gate_policy_block.get("integration_status", {})),
            metadata=metadata,
        )

    @staticmethod
    def _is_allowed(gate_policy_decision: dict[str, Any] | None) -> bool:
        if not gate_policy_decision:
            return False

        allowed = gate_policy_decision.get("allowed")
        if isinstance(allowed, bool):
            return allowed

        for key in ("allow", "approved", "usable"):
            value = gate_policy_decision.get(key)
            if isinstance(value, bool):
                return value

        decision_value = str(gate_policy_decision.get("decision", "")).upper()
        return decision_value.startswith("ALLOW")


def evaluate_gate_policy_replay(
    prediction_payloads: list[dict[str, Any]],
) -> GatePolicyReplayEvaluationSummary:
    """Evaluate a replay payload sequence through GatePolicy."""

    return GatePolicyReplayEvaluator().evaluate(prediction_payloads)
