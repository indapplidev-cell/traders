from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.db.models import PaperPosition


def build_open_position(symbol: str = "BTCUSDT") -> PaperPosition:
    """Создаёт тестовую OPEN-позицию."""

    now = datetime.now(UTC)
    return PaperPosition(
        symbol=symbol,
        side="LONG",
        status="OPEN",
        entry_price=Decimal("100"),
        quantity=Decimal("0.1"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("120"),
        opened_at=now,
        closed_at=None,
        close_price=None,
        realized_pnl=None,
        created_at=now,
        updated_at=now,
    )


def test_partial_unique_index_exists_for_one_open_position(sqlite_session) -> None:
    """Проверяет наличие partial unique index в metadata/SQLite."""

    indexes = inspect(sqlite_session.bind).get_indexes("paper_positions")
    index_names = {item["name"] for item in indexes}
    assert "uq_paper_positions_one_open_per_symbol" in index_names


def test_cannot_create_two_open_positions_for_same_symbol(sqlite_session) -> None:
    """Проверяет DB-level защиту от двух OPEN-позиций по одному symbol."""

    sqlite_session.add(build_open_position())
    sqlite_session.flush()

    sqlite_session.add(build_open_position())
    with pytest.raises(IntegrityError):
        sqlite_session.flush()
    sqlite_session.rollback()


def test_can_open_new_position_after_previous_is_closed(sqlite_session) -> None:
    """Проверяет, что CLOSED-позиция не блокирует новую OPEN-позицию."""

    first = build_open_position()
    sqlite_session.add(first)
    sqlite_session.flush()

    first.status = "CLOSED"
    first.closed_at = datetime.now(UTC)
    first.close_price = Decimal("105")
    first.realized_pnl = Decimal("0.5")
    sqlite_session.flush()

    sqlite_session.add(build_open_position())
    sqlite_session.flush()

    open_positions = sqlite_session.execute(
        select(PaperPosition).where(PaperPosition.symbol == "BTCUSDT", PaperPosition.status == "OPEN")
    ).scalars().all()
    assert len(open_positions) == 1

