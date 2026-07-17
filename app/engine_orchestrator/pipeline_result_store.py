"""Transactional reservation and compact result persistence."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.orchestrator_status import PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult, json_safe


def utc_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


class PipelineResultStore:
    def __init__(self, session_or_factory: Session | Callable[[], Session], *,
                 stale_run_after_seconds: int = 300) -> None:
        if stale_run_after_seconds < 1:
            raise ValueError("stale_run_after_seconds must be positive")
        self._session_or_factory = session_or_factory
        self.stale_run_after_seconds = stale_run_after_seconds

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._session_or_factory, Session):
            yield self._session_or_factory
            return
        with self._session_or_factory() as session:
            yield session

    def has_window(self, symbol: str, timeframe: str, closed_until_ms: int) -> bool:
        query = select(OnlinePipelineRun).where(
            OnlinePipelineRun.symbol == symbol.upper(),
            OnlinePipelineRun.primary_timeframe == timeframe,
            OnlinePipelineRun.closed_until_ms == int(closed_until_ms),
        ).limit(1)
        with self._session() as session:
            row = session.scalar(query)
            if row is None:
                return False
            if row.status not in {PipelineStatus.PENDING.value, PipelineStatus.RUNNING.value}:
                return True
            started = row.started_at
            if started is None:
                return False
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return started > datetime.now(timezone.utc) - timedelta(seconds=self.stale_run_after_seconds)

    def reserve(self, symbol: str, timeframe: str, closed_until_ms: int, *,
                daemon_instance_id: str, trigger_source: str) -> str | None:
        run_id = f"orchestrator:{uuid4().hex}"
        now = datetime.now(timezone.utc)
        row = OnlinePipelineRun(
            run_id=run_id, symbol=symbol.upper(), primary_timeframe=timeframe,
            closed_until_ms=int(closed_until_ms), closed_until_utc=utc_from_ms(closed_until_ms),
            status=PipelineStatus.RUNNING.value, started_at=now,
            trigger_source=trigger_source, daemon_instance_id=daemon_instance_id,
        )
        with self._session() as session:
            try:
                session.add(row)
                session.commit()
                return run_id
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(OnlinePipelineRun).where(
                    OnlinePipelineRun.symbol == symbol.upper(),
                    OnlinePipelineRun.primary_timeframe == timeframe,
                    OnlinePipelineRun.closed_until_ms == int(closed_until_ms),
                ))
                if existing is None or existing.status not in {
                    PipelineStatus.PENDING.value, PipelineStatus.RUNNING.value,
                }:
                    return None
                started = existing.started_at
                if started is not None and started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                cutoff = now - timedelta(seconds=self.stale_run_after_seconds)
                if started is not None and started > cutoff:
                    return None
                existing.status = PipelineStatus.RUNNING.value
                existing.started_at = now
                existing.finished_at = None
                existing.duration_ms = None
                existing.daemon_instance_id = daemon_instance_id
                existing.error_code = None
                existing.error_message = None
                session.commit()
                return existing.run_id

    def finish(self, run_id: str, result: PipelineResult, *, freshness_status: str) -> None:
        now = datetime.now(timezone.utc)
        with self._session() as session:
            run = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == run_id))
            if run is None:
                raise KeyError(f"unknown run_id {run_id}")
            run.status = result.status
            run.finished_at = now
            started = run.started_at or now
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            run.duration_ms = max(0, int((now - started).total_seconds() * 1000))
            run.market_data_freshness_status = freshness_status
            run.analysis_status = result.analysis_status
            run.setup_status = result.setup_status
            run.strategy_status = result.strategy_status
            run.risk_status = result.risk_status
            run.paper_status = result.paper_status
            run.final_result = result.final_result
            run.final_reason = result.final_reason
            run.error_code = result.error_code
            run.error_message = result.error_message
            counters = result.safety_counters
            run.future_bars_used = counters.future_bars_used_count > 0
            run.is_trade_signal = counters.trade_signal_count > 0
            run.is_executable = counters.is_executable_count > 0
            run.order_approved = counters.order_approved_count > 0
            run.execution_approved = counters.execution_approved_count > 0
            run.position_opened = counters.position_opened_count > 0
            run.position_size_approved = counters.position_size_approved_count > 0
            row = OnlinePipelineResultRow(
                run_id=run_id, symbol=result.symbol, primary_timeframe=result.primary_timeframe,
                closed_until_ms=result.closed_until_ms,
                market_data_payload_json=json_safe(result.market_data_payload),
                analysis_payload_json=json_safe(result.analysis_payload),
                setup_payload_json=json_safe(result.setup_payload),
                strategy_payload_json=json_safe(result.strategy_payload),
                risk_payload_json=json_safe(result.risk_payload),
                paper_payload_json=json_safe(result.paper_payload),
                module_reasons_json=json_safe(result.module_reasons),
                module_warnings_json=json_safe(result.module_warnings),
                safety_counters_json=json_safe(result.safety_counters),
            )
            session.add(row)
            session.commit()

    def get_latest(self, symbol: str, timeframe: str) -> OnlinePipelineRun | None:
        query = select(OnlinePipelineRun).where(
            OnlinePipelineRun.symbol == symbol.upper(),
            OnlinePipelineRun.primary_timeframe == timeframe,
        ).order_by(OnlinePipelineRun.closed_until_ms.desc()).limit(1)
        with self._session() as session:
            return session.scalar(query)

    def count(self, symbol: str | None = None) -> int:
        query = select(OnlinePipelineRun)
        if symbol is not None:
            query = query.where(OnlinePipelineRun.symbol == symbol.upper())
        with self._session() as session:
            return len(list(session.scalars(query)))

    def safety_totals(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        with self._session() as session:
            payloads = list(session.scalars(select(OnlinePipelineResultRow.safety_counters_json)))
        for payload in payloads:
            for name, value in dict(payload or {}).items():
                totals[name] = totals.get(name, 0) + int(value or 0)
        return totals
