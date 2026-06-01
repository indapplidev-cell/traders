"""Сохранение решений стратегии в БД."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import TradeDecisionRecord
from app.strategy.trade_decision import TradeDecision


@dataclass(slots=True)
class TradeJournalPayload:
    """Полный набор данных для записи результата одного paper-step."""

    strategy_decision: TradeDecision
    final_decision: TradeDecision
    risk_approved: bool
    risk_reason: str
    execution_action: str
    execution_message: str


class TradeJournal:
    """Журналирует торговые решения вне зависимости от исполнения."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, payload: TradeJournalPayload) -> TradeDecisionRecord:
        """Сохраняет решение в таблицу trade_decisions."""

        record = TradeDecisionRecord(
            symbol=payload.strategy_decision.symbol,
            interval=payload.strategy_decision.interval,
            strategy_decision=payload.strategy_decision.decision.value,
            strategy_reason=payload.strategy_decision.reason,
            final_decision=payload.final_decision.decision.value,
            final_reason=payload.final_decision.reason,
            regime=payload.strategy_decision.regime.value,
            price=payload.strategy_decision.price,
            risk_approved=payload.risk_approved,
            risk_reason=payload.risk_reason,
            execution_action=payload.execution_action,
            execution_message=payload.execution_message,
            created_at=payload.strategy_decision.created_at,
        )
        self.session.add(record)
        self.session.flush()
        return record
