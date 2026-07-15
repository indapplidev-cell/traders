"""Persistent state schema and immutable operational status contracts."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.engine_market_data.db.base import Base


class ContinuousSyncStatus(StrEnum):
    OK = "OK"
    STALE = "STALE"
    GAP_DETECTED = "GAP_DETECTED"
    RECOVERING = "RECOVERING"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    NOT_CONFIGURED = "NOT_CONFIGURED"


ALLOWED_SYNC_STATUSES = tuple(value.value for value in ContinuousSyncStatus)


class MarketDataSyncState(Base):
    __tablename__ = "market_data_sync_state"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", name="uq_market_data_sync_state_symbol_timeframe"),
        CheckConstraint("status IN ('OK','STALE','GAP_DETECTED','RECOVERING','DEGRADED','DISCONNECTED','ERROR','NOT_CONFIGURED')",
                        name="ck_market_data_sync_state_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    last_expected_open_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_expected_close_boundary_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_stored_open_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    last_stored_close_boundary_ms: Mapped[int | None] = mapped_column(BigInteger)
    freshness_lag_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    freshness_lag_candles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_CONFIGURED")
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    recovering_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    last_inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="binance_public_rest")
    daemon_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


@dataclass(slots=True)
class SyncStateUpdate:
    symbol: str
    timeframe: str
    daemon_instance_id: str
    status: str = ContinuousSyncStatus.NOT_CONFIGURED
    last_expected_open_time_ms: int | None = None
    last_expected_close_boundary_ms: int | None = None
    last_stored_open_time_ms: int | None = None
    last_stored_close_boundary_ms: int | None = None
    freshness_lag_ms: int = 0
    freshness_lag_candles: int = 0
    missing_count: int = 0
    recovering_count: int = 0
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    last_inserted_count: int = 0
    last_updated_count: int = 0
    last_skipped_count: int = 0
    last_failed_count: int = 0
    source: str = "binance_public_rest"

    def __post_init__(self) -> None:
        if str(self.status) not in ALLOWED_SYNC_STATUSES:
            raise ValueError("unsupported sync status")
        for value in (self.last_attempt_at, self.last_success_at, self.last_error_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("sync state timestamps must be timezone-aware UTC")

    def values(self) -> dict[str, Any]:
        values = asdict(self)
        values["status"] = str(self.status)
        return values
