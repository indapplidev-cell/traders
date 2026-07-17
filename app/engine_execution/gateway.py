"""Local-only gateways. No implementation in this module communicates with an exchange."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from app.engine_execution.enums import (
    ExecutionAcknowledgementStatus as AckStatus, ExecutionIntentStatus,
    ExecutionMode, ExecutionReasonCode as R,
)
from app.engine_execution.models import ExecutionAcknowledgement, ExecutionIntent
from app.engine_execution.validator import validate_intent_contract


class ExecutionGateway(ABC):
    @abstractmethod
    def validate_intent(self, intent: ExecutionIntent) -> tuple[str, ...]: ...

    @abstractmethod
    def submit(self, intent: ExecutionIntent) -> ExecutionAcknowledgement: ...

    @abstractmethod
    def cancel(self, execution_intent_id: str) -> ExecutionAcknowledgement: ...

    @abstractmethod
    def get_status(self, execution_intent_id: str) -> ExecutionAcknowledgement | None: ...


class _LocalGateway(ExecutionGateway):
    mode: ExecutionMode

    def __init__(self) -> None:
        self._acknowledgements: dict[str, ExecutionAcknowledgement] = {}

    def validate_intent(self, intent: ExecutionIntent) -> tuple[str, ...]:
        reasons = list(validate_intent_contract(intent))
        if intent.execution_mode is not self.mode:
            reasons.append(R.CONTRACT_MISMATCH.value)
        if intent.status is ExecutionIntentStatus.DUPLICATE:
            reasons.append(R.DUPLICATE_EXECUTION_INTENT.value)
        elif intent.status is not ExecutionIntentStatus.READY:
            reasons.extend(intent.reason_codes or (R.CONTRACT_MISMATCH.value,))
        return tuple(dict.fromkeys(reasons))

    def _ack(self, intent: ExecutionIntent, *, metadata: Mapping[str, Any] | None = None) -> ExecutionAcknowledgement:
        if intent.status is ExecutionIntentStatus.DUPLICATE:
            return ExecutionAcknowledgement(
                intent.execution_intent_id, intent.idempotency_key, self.mode,
                AckStatus.DUPLICATE, None, reason_codes=(R.DUPLICATE_EXECUTION_INTENT.value,),
            )
        existing = self._acknowledgements.get(intent.idempotency_key)
        if existing is not None:
            return ExecutionAcknowledgement(
                intent.execution_intent_id, intent.idempotency_key, self.mode,
                AckStatus.DUPLICATE, None, reason_codes=(R.DUPLICATE_EXECUTION_INTENT.value,),
            )
        reasons = self.validate_intent(intent)
        status = AckStatus.ACKNOWLEDGED if not reasons else AckStatus.REJECTED
        acknowledgement = ExecutionAcknowledgement(
            intent.execution_intent_id, intent.idempotency_key, self.mode, status,
            datetime.now(timezone.utc) if status is AckStatus.ACKNOWLEDGED else None,
            external_order_id=None,
            reason_codes=(R.EXECUTION_INTENT_READY.value,) if not reasons else reasons,
            warnings=intent.warnings, metadata=metadata or {},
        )
        if status is AckStatus.ACKNOWLEDGED:
            self._acknowledgements[intent.idempotency_key] = acknowledgement
        return acknowledgement

    def cancel(self, execution_intent_id: str) -> ExecutionAcknowledgement:
        for acknowledgement in self._acknowledgements.values():
            if acknowledgement.execution_intent_id == execution_intent_id:
                return acknowledgement
        return ExecutionAcknowledgement(
            execution_intent_id, "", self.mode, AckStatus.REJECTED, None,
            reason_codes=(R.CONTRACT_MISMATCH.value,),
        )

    def get_status(self, execution_intent_id: str) -> ExecutionAcknowledgement | None:
        return next((item for item in self._acknowledgements.values()
                     if item.execution_intent_id == execution_intent_id), None)


class DryRunExecutionGateway(_LocalGateway):
    mode = ExecutionMode.DRY_RUN

    def submit(self, intent: ExecutionIntent) -> ExecutionAcknowledgement:
        return self._ack(intent, metadata={"simulation": "validation_only"})


class PaperExecutionGateway(_LocalGateway):
    """Delegates to an injected engine_paper runner and never derives price levels."""

    mode = ExecutionMode.PAPER

    def __init__(self, paper_runner: object | None = None,
                 risk_decisions: Mapping[str, object] | None = None) -> None:
        super().__init__()
        if paper_runner is None:
            from app.engine_paper import PaperRunner
            paper_runner = PaperRunner()
        if paper_runner.__class__.__module__.split(".")[:2] != ["app", "engine_paper"]:
            raise TypeError("paper_runner must be provided by app.engine_paper")
        self._paper_runner = paper_runner
        self._risk_decisions = dict(risk_decisions or {})

    def submit(self, intent: ExecutionIntent) -> ExecutionAcknowledgement:
        if intent.status is ExecutionIntentStatus.DUPLICATE:
            return self._ack(intent)
        if intent.idempotency_key in self._acknowledgements:
            return self._ack(intent)
        reasons = self.validate_intent(intent)
        source = self._risk_decisions.get(intent.risk_decision_id)
        if source is None:
            reasons = tuple(dict.fromkeys((*reasons, R.CONTRACT_MISMATCH.value)))
        if reasons:
            return ExecutionAcknowledgement(
                intent.execution_intent_id, intent.idempotency_key, self.mode,
                AckStatus.REJECTED, None, reason_codes=reasons,
            )
        try:
            plan = self._paper_runner.process_risk_decision(source)
        except Exception as exc:
            return ExecutionAcknowledgement(
                intent.execution_intent_id, intent.idempotency_key, self.mode,
                AckStatus.REJECTED, None, reason_codes=(R.CONTRACT_MISMATCH.value,),
                warnings=(f"paper runner rejected safely: {type(exc).__name__}",),
            )
        return self._ack(intent, metadata={
            "paper_plan_id": getattr(plan, "paper_plan_id", None),
            "paper_status": getattr(plan, "paper_status", None),
            "intent_values": {
                "quantity": str(intent.quantity), "reference_price": str(intent.reference_price),
                "stop_price": str(intent.stop_price), "target_price": str(intent.target_price),
            },
        })


class DisabledLiveExecutionGateway(ExecutionGateway):
    def validate_intent(self, intent: ExecutionIntent) -> tuple[str, ...]:
        return (R.LIVE_EXECUTION_DISABLED.value,)

    def submit(self, intent: ExecutionIntent) -> ExecutionAcknowledgement:
        return ExecutionAcknowledgement(
            intent.execution_intent_id, intent.idempotency_key, ExecutionMode.LIVE,
            AckStatus.DISABLED, None, reason_codes=(R.LIVE_EXECUTION_DISABLED.value,),
        )

    def cancel(self, execution_intent_id: str) -> ExecutionAcknowledgement:
        return ExecutionAcknowledgement(
            execution_intent_id, "", ExecutionMode.LIVE, AckStatus.DISABLED, None,
            reason_codes=(R.LIVE_EXECUTION_DISABLED.value,),
        )

    def get_status(self, execution_intent_id: str) -> ExecutionAcknowledgement | None:
        return ExecutionAcknowledgement(
            execution_intent_id, "", ExecutionMode.LIVE, AckStatus.DISABLED, None,
            reason_codes=(R.LIVE_EXECUTION_DISABLED.value,),
        )
