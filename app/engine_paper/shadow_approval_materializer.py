"""Non-executable full-funnel materialization for SHADOW trade profiles."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Final

from sqlalchemy.orm import Session

from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.pipeline_result import PipelineResult, json_safe
from app.engine_paper.accounting import PaperAccountSummary
from app.engine_paper.controlled_quantity_validity import calculate_quantity_sizing
from app.engine_paper.final_approval_materializer import (
    FinalApprovalMaterialization,
    _default_account_summary,
)
from app.engine_safety.paper_domain import PaperDomainError


SHADOW_APPROVAL_MATERIALIZER_VERSION: Final = "shadow-final-approval-materializer-v1"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _decimal(value: object, field: str) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _identity(values: tuple[object, ...]) -> str:
    encoded = json.dumps(values, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


class ShadowFinalApprovalMaterializer:
    """Evaluate every post-risk stage without creating executable authority."""

    def __init__(
        self,
        *,
        account_summary_source: Callable[[Session], PaperAccountSummary] =
        _default_account_summary,
    ) -> None:
        self._account_summary_source = account_summary_source

    @staticmethod
    def _generation(
        payload: dict[str, Any],
        *,
        outcome: str,
        stage: str,
        status: str,
        quantity_status: str,
        detail: str,
    ) -> FinalApprovalMaterialization:
        payload["shadow_final_approval_generation"] = {
            "materializer_version": SHADOW_APPROVAL_MATERIALIZER_VERSION,
            "outcome": outcome,
            "stage": stage,
            "status": status,
            "reason_code": outcome,
            "safe_reason_detail": detail,
            "quantity_authority_status": quantity_status,
            "execution_eligible": False,
            "forward_only": True,
        }
        candidate = dict(_mapping(payload.get("shadow_final_approval_candidate")))
        candidate.update({
            "status": "ELIGIBLE" if status == "PASS" else "NOT_ELIGIBLE",
            "execution_eligible": False,
            "persisted_final_approval_created": False,
            "shadow_final_approval_created": status == "PASS",
        })
        payload["shadow_final_approval_candidate"] = candidate
        return FinalApprovalMaterialization(json_safe(payload), False, outcome)

    def materialize(
        self,
        session: Session,
        *,
        run_id: str,
        result: PipelineResult,
        evaluation_time: datetime,
    ) -> FinalApprovalMaterialization:
        payload = dict(result.paper_payload)
        plan = _mapping(payload.get("shadow_plan"))
        checklist = _mapping(payload.get("final_approval_checklist"))
        if (
            result.profile_mode != "SHADOW_SEARCH"
            or result.strategy_status != "ALLOW_RESEARCH_TRADE_PLAN"
            or result.risk_status not in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"}
            or plan.get("paper_status") != "PAPER_PLAN_READY"
            or checklist.get("passed") is not True
        ):
            return self._generation(
                payload,
                outcome="NOT_ELIGIBLE",
                stage="PAPER_TRADE_PLAN",
                status="NOT_REACHED",
                quantity_status="NOT_REACHED",
                detail="shadow plan is not eligible",
            )

        stage = "FINAL_APPROVAL"
        quantity_status = "NOT_REACHED"
        try:
            strategy = _mapping(result.strategy_payload)
            risk = _mapping(result.risk_payload)
            setup = _mapping(result.setup_payload)
            if (
                plan.get("symbol") != result.symbol
                or plan.get("timeframe") != result.primary_timeframe
                or int(plan.get("closed_until_ms", -1)) != result.closed_until_ms
                or plan.get("source_risk_decision_id") != risk.get("risk_decision_id")
                or plan.get("source_strategy_decision_id") != strategy.get("decision_id")
                or plan.get("source_setup_id") != setup.get("setup_id")
            ):
                raise ValueError("same-run shadow lineage mismatch")

            entry = _decimal(plan.get("hypothetical_entry_reference"), "entry")
            stop = _decimal(plan.get("hypothetical_stop_level"), "stop")
            target = _decimal(plan.get("hypothetical_target_level"), "target")
            planned_rr = _decimal(plan.get("planned_rr"), "planned_rr")
            risk_score = _decimal(risk.get("risk_score"), "risk_score")
            strategy_score = _decimal(strategy.get("strategy_score"), "strategy_score")
            if entry <= 0 or stop <= 0 or target <= 0 or planned_rr <= 0:
                raise ValueError("shadow levels and planned RR must be positive")

            stage = "QUANTITY_APPROVED"
            account = self._account_summary_source(session)
            sizing = calculate_quantity_sizing(
                symbol=result.symbol,
                equity=account.current_balance,
                entry=entry,
                stop=stop,
            )
            quantity_status = "PASS"

            stage = "VALIDITY_APPROVED"
            validity = _mapping(payload.get("validity_policy"))
            valid_until_ms = int(validity.get("valid_until_ms", -1))
            expected_valid_until_ms = result.closed_until_ms + (
                timeframe_to_milliseconds(result.primary_timeframe)
                * int(validity.get("validity_boundaries", 0))
            )
            evaluation_time_ms = int(evaluation_time.timestamp() * 1000)
            if valid_until_ms != expected_valid_until_ms or evaluation_time_ms > valid_until_ms:
                raise ValueError("shadow approval validity is invalid or expired")

            stage = "FINAL_APPROVAL"
            candidate_id = str(_mapping(
                payload.get("shadow_final_approval_candidate")
            ).get("candidate_id") or (
                f"shadow:{result.trade_profile_id}:{result.symbol}:{result.closed_until_ms}"
            ))
            digest = _identity((
                SHADOW_APPROVAL_MATERIALIZER_VERSION,
                run_id,
                candidate_id,
                result.runtime_parameter_set_id,
                format(sizing.normalized_quantity, "f"),
                valid_until_ms,
            ))
            final_approval_id = f"shadow-final:{digest}"
            payload["shadow_approvals"] = {
                "shadow_plan_approval": {
                    "approval_id": f"shadow-plan:{digest}",
                    "status": "PASS",
                    "planned_risk_reward": format(planned_rr, "f"),
                    "execution_eligible": False,
                },
                "shadow_quantity_approval": {
                    "approval_id": f"shadow-quantity:{digest}",
                    "status": "PASS",
                    "approved_quantity": format(sizing.normalized_quantity, "f"),
                    "sizing_audit": sizing.to_dict(),
                    "execution_eligible": False,
                },
                "shadow_validity_approval": {
                    "approval_id": f"shadow-validity:{digest}",
                    "status": "PASS",
                    "valid_until_ms": valid_until_ms,
                    "execution_eligible": False,
                },
                "shadow_final_approval": {
                    "approval_id": final_approval_id,
                    "status": "PASS",
                    "valid_until_ms": valid_until_ms,
                    "execution_eligible": False,
                },
            }
            candidate = dict(_mapping(payload.get("shadow_final_approval_candidate")))
            candidate.update({
                "candidate_id": candidate_id,
                "final_approval_id": final_approval_id,
                "source_run_id": run_id,
                "symbol": result.symbol,
                "risk_score": format(risk_score, "f"),
                "strategy_score": format(strategy_score, "f"),
                "planned_risk_reward": format(planned_rr, "f"),
                "closed_until_ms": result.closed_until_ms,
                "valid_until_ms": valid_until_ms,
                "approved_quantity": format(sizing.normalized_quantity, "f"),
            })
            payload["shadow_final_approval_candidate"] = candidate
            materialized = self._generation(
                payload,
                outcome="SHADOW_FINAL_APPROVAL_CREATED",
                stage="FINAL_APPROVAL",
                status="PASS",
                quantity_status="PASS",
                detail="non-executable shadow final approval created",
            )
            complete = dict(materialized.paper_payload)
            generation = dict(_mapping(complete.get("shadow_final_approval_generation")))
            generation["final_approval_id"] = final_approval_id
            generation["candidate_id"] = candidate_id
            generation["source_run_id"] = run_id
            generation["valid_until_ms"] = valid_until_ms
            complete["shadow_final_approval_generation"] = generation
            return FinalApprovalMaterialization(
                json_safe(complete), False, "SHADOW_FINAL_APPROVAL_CREATED"
            )
        except PaperDomainError as error:
            detail = error.public_message
            if error.field_path:
                detail = f"{detail} ({error.field_path})"
            return self._generation(
                payload,
                outcome=error.reason_code.value,
                stage=stage,
                status="REJECTED",
                quantity_status="REJECTED" if stage == "QUANTITY_APPROVED" else quantity_status,
                detail=detail,
            )
        except Exception:
            return self._generation(
                payload,
                outcome="SAFE_SHADOW_MATERIALIZATION_FAILURE",
                stage=stage,
                status="ERROR",
                quantity_status=quantity_status,
                detail="safe shadow final approval materialization failure",
            )


DEFAULT_SHADOW_FINAL_APPROVAL_MATERIALIZER = ShadowFinalApprovalMaterializer()


__all__ = (
    "DEFAULT_SHADOW_FINAL_APPROVAL_MATERIALIZER",
    "SHADOW_APPROVAL_MATERIALIZER_VERSION",
    "ShadowFinalApprovalMaterializer",
)
