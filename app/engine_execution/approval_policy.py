"""Exact-match approval policy for safe execution-intent inputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.engine_execution.enums import ExecutionReasonCode as R


class ApprovalScope(StrEnum):
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"
    RESEARCH_ONLY = "RESEARCH_ONLY"


PRODUCTION_APPROVAL_PAIR = ("APPROVED", "RISK_APPROVED")
RESEARCH_APPROVAL_PAIR = ("ALLOW_RESEARCH_TRADE_PLAN", "RISK_PRE_APPROVED_RESEARCH")
APPROVED_STRATEGY_STATUSES = frozenset(pair[0] for pair in (
    PRODUCTION_APPROVAL_PAIR, RESEARCH_APPROVAL_PAIR,
))
APPROVED_RISK_STATUSES = frozenset(pair[1] for pair in (
    PRODUCTION_APPROVAL_PAIR, RESEARCH_APPROVAL_PAIR,
))


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    scope: ApprovalScope | None
    reason_codes: tuple[str, ...]


def evaluate_approval_pair(strategy_status: object, risk_status: object) -> ApprovalResult:
    """Classify one exact status pair; mixed approved classes are invalid."""
    pair = (str(strategy_status or "").upper(), str(risk_status or "").upper())
    if pair == PRODUCTION_APPROVAL_PAIR:
        return ApprovalResult(ApprovalScope.PRODUCTION_APPROVED, ())
    if pair == RESEARCH_APPROVAL_PAIR:
        return ApprovalResult(ApprovalScope.RESEARCH_ONLY, ())
    if pair[0] in APPROVED_STRATEGY_STATUSES and pair[1] in APPROVED_RISK_STATUSES:
        return ApprovalResult(None, (R.CONTRACT_MISMATCH.value,))
    reasons: list[str] = []
    if pair[0] not in APPROVED_STRATEGY_STATUSES:
        reasons.append(R.STRATEGY_NOT_APPROVED.value)
    if pair[1] not in APPROVED_RISK_STATUSES:
        reasons.append(R.RISK_NOT_APPROVED.value)
    return ApprovalResult(None, tuple(reasons))
