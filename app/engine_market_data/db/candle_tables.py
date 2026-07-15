"""One physically separate, identical PostgreSQL table per supported timeframe."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.engine_market_data.db.base import Base


class CandleTableMixin:
    """Common closed-candle schema; subclasses only select a physical table."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    open_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    close_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Any] = mapped_column(Numeric(38, 18), nullable=False)
    high: Mapped[Any] = mapped_column(Numeric(38, 18), nullable=False)
    low: Mapped[Any] = mapped_column(Numeric(38, 18), nullable=False)
    close: Mapped[Any] = mapped_column(Numeric(38, 18), nullable=False)
    volume: Mapped[Any] = mapped_column(Numeric(38, 18), nullable=False)
    quote_volume: Mapped[Any | None] = mapped_column(Numeric(38, 18), nullable=True)
    trades_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    ingested_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    data_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    @declared_attr.directive
    def __table_args__(cls) -> tuple[object, ...]:
        table = cls.__tablename__
        return (
            UniqueConstraint("symbol", "open_time_ms", name=f"uq_{table}_symbol_open_ms"),
            Index(f"ix_{table}_symbol_open_ms", "symbol", "open_time_ms"),
            Index(f"ix_{table}_symbol_close_ms", "symbol", "close_time_ms"),
            Index(f"ix_{table}_symbol_open_utc", "symbol", "open_time_utc"),
            CheckConstraint("is_closed = true", name=f"ck_{table}_closed"),
            CheckConstraint("volume >= 0", name=f"ck_{table}_volume"),
            CheckConstraint("high >= open", name=f"ck_{table}_high_open"),
            CheckConstraint("high >= close", name=f"ck_{table}_high_close"),
            CheckConstraint("high >= low", name=f"ck_{table}_high_low"),
            CheckConstraint("low <= open", name=f"ck_{table}_low_open"),
            CheckConstraint("low <= close", name=f"ck_{table}_low_close"),
            CheckConstraint("low <= high", name=f"ck_{table}_low_high"),
        )


class Candle1m(CandleTableMixin, Base): __tablename__ = "candles_1m"
class Candle5m(CandleTableMixin, Base): __tablename__ = "candles_5m"
class Candle15m(CandleTableMixin, Base): __tablename__ = "candles_15m"
class Candle1h(CandleTableMixin, Base): __tablename__ = "candles_1h"
class Candle4h(CandleTableMixin, Base): __tablename__ = "candles_4h"
class Candle1d(CandleTableMixin, Base): __tablename__ = "candles_1d"


CANDLE_MODELS = {
    "1m": Candle1m, "5m": Candle5m, "15m": Candle15m,
    "1h": Candle1h, "4h": Candle4h, "1d": Candle1d,
}
