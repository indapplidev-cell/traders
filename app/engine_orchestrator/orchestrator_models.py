"""SQLAlchemy persistence models for compact online pipeline records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.engine_market_data.db.base import Base


class ClosedWindow:
    """Small immutable trigger value without candle payloads."""

    __slots__ = ("symbol", "timeframe", "closed_until_ms")

    def __init__(self, symbol: str, timeframe: str, closed_until_ms: int) -> None:
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.closed_until_ms = int(closed_until_ms)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ClosedWindow) and (
            self.symbol, self.timeframe, self.closed_until_ms
        ) == (other.symbol, other.timeframe, other.closed_until_ms)

    def __hash__(self) -> int:
        return hash((self.symbol, self.timeframe, self.closed_until_ms))


class OnlinePipelineRun(Base):
    __tablename__ = "online_pipeline_runs"
    __table_args__ = (
        UniqueConstraint("trade_profile_id", "symbol", "primary_timeframe", "closed_until_ms", name="uq_online_pipeline_profile_window"),
        CheckConstraint("status IN ('PENDING','RESERVED','CHECKING_FRESHNESS','WAITING_FOR_REQUIRED_BOUNDARY','READY_TO_RUN','RUNNING','COMPLETED','SKIPPED_DUPLICATE_WINDOW','SKIPPED_FRESHNESS_NOT_OK','SKIPPED_FRESHNESS_TIMEOUT','SKIPPED_NOT_ENOUGH_DATA','MODULE_ERROR','ERROR')", name="ck_online_pipeline_run_status"),
        Index("ix_online_pipeline_runs_status_next_retry", "status", "next_retry_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    trade_profile_id: Mapped[str] = mapped_column(String(32), default="trade-15m-v1", server_default="trade-15m-v1", nullable=False)
    profile_mode: Mapped[str] = mapped_column(String(32), default="PRODUCTION_SEARCH", server_default="PRODUCTION_SEARCH", nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closed_until_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    trigger_source: Mapped[str] = mapped_column(String(50), nullable=False)
    daemon_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    market_data_freshness_status: Mapped[str | None] = mapped_column(String(40))
    freshness_attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    first_freshness_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_freshness_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_wait_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiting_reason_code: Mapped[str | None] = mapped_column(String(100))
    waiting_timeframes: Mapped[list[str] | None] = mapped_column(JSON)
    last_freshness_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    freshness_recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_status: Mapped[str | None] = mapped_column(String(60))
    setup_status: Mapped[str | None] = mapped_column(String(60))
    strategy_status: Mapped[str | None] = mapped_column(String(60))
    risk_status: Mapped[str | None] = mapped_column(String(60))
    paper_status: Mapped[str | None] = mapped_column(String(60))
    final_result: Mapped[str | None] = mapped_column(String(40))
    final_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    future_bars_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_trade_signal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_executable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    order_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    execution_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    position_opened: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    position_size_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OnlinePipelineResultRow(Base):
    __tablename__ = "online_pipeline_results"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("online_pipeline_runs.run_id", ondelete="CASCADE"), unique=True, nullable=False)
    trade_profile_id: Mapped[str] = mapped_column(String(32), default="trade-15m-v1", server_default="trade-15m-v1", nullable=False)
    profile_mode: Mapped[str] = mapped_column(String(32), default="PRODUCTION_SEARCH", server_default="PRODUCTION_SEARCH", nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    closed_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    market_data_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    analysis_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    setup_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    strategy_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    risk_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    paper_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    module_reasons_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    module_warnings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    safety_counters_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
