from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.db.models import PaperPosition
from app.execution.paper_step_service import PaperStepService
from app.execution.position_manager import PaperPortfolioState
from app.risk.risk_manager import RiskManager
from app.strategy.base_strategy import StrategyDecision
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


def build_trade_decision(decision: DecisionType) -> TradeDecision:
    return TradeDecision.build(
        symbol="BTCUSDT",
        interval="15m",
        decision=decision,
        reason="test decision",
        regime=MarketRegime.UNKNOWN,
        price=Decimal("100"),
        created_at=datetime.now(UTC),
    )


def build_strategy_decision(action: str, confidence: float = 0.9) -> StrategyDecision:
    return StrategyDecision(
        strategy_name="simple_trend",
        strategy_version="1.0",
        symbol="BTCUSDT",
        interval="15m",
        action=action,
        reason="runtime signal",
        confidence=confidence,
        metadata={"price": "100", "market_regime": "UNKNOWN"},
    )


def build_portfolio(*, open_positions: list[PaperPosition] | None = None) -> PaperPortfolioState:
    return PaperPortfolioState(
        balance_usdt=Decimal("1000"),
        open_positions=open_positions or [],
        realized_pnl=Decimal("0"),
    )


def build_open_position() -> PaperPosition:
    return PaperPosition(
        symbol="BTCUSDT",
        side="LONG",
        status="OPEN",
        entry_price=Decimal("100"),
        quantity=Decimal("0.1"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("105"),
        opened_at=datetime.now(UTC),
        closed_at=None,
        close_price=None,
        realized_pnl=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_risk_rejects_duplicate_buy_for_open_symbol() -> None:
    result = RiskManager().validate_strategy_decision(
        build_strategy_decision("BUY"),
        build_portfolio(open_positions=[build_open_position()]),
    )

    assert result.approved is False
    assert result.final_action == "HOLD"


def test_risk_rejects_sell_without_open_position() -> None:
    result = RiskManager().validate_strategy_decision(build_strategy_decision("SELL"), build_portfolio())

    assert result.approved is False
    assert result.final_action == "HOLD"


def test_risk_rejects_low_confidence_action() -> None:
    result = RiskManager().validate_strategy_decision(build_strategy_decision("BUY", confidence=0.10), build_portfolio())

    assert result.approved is False
    assert result.final_action == "HOLD"
    assert "low_confidence" in result.reason


def test_hold_does_not_create_paper_order(sqlite_session) -> None:
    result = PaperStepService(sqlite_session).process(build_trade_decision(DecisionType.HOLD))
    open_positions = sqlite_session.execute(select(PaperPosition).where(PaperPosition.status == "OPEN")).scalars().all()

    assert result.risk_approved is True
    assert result.execution_action == "HOLD"
    assert open_positions == []
