"""Forward-only materialization of natural online PAPER final approvals."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Final

from sqlalchemy.orm import Session

from app.engine_orchestrator.pipeline_result import PipelineResult, json_safe
from app.engine_paper.accounting import (
    PaperAccountAccountingService,
    PaperAccountSummary,
)
from app.engine_paper.controlled_quantity_validity import (
    QUANTITY_POLICY_VERSION,
    VALIDITY_POLICY_VERSION,
    derive_approval_valid_until_ms,
    issue_controlled_paper_quantity_approval,
)
from app.engine_paper.paper_approvals import (
    approval_serialization,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    map_final_approvals_to_command_compatibility,
)
from app.engine_paper.paper_trade_plan import PaperTradePlan
from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperDomainError,
    PaperInputHealthStatus,
    PaperSide,
)
from app.engine_strategy.strategy_decision import StrategyDecision
from app.instrument_constraints.registry import (
    ACTIVE_QUANTITY_CONSTRAINT_REGISTRY,
    REGISTRY_VERSION,
)
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter


FINAL_APPROVAL_MATERIALIZER_VERSION: Final = "natural-final-approval-materializer-v1"
FINAL_APPROVAL_COMPONENT_KEYS: Final = (
    "paper_strategy_approval",
    "paper_quantity_approval",
    "paper_risk_approval",
)
MAX_ACCOUNTING_CLOSED_TRADES: Final = 10_000


@dataclass(frozen=True, slots=True)
class FinalApprovalMaterialization:
    paper_payload: Mapping[str, Any]
    final_approval_created: bool
    outcome: str
    idempotency_key: str | None = None


def _typed(cls: type, payload: Mapping[str, Any]):
    names = {field.name for field in fields(cls) if field.init}
    return cls(**{name: payload[name] for name in names})


def _canonical_hash(values: tuple[object, ...]) -> str:
    encoded = json.dumps(values, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _default_account_summary(session: Session) -> PaperAccountSummary:
    reader = SqlAlchemyReadAdapter(session)
    baselines = reader.list_account_baselines(2)
    if len(baselines) != 1:
        raise ValueError("authoritative PAPER account baseline is unavailable")
    trades = reader.list_closed_trade_facts(MAX_ACCOUNTING_CLOSED_TRADES + 1)
    if len(trades) > MAX_ACCOUNTING_CLOSED_TRADES:
        raise ValueError("authoritative PAPER accounting scope exceeded")
    result = PaperAccountAccountingService().project(baselines[0], trades)
    reports, summary = result
    if len(reports) != len(trades):
        raise ValueError("authoritative PAPER accounting projection mismatch")
    return summary


def _default_configuration_fingerprint(
    session: Session, result: PipelineResult
) -> str:
    del session
    plan_context = result.paper_payload.get("paper_context")
    if not isinstance(plan_context, Mapping):
        raise ValueError("PAPER plan policy lineage is unavailable")
    plan_policy_version = plan_context.get("plan_policy_version")
    risk_policy_version = result.risk_payload.get("risk_policy_version")
    if not plan_policy_version or not risk_policy_version:
        raise ValueError("same-run policy lineage is incomplete")
    material = (
        "paper-final-approval-configuration-v1",
        result.primary_timeframe,
        str(risk_policy_version),
        str(plan_policy_version),
        QUANTITY_POLICY_VERSION,
        VALIDITY_POLICY_VERSION,
        REGISTRY_VERSION,
        ACTIVE_QUANTITY_CONSTRAINT_REGISTRY.universe_id,
    )
    return "paper:approval-config:v1:" + _canonical_hash(material)


class NaturalFinalApprovalMaterializer:
    """Compose existing authorities without re-running strategy, risk, or ranking."""

    def __init__(
        self,
        *,
        account_summary_source: Callable[[Session], PaperAccountSummary] = _default_account_summary,
        configuration_fingerprint_source: Callable[[Session, PipelineResult], str] =
        _default_configuration_fingerprint,
    ) -> None:
        self._account_summary_source = account_summary_source
        self._configuration_fingerprint_source = configuration_fingerprint_source

    @staticmethod
    def _not_created(result: PipelineResult, outcome: str) -> FinalApprovalMaterialization:
        payload = dict(result.paper_payload)
        payload["final_approval_generation"] = {
            "materializer_version": FINAL_APPROVAL_MATERIALIZER_VERSION,
            "outcome": outcome,
            "forward_only": True,
        }
        return FinalApprovalMaterialization(payload, False, outcome)

    def materialize(
        self,
        session: Session,
        *,
        run_id: str,
        result: PipelineResult,
        evaluation_time: datetime,
    ) -> FinalApprovalMaterialization:
        if (
            result.primary_timeframe != "15m"
            or result.paper_status != "PAPER_PLAN_READY"
            or result.strategy_status != "ALLOW_RESEARCH_TRADE_PLAN"
            or result.risk_status != "RISK_PRE_APPROVED_RESEARCH"
        ):
            return self._not_created(result, "NOT_ELIGIBLE")

        try:
            strategy = _typed(StrategyDecision, result.strategy_payload)
            research_risk = _typed(RiskDecision, result.risk_payload)
            plan = _typed(PaperTradePlan, result.paper_payload)
            analysis = result.analysis_payload
            setup = result.setup_payload
            primary_market = result.market_data_payload[result.primary_timeframe]
            source_close_ms = int(primary_market["last_close_time_ms"])
            evaluation_time_ms = int(evaluation_time.timestamp() * 1000)

            if (
                result.symbol != strategy.symbol
                or result.symbol != research_risk.symbol
                or result.symbol != plan.symbol
                or result.closed_until_ms != strategy.closed_until_ms
                or result.closed_until_ms != research_risk.closed_until_ms
                or result.closed_until_ms != plan.closed_until_ms
                or source_close_ms + 1 != result.closed_until_ms
                or strategy.source_setup_id != setup.get("setup_id")
                or strategy.source_analysis_snapshot_id != analysis.get("snapshot_id")
                or research_risk.source_strategy_decision_id != strategy.decision_id
                or research_risk.source_setup_id != strategy.source_setup_id
                or research_risk.source_analysis_snapshot_id != strategy.source_analysis_snapshot_id
                or plan.source_risk_decision_id != research_risk.risk_decision_id
                or plan.source_strategy_decision_id != strategy.decision_id
                or plan.source_setup_id != strategy.source_setup_id
                or plan.source_analysis_snapshot_id != strategy.source_analysis_snapshot_id
            ):
                return self._not_created(result, "LINEAGE_MISMATCH")

            side = PaperSide.LONG if plan.paper_direction == "BULLISH" else (
                PaperSide.SHORT if plan.paper_direction == "BEARISH" else None
            )
            if side is None or strategy.direction_hint != plan.paper_direction or research_risk.direction_hint != plan.paper_direction:
                return self._not_created(result, "DIRECTION_MISMATCH")

            prerequisite_ms = max(
                int(result.analysis_payload["created_at_ms"]),
                int(result.setup_payload["created_at_ms"]),
                int(strategy.created_at_ms),
                int(research_risk.created_at_ms),
                int(plan.created_at_ms),
            )
            approved_at = datetime.fromtimestamp(prerequisite_ms / 1000, tz=timezone.utc)
            valid_until_ms = derive_approval_valid_until_ms(
                source_close_ms, evaluation_time_ms=evaluation_time_ms
            )
            configuration_fingerprint = self._configuration_fingerprint_source(session, result)
            account = self._account_summary_source(session)

            strategy_approval = finalize_paper_strategy_approval(
                strategy,
                mode=ExecutionMode.PAPER,
                paper_authorized=True,
                setup_id=strategy.source_setup_id,
                pipeline_run_id=run_id,
                analysis_result_id=strategy.source_analysis_snapshot_id,
                side=side,
                entry_reference_price=Decimal(str(plan.hypothetical_entry_reference)),
                stop_price=Decimal(str(plan.hypothetical_stop_level)),
                target_price=Decimal(str(plan.hypothetical_target_level)),
                approved_at=approved_at,
                valid_until_ms=valid_until_ms,
                configuration_fingerprint=configuration_fingerprint,
                symbol_constraints_id=REGISTRY_VERSION,
                input_health_status=PaperInputHealthStatus.CURRENT,
                future_bars_used=False,
                correlation_id=run_id,
                causation_id=strategy.decision_id,
                evaluation_time_ms=evaluation_time_ms,
            )
            controlled_quantity = issue_controlled_paper_quantity_approval(
                strategy_approval,
                research_risk,
                account,
                approved_at=approved_at,
                evaluation_time_ms=evaluation_time_ms,
                source_candle_close_time_ms=source_close_ms,
            )
            risk_approval = finalize_paper_risk_approval(
                strategy_approval,
                research_risk,
                controlled_quantity.approval,
                mode=ExecutionMode.PAPER,
                paper_authorized=True,
                approved_at=approved_at,
                evaluation_time_ms=evaluation_time_ms,
                correlation_id=run_id,
                causation_id=controlled_quantity.approval.quantity_approval_id,
            )
            compatibility = map_final_approvals_to_command_compatibility(
                strategy_approval, controlled_quantity.approval, risk_approval
            )
            if compatibility.valid_until_ms != min(
                strategy_approval.valid_until_ms,
                controlled_quantity.approval.valid_until_ms,
                risk_approval.valid_until_ms,
            ):
                raise ValueError("final approval validity mismatch")

            idempotency_key = "paper:final-approval:v1:" + _canonical_hash((
                run_id,
                analysis.get("snapshot_id"),
                setup.get("setup_id"),
                strategy.decision_id,
                research_risk.risk_decision_id,
                plan.paper_plan_id,
                result.symbol,
                plan.paper_direction,
                source_close_ms,
                QUANTITY_POLICY_VERSION,
                VALIDITY_POLICY_VERSION,
                REGISTRY_VERSION,
                configuration_fingerprint,
            ))
            quantity_payload = controlled_quantity.to_persisted_payload()
            payload = dict(result.paper_payload)
            payload.update(quantity_payload)
            payload["persisted_final_approvals"] = {
                FINAL_APPROVAL_COMPONENT_KEYS[0]: approval_serialization(strategy_approval),
                FINAL_APPROVAL_COMPONENT_KEYS[1]: approval_serialization(controlled_quantity.approval),
                FINAL_APPROVAL_COMPONENT_KEYS[2]: approval_serialization(risk_approval),
            }
            payload["final_approval_generation"] = {
                "materializer_version": FINAL_APPROVAL_MATERIALIZER_VERSION,
                "outcome": "FINAL_APPROVAL_CREATED",
                "idempotency_key": idempotency_key,
                "final_approval_id": risk_approval.approval_id,
                "source_run_id": run_id,
                "candidate_id": setup.get("setup_id"),
                "symbol": result.symbol,
                "direction": plan.paper_direction,
                "source_candle_close_time_ms": source_close_ms,
                "quantity_policy_version": QUANTITY_POLICY_VERSION,
                "validity_policy_version": VALIDITY_POLICY_VERSION,
                "instrument_registry_version": REGISTRY_VERSION,
                "final_valid_until_ms": compatibility.valid_until_ms,
                "forward_only": True,
            }
            return FinalApprovalMaterialization(json_safe(payload), True, "FINAL_APPROVAL_CREATED", idempotency_key)
        except PaperDomainError as error:
            return self._not_created(result, error.reason_code.value)
        except Exception:
            return self._not_created(result, "SAFE_MATERIALIZATION_FAILURE")


DEFAULT_NATURAL_FINAL_APPROVAL_MATERIALIZER = NaturalFinalApprovalMaterializer()


__all__ = (
    "DEFAULT_NATURAL_FINAL_APPROVAL_MATERIALIZER",
    "FINAL_APPROVAL_COMPONENT_KEYS",
    "FINAL_APPROVAL_MATERIALIZER_VERSION",
    "FinalApprovalMaterialization",
    "NaturalFinalApprovalMaterializer",
)
