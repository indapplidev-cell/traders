"""ORM-модели базы данных."""

from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Candle(Base):
    """Историческая свеча рынка.

    Храним OHLCV в Decimal, чтобы не тащить float-ошибки в денежные расчёты
    и в построение торговых решений.
    """

    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "open_time", name="uq_candles_symbol_interval_open_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), index=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class PaperAccount(Base):
    """Виртуальный счёт paper trading.

    На первом этапе достаточно одного счёта в валюте USDT, но отдельная
    таблица позволяет позже расширить логику без глобальных переменных.
    """

    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class PaperPosition(Base):
    """Виртуальная позиция paper trading.

    Здесь добавлена DB-level защита от двух одновременно открытых позиций
    по одному symbol. Python-проверки полезны, но только уникальный индекс
    на стороне БД защищает от гонок и параллельных записей.
    """

    __tablename__ = "paper_positions"
    __table_args__ = (
        Index(
            "uq_paper_positions_one_open_per_symbol",
            "symbol",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
            sqlite_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), index=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class TradeDecisionRecord(Base):
    """Журнал торговых решений стратегии."""

    __tablename__ = "trade_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), index=True)
    strategy_name: Mapped[str] = mapped_column(String(64))
    strategy_version: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    strategy_decision: Mapped[str] = mapped_column(String(16))
    strategy_reason: Mapped[str] = mapped_column(String(512))
    final_decision: Mapped[str] = mapped_column(String(16))
    final_reason: Mapped[str] = mapped_column(String(512))
    regime: Mapped[str] = mapped_column(String(16))
    price: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    risk_approved: Mapped[bool] = mapped_column(Boolean())
    risk_reason: Mapped[str] = mapped_column(String(512))
    execution_action: Mapped[str] = mapped_column(String(16))
    execution_message: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class RunnerSession(Base):
    """Запуск bounded paper runner для серии runtime tick-ов."""

    __tablename__ = "runner_sessions"
    __table_args__ = (
        Index("ix_runner_sessions_strategy_name", "strategy_name"),
        Index("ix_runner_sessions_symbol", "symbol"),
        Index("ix_runner_sessions_status", "status"),
        Index("ix_runner_sessions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64))
    strategy_version: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    interval: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticks_requested: Mapped[int] = mapped_column()
    ticks_completed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class RuntimeTick(Base):
    """Аудит одного runtime tick внутри runner session."""

    __tablename__ = "runtime_ticks"
    __table_args__ = (
        UniqueConstraint("runner_session_id", "tick_number", name="uq_runtime_ticks_session_tick"),
        Index("ix_runtime_ticks_runner_session_id", "runner_session_id"),
        Index("ix_runtime_ticks_symbol", "symbol"),
        Index("ix_runtime_ticks_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    runner_session_id: Mapped[int] = mapped_column(ForeignKey("runner_sessions.id", ondelete="CASCADE"))
    tick_number: Mapped[int] = mapped_column()
    symbol: Mapped[str] = mapped_column(String(32))
    interval: Mapped[str] = mapped_column(String(16))
    strategy_action: Mapped[str] = mapped_column(String(16))
    final_action: Mapped[str] = mapped_column(String(16))
    risk_approved: Mapped[bool] = mapped_column(Boolean())
    risk_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    execution_action: Mapped[str] = mapped_column(String(16))
    journal_id: Mapped[int | None] = mapped_column(nullable=True)
    market_regime: Mapped[str | None] = mapped_column(String(16), nullable=True)
    candles_used: Mapped[int | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class PaperRunnerState(Base):
    """Состояние paper-runner для защиты от повторной обработки одной свечи."""

    __tablename__ = "paper_runner_state"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", name="uq_paper_runner_state_symbol_interval"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16), index=True)
    last_processed_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
