from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_paper.paper_approvals import (
    PaperQuantityApprovalSource,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    issue_paper_quantity_approval,
)
from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import ExecutionMode, PaperInputHealthStatus, PaperSide
from app.engine_strategy.strategy_decision import StrategyDecision


CLOSED = 1_700_000_000_000
APPROVED_AT = datetime.fromtimestamp((CLOSED + 1_000) / 1000, tz=timezone.utc)
VALID = CLOSED + 60_000


def make_strategy(**changes: object) -> StrategyDecision:
    values: dict[str, object] = {
        "decision_id": "strategy:1",
        "created_at_ms": CLOSED + 1,
        "source_setup_id": "setup:1",
        "source_analysis_snapshot_id": "analysis:1",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "closed_until_ms": CLOSED,
        "decision_status": "ALLOW_RESEARCH_TRADE_PLAN",
        "strategy_type": "BREAKOUT_CONTINUATION_RESEARCH",
        "direction_hint": "BULLISH",
        "setup_status": "SETUP_CANDIDATE",
        "setup_type": "BREAKOUT_CONTINUATION",
        "setup_quality": "GOOD",
        "setup_quality_score": 90.0,
        "strategy_score": 82.0,
        "strategy_quality": "ACCEPTABLE",
        "decision_reasons": [],
        "decision_warnings": [],
        "rejection_reasons": [],
        "wait_reasons": [],
        "required_next_layer": "engine_risk",
        "requires_risk_review": True,
        "context": {},
    }
    values.update(changes)
    if values["decision_status"] != "ALLOW_RESEARCH_TRADE_PLAN":
        values["required_next_layer"] = None
        values["requires_risk_review"] = False
    return StrategyDecision(**values)


def make_risk(**changes: object) -> RiskDecision:
    values: dict[str, object] = {
        "risk_decision_id": "risk:1",
        "created_at_ms": CLOSED + 2,
        "source_strategy_decision_id": "strategy:1",
        "source_setup_id": "setup:1",
        "source_analysis_snapshot_id": "analysis:1",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "closed_until_ms": CLOSED,
        "risk_status": "RISK_PRE_APPROVED_RESEARCH",
        "risk_level": "LOW",
        "risk_score": 90.0,
        "risk_policy_version": "risk-v1",
        "source_decision_status": "ALLOW_RESEARCH_TRADE_PLAN",
        "source_strategy_type": "BREAKOUT_CONTINUATION_RESEARCH",
        "source_strategy_quality": "ACCEPTABLE",
        "source_strategy_score": 82.0,
        "direction_hint": "BULLISH",
        "risk_reasons": [],
        "risk_warnings": [],
        "rejection_reasons": [],
        "wait_reasons": [],
        "risk_context": {},
        "risk_pre_approved": True,
        "requires_execution_review": True,
    }
    values.update(changes)
    if values["risk_status"] != "RISK_PRE_APPROVED_RESEARCH":
        values["risk_pre_approved"] = False
        values["requires_execution_review"] = False
    return RiskDecision(**values)


def strategy_kwargs(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "mode": ExecutionMode.PAPER,
        "paper_authorized": True,
        "setup_id": "setup:1",
        "pipeline_run_id": "run:1",
        "analysis_result_id": "analysis:1",
        "side": PaperSide.LONG,
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("90"),
        "target_price": Decimal("120"),
        "approved_at": APPROVED_AT,
        "valid_until_ms": VALID,
        "configuration_fingerprint": "config:v1",
        "symbol_constraints_id": "constraints:BTCUSDT:v1",
        "input_health_status": PaperInputHealthStatus.CURRENT,
        "future_bars_used": False,
        "correlation_id": "run:1",
        "causation_id": "strategy:1",
        "evaluation_time_ms": CLOSED + 2_000,
    }
    values.update(changes)
    return values


@pytest.fixture
def approval_chain():
    research_strategy = make_strategy()
    research_risk = make_risk()
    strategy = finalize_paper_strategy_approval(
        research_strategy, **strategy_kwargs()
    )
    quantity = issue_paper_quantity_approval(
        strategy,
        research_risk,
        mode=ExecutionMode.PAPER,
        paper_authorized=True,
        requested_quantity=Decimal("2"),
        approval_source=PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
        approved_at=APPROVED_AT,
        valid_until_ms=VALID,
        evaluation_time_ms=CLOSED + 2_000,
        correlation_id="run:1",
        causation_id=strategy.approval_id,
    )
    risk = finalize_paper_risk_approval(
        strategy,
        research_risk,
        quantity,
        mode=ExecutionMode.PAPER,
        paper_authorized=True,
        approved_at=APPROVED_AT,
        evaluation_time_ms=CLOSED + 2_000,
        correlation_id="run:1",
        causation_id=quantity.quantity_approval_id,
    )
    return research_strategy, research_risk, strategy, quantity, risk
