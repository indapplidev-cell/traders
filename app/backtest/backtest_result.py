"""Структуры результата backtest."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class BacktestTrade:
    """Одна закрытая сделка внутри backtest."""

    symbol: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    exit_action: str
    opened_at: datetime
    closed_at: datetime


@dataclass(slots=True)
class BacktestResult:
    """Сводный итог backtest по одному symbol/interval."""

    symbol: str
    interval: str
    candles_used: int
    initial_balance: Decimal
    final_balance: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    winrate_pct: Decimal
    max_drawdown_pct: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    trades: list[BacktestTrade] = field(default_factory=list)

