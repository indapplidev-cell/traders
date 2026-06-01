"""Изолированное состояние портфеля для backtest без записи в paper-таблицы."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from types import SimpleNamespace

from app.backtest.backtest_result import BacktestTrade
from app.config.settings import Settings
from app.execution.protective_levels import ProtectiveLevels, calculate_long_protective_levels


@dataclass(slots=True)
class BacktestPosition:
    """Открытая позиция внутри backtest, не связанная с БД paper trading."""

    symbol: str
    entry_price: Decimal
    quantity: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    opened_at: datetime


@dataclass(slots=True)
class BacktestPortfolioState:
    """Минимальное состояние портфеля для reuse в RiskManager и метриках."""

    balance_usdt: Decimal
    open_positions: list[object]
    realized_pnl: Decimal


class BacktestPortfolio:
    """Держит отдельный in-memory портфель для backtest."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.initial_balance = settings.paper_initial_balance_usdt
        self.balance = settings.paper_initial_balance_usdt
        self.realized_pnl = Decimal("0")
        self.open_position: BacktestPosition | None = None
        self.closed_trades: list[BacktestTrade] = []

    def build_risk_state(self) -> BacktestPortfolioState:
        """Возвращает компактное состояние для RiskManager."""

        open_positions = []
        if self.open_position is not None:
            open_positions.append(SimpleNamespace(symbol=self.open_position.symbol))
        return BacktestPortfolioState(
            balance_usdt=self.balance,
            open_positions=open_positions,
            realized_pnl=self.realized_pnl,
        )

    def open_long(
        self,
        *,
        symbol: str,
        entry_price: Decimal,
        atr_14: Decimal,
        opened_at: datetime,
    ) -> BacktestPosition | None:
        """Открывает long-позицию, если ATR позволяет построить защитные уровни."""

        protective_levels = self._build_protective_levels(entry_price=entry_price, atr_14=atr_14)
        if protective_levels is None:
            return None

        position_notional = (
            self.balance * self.settings.paper_position_size_fraction
        ).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        quantity = (position_notional / entry_price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        if quantity <= 0 or position_notional <= 0:
            return None

        self.balance -= position_notional
        self.open_position = BacktestPosition(
            symbol=symbol.upper(),
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=protective_levels.stop_loss,
            take_profit=protective_levels.take_profit,
            opened_at=opened_at,
        )
        return self.open_position

    def close_position(self, *, exit_price: Decimal, exit_action: str, closed_at: datetime) -> None:
        """Закрывает текущую позицию и обновляет баланс плюс realized PnL."""

        if self.open_position is None:
            return

        position = self.open_position
        proceeds = (position.quantity * exit_price).quantize(Decimal("0.00000001"))
        entry_notional = (position.quantity * position.entry_price).quantize(Decimal("0.00000001"))
        pnl = proceeds - entry_notional

        self.closed_trades.append(
            BacktestTrade(
                symbol=position.symbol,
                entry_price=position.entry_price,
                exit_price=exit_price,
                quantity=position.quantity,
                pnl=pnl,
                exit_action=exit_action,
                opened_at=position.opened_at,
                closed_at=closed_at,
            )
        )
        self.balance += proceeds
        self.realized_pnl += pnl
        self.open_position = None

    def mark_to_market(self, *, close_price: Decimal) -> Decimal:
        """Считает текущую стоимость портфеля с учётом открытой позиции."""

        if self.open_position is None:
            return self.balance
        return self.balance + (self.open_position.quantity * close_price).quantize(Decimal("0.00000001"))

    @staticmethod
    def _build_protective_levels(*, entry_price: Decimal, atr_14: Decimal) -> ProtectiveLevels | None:
        """Безопасно строит SL/TP и не роняет backtest при отсутствующем ATR."""

        try:
            return calculate_long_protective_levels(entry_price, atr_14)
        except ValueError:
            return None
