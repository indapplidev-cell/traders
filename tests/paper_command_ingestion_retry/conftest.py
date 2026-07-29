from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.engine_paper.command_ingestion_service import (
    PaperCommandIngestionRequest,
    paper_ingestion_command_id,
)
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.paper_approvals import (
    PaperQuantityApprovalSource,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    issue_paper_quantity_approval,
)
from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperSide,
)
from app.engine_strategy.strategy_decision import StrategyDecision


CLOSED = 1_800_000_000_000
APPROVED_AT = datetime.fromtimestamp((CLOSED + 1_000) / 1000, tz=timezone.utc)
CREATED_AT = datetime.fromtimestamp((CLOSED + 3_000) / 1000, tz=timezone.utc)
VALID = CLOSED + 60_000
Q = Decimal("0.000000000000000001")


def make_research_strategy() -> StrategyDecision:
    return StrategyDecision(
        decision_id="strategy:ingestion:1",
        created_at_ms=CLOSED + 1,
        source_setup_id="setup:ingestion:1",
        source_analysis_snapshot_id="analysis:ingestion:1",
        symbol="BTCUSDT",
        timeframe="15m",
        closed_until_ms=CLOSED,
        decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        direction_hint="BULLISH",
        setup_status="SETUP_CANDIDATE",
        setup_type="BREAKOUT_CONTINUATION",
        setup_quality="GOOD",
        setup_quality_score=90.0,
        strategy_score=82.0,
        strategy_quality="ACCEPTABLE",
        decision_reasons=[],
        decision_warnings=[],
        rejection_reasons=[],
        wait_reasons=[],
        required_next_layer="engine_risk",
        requires_risk_review=True,
        context={},
    )


def make_research_risk() -> RiskDecision:
    return RiskDecision(
        risk_decision_id="risk:ingestion:1",
        created_at_ms=CLOSED + 2,
        source_strategy_decision_id="strategy:ingestion:1",
        source_setup_id="setup:ingestion:1",
        source_analysis_snapshot_id="analysis:ingestion:1",
        symbol="BTCUSDT",
        timeframe="15m",
        closed_until_ms=CLOSED,
        risk_status="RISK_PRE_APPROVED_RESEARCH",
        risk_level="LOW",
        risk_score=90.0,
        risk_policy_version="risk-v1",
        source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="ACCEPTABLE",
        source_strategy_score=82.0,
        direction_hint="BULLISH",
        risk_reasons=[],
        risk_warnings=[],
        rejection_reasons=[],
        wait_reasons=[],
        risk_context={},
        risk_pre_approved=True,
        requires_execution_review=True,
    )


def make_chain(*, approved_at: datetime = APPROVED_AT):
    research_strategy = make_research_strategy()
    research_risk = make_research_risk()
    strategy = finalize_paper_strategy_approval(
        research_strategy,
        mode=ExecutionMode.PAPER,
        paper_authorized=True,
        setup_id="setup:ingestion:1",
        pipeline_run_id="run:ingestion:1",
        analysis_result_id="analysis:ingestion:1",
        side=PaperSide.LONG,
        entry_reference_price=Decimal("100"),
        stop_price=Decimal("90"),
        target_price=Decimal("120"),
        approved_at=approved_at,
        valid_until_ms=VALID,
        configuration_fingerprint="config:ingestion:v1",
        symbol_constraints_id="constraints:BTCUSDT:v1",
        input_health_status=PaperInputHealthStatus.CURRENT,
        future_bars_used=False,
        correlation_id="run:ingestion:1",
        causation_id=research_strategy.decision_id,
        evaluation_time_ms=CLOSED + 2_000,
    )
    quantity = issue_paper_quantity_approval(
        strategy,
        research_risk,
        mode=ExecutionMode.PAPER,
        paper_authorized=True,
        requested_quantity=Decimal("2"),
        approval_source=PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
        approved_at=approved_at,
        valid_until_ms=VALID,
        evaluation_time_ms=CLOSED + 2_000,
        correlation_id="run:ingestion:1",
        causation_id=strategy.approval_id,
    )
    risk = finalize_paper_risk_approval(
        strategy,
        research_risk,
        quantity,
        mode=ExecutionMode.PAPER,
        paper_authorized=True,
        approved_at=approved_at,
        evaluation_time_ms=CLOSED + 2_000,
        correlation_id="run:ingestion:1",
        causation_id=quantity.quantity_approval_id,
    )
    return strategy, quantity, risk


def make_policy(**changes: object) -> PaperFillSimulationPolicy:
    values = {
        "simulation_policy_id": "simulation:foundation:v1",
        "fee_policy_id": "fee:quote:10bps:v1",
        "slippage_policy_id": "slippage:adverse:2bps:v1",
        "latency_policy_id": "latency:one-closed-1m:v1",
        "price_source": PaperFillPriceSource.NEXT_ELIGIBLE_CLOSED_1M_OPEN,
        "timeframe": "1m",
        "latency_candles": 1,
        "slippage_bps": Decimal("2"),
        "fee_bps": Decimal("10"),
        "partial_fill_enabled": False,
        "future_data_allowed": False,
        "intrabar_conflict_policy":
            PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE,
        "price_quantum": Q,
        "fee_quantum": Q,
        "contract_version": "PAPER_FILL_SIMULATION_V1",
    }
    values.update(changes)
    return PaperFillSimulationPolicy(**values)


def make_request(
    *,
    chain=None,
    identity_suffix: str = "1",
    **changes: object,
) -> PaperCommandIngestionRequest:
    strategy, quantity, risk = chain or make_chain()
    values = {
        "paper_strategy_approval": strategy,
        "paper_quantity_approval": quantity,
        "paper_risk_approval": risk,
        "simulation_policy": make_policy(),
        "execution_mode": ExecutionMode.PAPER,
        "explicit_paper_authorization": True,
        "command_id": paper_ingestion_command_id(
            strategy.approval_id,
            quantity.quantity_approval_id,
            risk.approval_id,
        ),
        "order_id": f"order:ingestion:{identity_suffix}",
        "command_event_id": f"event:ingestion:{identity_suffix}:command",
        "order_created_event_id":
            f"event:ingestion:{identity_suffix}:order-created",
        "order_validated_event_id":
            f"event:ingestion:{identity_suffix}:order-validated",
        "order_opened_event_id":
            f"event:ingestion:{identity_suffix}:order-opened",
        "journal_entry_ids": (
            f"event:ingestion:{identity_suffix}:command",
            f"event:ingestion:{identity_suffix}:order-created",
            f"event:ingestion:{identity_suffix}:order-validated",
            f"event:ingestion:{identity_suffix}:order-opened",
        ),
        "created_at": CREATED_AT,
        "correlation_id": strategy.pipeline_run_id,
        "causation_id": risk.approval_id,
    }
    values.update(changes)
    return PaperCommandIngestionRequest(**values)
