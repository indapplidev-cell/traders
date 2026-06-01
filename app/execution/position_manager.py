"""Утилиты для чтения и обновления paper-портфеля."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import PaperAccount, PaperPosition, PaperRunnerState


@dataclass(slots=True)
class PaperPortfolioState:
    """Снимок paper-портфеля для риск-проверок и CLI."""

    balance_usdt: Decimal
    open_positions: list[PaperPosition]
    realized_pnl: Decimal


class PositionManager:
    """Работает с состоянием paper-счёта и позиций."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def ensure_account(self) -> PaperAccount:
        """Создаёт paper-счёт USDT при первом обращении."""

        account = self.session.execute(
            select(PaperAccount).where(PaperAccount.currency == "USDT")
        ).scalar_one_or_none()
        if account is None:
            account = PaperAccount(
                currency="USDT",
                balance=self.settings.paper_initial_balance_usdt,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.session.add(account)
            self.session.flush()
        return account

    def get_open_positions(self) -> list[PaperPosition]:
        """Возвращает все открытые позиции."""

        statement: Select[tuple[PaperPosition]] = select(PaperPosition).where(PaperPosition.status == "OPEN")
        return list(self.session.execute(statement).scalars().all())

    def get_open_position_by_symbol(self, symbol: str) -> PaperPosition | None:
        """Возвращает открытую позицию по конкретному символу."""

        return self.session.execute(
            select(PaperPosition).where(
                PaperPosition.symbol == symbol.upper(),
                PaperPosition.status == "OPEN",
            )
        ).scalar_one_or_none()

    def get_or_create_runner_state(self, symbol: str, interval: str) -> PaperRunnerState:
        """Возвращает или создаёт состояние paper-runner по symbol/interval."""

        state = self.session.execute(
            select(PaperRunnerState).where(
                PaperRunnerState.symbol == symbol.upper(),
                PaperRunnerState.interval == interval,
            )
        ).scalar_one_or_none()
        if state is None:
            state = PaperRunnerState(
                symbol=symbol.upper(),
                interval=interval,
                last_processed_open_time=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.session.add(state)
            self.session.flush()
        return state

    def get_realized_pnl(self) -> Decimal:
        """Суммирует прибыль и убыток по закрытым позициям."""

        value = self.session.execute(
            select(func.coalesce(func.sum(PaperPosition.realized_pnl), 0)).where(PaperPosition.status == "CLOSED")
        ).scalar_one()
        return Decimal(str(value))

    def get_portfolio_state(self) -> PaperPortfolioState:
        """Собирает снимок текущего портфеля."""

        account = self.ensure_account()
        return PaperPortfolioState(
            balance_usdt=Decimal(str(account.balance)),
            open_positions=self.get_open_positions(),
            realized_pnl=self.get_realized_pnl(),
        )
