"""Виртуальное исполнение paper-сделок."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import Candle, PaperPosition
from app.execution.position_manager import PositionManager
from app.execution.protective_levels import calculate_long_protective_levels, detect_long_protective_exit
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


@dataclass(slots=True)
class ExecutionResult:
    """Результат виртуального исполнения решения."""

    action: str
    message: str
    price: Decimal | None = None


class PaperExecutionEngine:
    """Исполняет торговые решения только в безопасном paper-режиме."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.position_manager = PositionManager(session)

    def execute(
        self,
        decision: TradeDecision,
        *,
        indicator_snapshot: IndicatorSnapshot | None = None,
    ) -> ExecutionResult:
        """Исполняет BUY / SELL / HOLD без реальных ордеров."""

        if decision.decision == DecisionType.HOLD:
            return ExecutionResult(action="HOLD", message="Сделка не выполнялась: стратегия вернула HOLD.", price=None)
        if decision.decision == DecisionType.BUY:
            return self._open_long(decision, indicator_snapshot=indicator_snapshot)
        if decision.decision == DecisionType.SELL:
            return self._close_long(decision)
        raise ValueError("Получен неподдерживаемый тип торгового решения.")

    def _open_long(
        self,
        decision: TradeDecision,
        *,
        indicator_snapshot: IndicatorSnapshot | None,
    ) -> ExecutionResult:
        """Открывает виртуальную LONG-позицию.

        На первом этапе short-исполнение запрещено, поэтому engine умеет
        только покупку спота и последующее закрытие этой позиции.
        """

        if self.position_manager.get_open_position_by_symbol(decision.symbol) is not None:
            raise ValueError("Нельзя открыть позицию: по символу уже есть открытая LONG-позиция.")

        account = self.position_manager.ensure_account()
        notional = (account.balance * self.settings.paper_position_size_fraction).quantize(
            Decimal("0.00000001"),
            rounding=ROUND_DOWN,
        )
        if notional <= 0:
            raise ValueError("Нельзя открыть позицию: расчётный объём сделки получился нулевым.")

        quantity = (notional / decision.price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        if quantity <= 0:
            raise ValueError("Нельзя открыть позицию: расчётное количество актива получилось нулевым.")

        atr_14 = indicator_snapshot.atr_14 if indicator_snapshot is not None else None
        protective_levels = calculate_long_protective_levels(decision.price, atr_14)

        account.balance = Decimal(str(account.balance)) - notional
        account.updated_at = datetime.now(UTC)

        position = PaperPosition(
            symbol=decision.symbol,
            side="LONG",
            status="OPEN",
            entry_price=decision.price,
            quantity=quantity,
            stop_loss=protective_levels.stop_loss,
            take_profit=protective_levels.take_profit,
            opened_at=decision.created_at,
            closed_at=None,
            close_price=None,
            realized_pnl=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        try:
            self.session.add(position)
            self.session.flush()
        except IntegrityError as exc:
            raise ValueError(
                "Нельзя открыть позицию: БД отклонила вторую открытую позицию по тому же symbol."
            ) from exc

        return ExecutionResult(
            action="BUY",
            message=(
                f"Открыта LONG-позиция: quantity={quantity}, entry_price={decision.price}, "
                f"stop_loss={protective_levels.stop_loss}, take_profit={protective_levels.take_profit}."
            ),
            price=decision.price,
        )

    def _close_long(self, decision: TradeDecision, *, execution_action: str = "SELL") -> ExecutionResult:
        """Закрывает открытую LONG-позицию по символу."""

        position = self.position_manager.get_open_position_by_symbol(decision.symbol)
        if position is None:
            raise ValueError("Нельзя закрыть позицию: открытая LONG-позиция не найдена.")

        account = self.position_manager.ensure_account()
        proceeds = (Decimal(str(position.quantity)) * decision.price).quantize(Decimal("0.00000001"))
        entry_notional = (Decimal(str(position.quantity)) * Decimal(str(position.entry_price))).quantize(
            Decimal("0.00000001")
        )
        realized_pnl = proceeds - entry_notional

        position.status = "CLOSED"
        position.closed_at = decision.created_at
        position.close_price = decision.price
        position.realized_pnl = realized_pnl
        position.updated_at = datetime.now(UTC)

        account.balance = Decimal(str(account.balance)) + proceeds
        account.updated_at = datetime.now(UTC)

        if execution_action == "STOP_LOSS":
            message = f"Позиция закрыта по stop-loss: quantity={position.quantity}, close_price={decision.price}, pnl={realized_pnl}."
        elif execution_action == "TAKE_PROFIT":
            message = (
                f"Позиция закрыта по take-profit: quantity={position.quantity}, close_price={decision.price}, "
                f"pnl={realized_pnl}."
            )
        else:
            message = f"Позиция закрыта: quantity={position.quantity}, close_price={decision.price}, pnl={realized_pnl}."

        return ExecutionResult(
            action=execution_action,
            message=message,
            price=decision.price,
        )

    def check_protective_exit(self, symbol: str, candle: Candle) -> ExecutionResult | None:
        """Проверяет, не достигла ли закрытая свеча защитных уровней позиции."""

        position = self.position_manager.get_open_position_by_symbol(symbol)
        if position is None:
            return None

        exit_match = detect_long_protective_exit(
            candle=candle,
            stop_loss=Decimal(str(position.stop_loss)) if position.stop_loss is not None else None,
            take_profit=Decimal(str(position.take_profit)) if position.take_profit is not None else None,
        )
        if exit_match is None:
            return None

        action, exit_price = exit_match
        return self._close_long(
            TradeDecision.build(
                symbol=symbol,
                interval=candle.interval,
                decision=DecisionType.SELL,
                reason=(
                    "Позиция закрыта автоматически по stop-loss."
                    if action == "STOP_LOSS"
                    else "Позиция закрыта автоматически по take-profit."
                ),
                regime=MarketRegime.UNKNOWN,
                price=exit_price,
                created_at=candle.close_time,
            ),
            execution_action=action,
        )
