"""Transactional, read-only PAPER portfolio admission for final approvals."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters


PORTFOLIO_GATE_VERSION: Final = "paper-portfolio-admission-v1"


def evaluate_paper_portfolio_gate(
    session: Session,
    *,
    result: PipelineResult,
    candidate_direction: str,
    account_equity: Decimal,
    evaluation_time: datetime,
) -> dict[str, Any]:
    """Evaluate one candidate against the authoritative persisted PAPER book."""
    parameters = resolve_runtime_parameters(result.trade_profile_id)
    rows = tuple(session.execute(
        select(PaperPositionRecord, OnlinePipelineRun.trade_profile_id)
        .join(PaperOrderRecord, PaperOrderRecord.order_id == PaperPositionRecord.entry_order_id)
        .join(
            PaperExecutionCommandRecord,
            PaperExecutionCommandRecord.command_id == PaperOrderRecord.command_id,
        )
        .outerjoin(
            OnlinePipelineRun,
            OnlinePipelineRun.run_id == PaperExecutionCommandRecord.pipeline_run_id,
        )
        .where(PaperPositionRecord.state.in_(("OPEN", "CLOSING")))
    ))
    active = tuple(row[0] for row in rows)
    symbols = tuple(sorted({row.symbol.upper() for row in active}))
    same_symbol = result.symbol.upper() in symbols
    candidate_side = "LONG" if candidate_direction == "BULLISH" else "SHORT"
    same_direction_count = sum(row.side == candidate_side for row in active)
    profile_count = sum(profile_id == result.trade_profile_id for _, profile_id in rows)
    equity = Decimal(account_equity)
    open_risk_amount = sum((
        Decimal(row.remaining_quantity)
        * abs(Decimal(row.average_entry_price) - Decimal(row.stop_price))
        for row in active
    ), Decimal("0"))
    open_risk_bps = (
        Decimal("0") if equity <= 0
        else open_risk_amount / equity * Decimal("10000")
    )
    candidate_risk_bps = Decimal(str(parameters.risk_per_trade_bps))
    projected_risk_bps = open_risk_bps + candidate_risk_bps
    max_positions = int(parameters.portfolio_max_concurrent_positions)
    max_risk_bps = Decimal(str(parameters.portfolio_max_total_open_risk_bps))

    reason = "PORTFOLIO_ADMITTED"
    decision = "PASS"
    if same_symbol:
        decision, reason = "REJECT", "PORTFOLIO_REJECT_DUPLICATE_OR_OPPOSING_SYMBOL"
    elif len(active) + 1 > max_positions:
        decision, reason = "REJECT", "PORTFOLIO_REJECT_MAX_CONCURRENT_POSITIONS"
    elif projected_risk_bps > max_risk_bps:
        decision, reason = "REJECT", "PORTFOLIO_REJECT_TOTAL_OPEN_RISK"

    return {
        "policy_version": PORTFOLIO_GATE_VERSION,
        "runtime_parameter_set_id": parameters.parameter_set_id,
        "evaluation_timestamp": evaluation_time.isoformat(),
        "decision": decision,
        "reason_code": reason,
        "measured": {
            "active_position_count": len(active),
            "active_profile_position_count": profile_count,
            "active_same_direction_count": same_direction_count,
            "active_symbols": list(symbols),
            "existing_open_risk_amount": format(open_risk_amount, "f"),
            "existing_open_risk_bps": format(open_risk_bps, "f"),
            "candidate_risk_bps": format(candidate_risk_bps, "f"),
            "projected_total_open_risk_bps": format(projected_risk_bps, "f"),
            "duplicate_or_opposing_symbol": same_symbol,
        },
        "limits": {
            "max_concurrent_positions": max_positions,
            "max_total_open_risk_bps": format(max_risk_bps, "f"),
            "same_symbol_exposure_allowed": False,
            "correlation_limit": None,
            "correlation_evidence_state": "NOT_APPLICABLE_NO_CANONICAL_GROUP_ON_PAPER_POSITION",
        },
        "deterministic": True,
    }


__all__ = ("PORTFOLIO_GATE_VERSION", "evaluate_paper_portfolio_gate")
