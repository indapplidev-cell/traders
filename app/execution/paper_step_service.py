"""Сервис одного шага paper trading без CLI-зависимостей."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Candle
from app.execution.paper_execution_engine import PaperExecutionEngine
from app.execution.position_manager import PositionManager
from app.journal.trade_journal import TradeJournal, TradeJournalPayload
from app.market.indicator_service import IndicatorSnapshot
from app.risk.risk_manager import RiskManager
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


@dataclass(slots=True)
class PaperStepResult:
    """Результат полного шага paper trading."""

    strategy_decision: TradeDecision
    final_decision: TradeDecision
    risk_approved: bool
    risk_reason: str
    execution_action: str
    execution_message: str
    has_execution_error: bool = False


class PaperStepService:
    """Связывает стратегию, риск-контроль, исполнение и журналирование."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def process(
        self,
        strategy_decision: TradeDecision,
        *,
        indicator_snapshot: IndicatorSnapshot | None = None,
        latest_candle: Candle | None = None,
    ) -> PaperStepResult:
        """Обрабатывает решение стратегии и сохраняет полную историю шага."""

        execution_engine = PaperExecutionEngine(self.session)
        portfolio_state = PositionManager(self.session).get_portfolio_state()
        risk_result = RiskManager().validate_decision(strategy_decision, portfolio_state)

        final_decision = strategy_decision
        execution_action = "SKIPPED"
        execution_message = "Исполнение не выполнялось."

        protective_result = None
        if latest_candle is not None:
            protective_result = execution_engine.check_protective_exit(strategy_decision.symbol, latest_candle)

        if protective_result is not None:
            final_decision = TradeDecision.build(
                symbol=strategy_decision.symbol,
                interval=strategy_decision.interval,
                decision=DecisionType.SELL,
                reason=protective_result.message,
                regime=MarketRegime.UNKNOWN,
                price=protective_result.price or strategy_decision.price,
                created_at=latest_candle.close_time,
            )
            risk_result.approved = True
            risk_result.reason = "Защитное закрытие позиции не требует отдельной риск-проверки."
            execution_action = protective_result.action
            execution_message = protective_result.message
        elif risk_result.approved:
            try:
                execution_result = execution_engine.execute(
                    strategy_decision,
                    indicator_snapshot=indicator_snapshot,
                )
                execution_action = execution_result.action
                execution_message = execution_result.message
            except Exception as exc:
                final_decision = TradeDecision.build(
                    symbol=strategy_decision.symbol,
                    interval=strategy_decision.interval,
                    decision=DecisionType.HOLD,
                    reason=f"Исполнение завершилось ошибкой: {exc}",
                    regime=strategy_decision.regime,
                    price=strategy_decision.price,
                    created_at=strategy_decision.created_at,
                )
                execution_action = "ERROR"
                execution_message = str(exc)
                payload = TradeJournalPayload(
                    strategy_decision=strategy_decision,
                    final_decision=final_decision,
                    risk_approved=risk_result.approved,
                    risk_reason=risk_result.reason,
                    execution_action=execution_action,
                    execution_message=execution_message,
                )
                TradeJournal(self.session).record(payload)
                return PaperStepResult(
                    strategy_decision=strategy_decision,
                    final_decision=final_decision,
                    risk_approved=risk_result.approved,
                    risk_reason=risk_result.reason,
                    execution_action=execution_action,
                    execution_message=execution_message,
                    has_execution_error=True,
                )
        else:
            final_decision = TradeDecision.build(
                symbol=strategy_decision.symbol,
                interval=strategy_decision.interval,
                decision=DecisionType.HOLD,
                reason=f"Решение отклонено RiskManager: {risk_result.reason}",
                regime=strategy_decision.regime,
                price=strategy_decision.price,
                created_at=strategy_decision.created_at,
            )
            execution_message = risk_result.reason

        payload = TradeJournalPayload(
            strategy_decision=strategy_decision,
            final_decision=final_decision,
            risk_approved=risk_result.approved,
            risk_reason=risk_result.reason,
            execution_action=execution_action,
            execution_message=execution_message,
        )
        TradeJournal(self.session).record(payload)

        return PaperStepResult(
            strategy_decision=strategy_decision,
            final_decision=final_decision,
            risk_approved=risk_result.approved,
            risk_reason=risk_result.reason,
            execution_action=execution_action,
            execution_message=execution_message,
            has_execution_error=False,
        )
