"""Сервис одного шага paper trading без CLI-зависимостей."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Candle
from app.execution.paper_execution_engine import PaperExecutionEngine
from app.execution.position_manager import PositionManager
from app.journal.trade_journal import TradeJournal, TradeJournalPayload
from app.market.indicator_service import IndicatorSnapshot
from app.risk.risk_manager import RiskManager
from app.strategy.base_strategy import StrategyDecision
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
    journal_id: int | None = None


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
        runtime_decision: StrategyDecision | None = None,
    ) -> PaperStepResult:
        """Обрабатывает решение стратегии и сохраняет полную историю шага."""

        execution_engine = PaperExecutionEngine(self.session)
        portfolio_state = PositionManager(self.session).get_portfolio_state()
        risk_manager = RiskManager()
        if runtime_decision is not None:
            risk_result = risk_manager.validate_strategy_decision(runtime_decision, portfolio_state)
        else:
            risk_result = risk_manager.validate_decision(strategy_decision, portfolio_state)

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
            risk_result.final_action = "SELL"
            risk_result.reason = "Защитное закрытие позиции не требует отдельной риск-проверки."
            execution_action = protective_result.action
            execution_message = protective_result.message
        elif risk_result.approved:
            execution_decision = strategy_decision
            if risk_result.final_action != strategy_decision.decision.value:
                execution_decision = TradeDecision.build(
                    symbol=strategy_decision.symbol,
                    interval=strategy_decision.interval,
                    decision=DecisionType(risk_result.final_action),
                    reason=f"RiskManager переопределил действие: {risk_result.reason}",
                    regime=strategy_decision.regime,
                    price=strategy_decision.price,
                    created_at=strategy_decision.created_at,
                )
                final_decision = execution_decision

            try:
                execution_result = execution_engine.execute(
                    execution_decision,
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
                record = TradeJournal(self.session).record(
                    self._build_payload(
                        strategy_decision=strategy_decision,
                        final_decision=final_decision,
                        risk_approved=risk_result.approved,
                        risk_reason=risk_result.reason,
                        execution_action=execution_action,
                        execution_message=execution_message,
                        runtime_decision=runtime_decision,
                    )
                )
                return PaperStepResult(
                    strategy_decision=strategy_decision,
                    final_decision=final_decision,
                    risk_approved=risk_result.approved,
                    risk_reason=risk_result.reason,
                    execution_action=execution_action,
                    execution_message=execution_message,
                    has_execution_error=True,
                    journal_id=record.id,
                )
        else:
            final_decision = TradeDecision.build(
                symbol=strategy_decision.symbol,
                interval=strategy_decision.interval,
                decision=DecisionType(risk_result.final_action),
                reason=f"Решение отклонено RiskManager: {risk_result.reason}",
                regime=strategy_decision.regime,
                price=strategy_decision.price,
                created_at=strategy_decision.created_at,
            )
            execution_message = risk_result.reason

        record = TradeJournal(self.session).record(
            self._build_payload(
                strategy_decision=strategy_decision,
                final_decision=final_decision,
                risk_approved=risk_result.approved,
                risk_reason=risk_result.reason,
                execution_action=execution_action,
                execution_message=execution_message,
                runtime_decision=runtime_decision,
            )
        )

        return PaperStepResult(
            strategy_decision=strategy_decision,
            final_decision=final_decision,
            risk_approved=risk_result.approved,
            risk_reason=risk_result.reason,
            execution_action=execution_action,
            execution_message=execution_message,
            has_execution_error=False,
            journal_id=record.id,
        )

    @staticmethod
    def _build_payload(
        *,
        strategy_decision: TradeDecision,
        final_decision: TradeDecision,
        risk_approved: bool,
        risk_reason: str,
        execution_action: str,
        execution_message: str,
        runtime_decision: StrategyDecision | None,
    ) -> TradeJournalPayload:
        if runtime_decision is None:
            return TradeJournalPayload(
                strategy_decision=strategy_decision,
                final_decision=final_decision,
                risk_approved=risk_approved,
                risk_reason=risk_reason,
                execution_action=execution_action,
                execution_message=execution_message,
            )

        return TradeJournalPayload(
            strategy_decision=strategy_decision,
            final_decision=final_decision,
            risk_approved=risk_approved,
            risk_reason=risk_reason,
            execution_action=execution_action,
            execution_message=execution_message,
            strategy_name=runtime_decision.strategy_name,
            strategy_version=runtime_decision.strategy_version,
            confidence=runtime_decision.confidence,
        )
