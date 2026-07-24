"""Read-only SQLAlchemy projection over existing persisted engine state.

The adapter is deliberately inert until a repository method is called. A
Session or session factory is always injected by a future composition root.
Only SQLAlchemy SELECT statements are constructed here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.engine_market_data.db.candle_tables import CANDLE_MODELS
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.server_api.repositories.records import (
    AnalysisRecord,
    HealthRecord,
    IncidentQuery,
    IncidentRecord,
    MarketRecord,
    RecordPage,
    RunRecord,
    ServiceRecord,
    SetupQuery,
    SetupRecord,
)


ANOMALOUS_RUN_STATUSES = (
    "SKIPPED_FRESHNESS_NOT_OK",
    "SKIPPED_FRESHNESS_TIMEOUT",
    "MODULE_ERROR",
    "ERROR",
)


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if isinstance(item, (str, int)))


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _score(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if 0 <= result <= 1 else None


def _health(value: Any) -> str:
    normalized = str(value or "").upper()
    if normalized in {"OK", "READY"}:
        return "OK"
    if normalized in {"STALE", "DEGRADED", "NOT_AVAILABLE", "ERROR", "OFFLINE"}:
        return normalized
    if normalized in {"GAP_DETECTED", "WAITING_RETRYABLE"}:
        return "DEGRADED"
    return "UNKNOWN"


def _direction(value: Any) -> str:
    normalized = str(value or "").upper()
    return normalized if normalized in {
        "BULLISH", "BEARISH", "NEUTRAL", "NONE", "NOT_APPLICABLE"
    } else "UNKNOWN"


class SqlAlchemyReadAdapter:
    """Implements API read protocols using existing candle/run/result tables."""

    def __init__(
        self,
        session_or_factory: Session | Callable[[], Session],
        *,
        primary_timeframe: str = "15m",
    ) -> None:
        if primary_timeframe not in CANDLE_MODELS:
            raise ValueError("unsupported primary timeframe")
        self._session_or_factory = session_or_factory
        self._primary_timeframe = primary_timeframe

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._session_or_factory, Session):
            yield self._session_or_factory
            return
        with self._session_or_factory() as session:
            yield session

    def _latest_bundle(self, symbol: str) -> tuple[OnlinePipelineRun | None, OnlinePipelineResultRow | None]:
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .outerjoin(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
            .where(OnlinePipelineRun.symbol == symbol.upper())
            .order_by(OnlinePipelineRun.closed_until_ms.desc(), OnlinePipelineRun.run_id.desc())
            .limit(1)
        )
        with self._session() as session:
            row = session.execute(statement).first()
        return (row[0], row[1]) if row else (None, None)

    def _latest_candle(self, symbol: str):
        model = CANDLE_MODELS[self._primary_timeframe]
        statement = (
            select(model)
            .where(model.symbol == symbol.upper(), model.is_closed.is_(True))
            .order_by(model.close_time_ms.desc())
            .limit(1)
        )
        with self._session() as session:
            return session.scalar(statement)

    def _market_record(self, symbol: str) -> MarketRecord | None:
        run, result = self._latest_bundle(symbol)
        candle = self._latest_candle(symbol)
        if run is None and candle is None:
            return None
        analysis = _mapping(result.analysis_payload_json) if result is not None else {}
        setup = _mapping(result.setup_payload_json) if result is not None else {}
        risk = _mapping(result.risk_payload_json) if result is not None else {}
        market = _mapping(result.market_data_payload_json) if result is not None else {}
        timeframe_market = _mapping(market.get(self._primary_timeframe))
        updated_at = _aware(
            run.updated_at if run is not None else getattr(candle, "updated_at_utc", None)
        )
        boundary_ms = int(candle.close_time_ms) + 1 if candle is not None else int(run.closed_until_ms)
        status_source = run.market_data_freshness_status if run is not None else None
        if status_source is None and candle is not None:
            status_source = "UNKNOWN"
        return MarketRecord(
            symbol=symbol.upper(),
            status=_health(status_source),
            updated_at=updated_at,
            timeframe=self._primary_timeframe,
            latest_price=_decimal(getattr(candle, "close", None)),
            closed_until_ms=boundary_ms,
            regime=str(analysis.get("regime")) if analysis.get("regime") is not None else None,
            setup_status=str(setup.get("status") or "UNKNOWN"),
            risk_status=str(risk.get("risk_status")) if risk.get("risk_status") is not None else None,
            open=_decimal(getattr(candle, "open", None)),
            high=_decimal(getattr(candle, "high", None)),
            low=_decimal(getattr(candle, "low", None)),
            close=_decimal(getattr(candle, "close", None)),
            volume=_decimal(getattr(candle, "volume", None)),
            has_gaps=timeframe_market.get("has_gaps") if isinstance(timeframe_market.get("has_gaps"), bool) else None,
            enough_data=timeframe_market.get("enough_data") if isinstance(timeframe_market.get("enough_data"), bool) else None,
            future_bars_used=bool(run.future_bars_used) if run is not None else False,
        )

    def list_markets(self) -> tuple[MarketRecord, ...]:
        model = CANDLE_MODELS[self._primary_timeframe]
        statement = select(model.symbol).where(model.is_closed.is_(True)).distinct().order_by(model.symbol.asc())
        with self._session() as session:
            symbols = tuple(str(value) for value in session.scalars(statement))
        return tuple(item for symbol in symbols if (item := self._market_record(symbol)) is not None)

    def get_market(self, symbol: str) -> MarketRecord | None:
        return self._market_record(symbol)

    def get_analysis(self, symbol: str) -> AnalysisRecord | None:
        run, result = self._latest_bundle(symbol)
        if run is None or result is None:
            return None
        payload = _mapping(result.analysis_payload_json)
        if not payload:
            return None
        return AnalysisRecord(
            analysis_id=str(payload.get("snapshot_id") or f"analysis:{run.run_id}"),
            symbol=run.symbol,
            timeframe=str(payload.get("timeframe") or run.primary_timeframe),
            closed_until_ms=int(run.closed_until_ms),
            status=str(payload.get("status") or run.analysis_status or "UNKNOWN"),
            market_data_status=_health(payload.get("market_data_health") or run.market_data_freshness_status),
            updated_at=_aware(run.updated_at),
            regime=str(payload.get("regime")) if payload.get("regime") is not None else None,
            direction=_direction(payload.get("direction") or payload.get("action")),
            confidence=_score(payload.get("confidence")),
            impulse_phase=str(payload.get("impulse_phase")) if payload.get("impulse_phase") is not None else None,
            entry_quality=str(payload.get("entry_quality")) if payload.get("entry_quality") is not None else None,
            reason_codes=_sequence(payload.get("reason_codes")),
        )

    @staticmethod
    def _setup_record(run: OnlinePipelineRun, result: OnlinePipelineResultRow) -> SetupRecord | None:
        setup = _mapping(result.setup_payload_json)
        if not setup:
            return None
        strategy = _mapping(result.strategy_payload_json)
        risk = _mapping(result.risk_payload_json)
        paper = _mapping(result.paper_payload_json)
        setup_id = str(setup.get("setup_id") or "")
        if not setup_id:
            return None
        return SetupRecord(
            setup_id=setup_id,
            symbol=run.symbol,
            timeframe=str(setup.get("timeframe") or run.primary_timeframe),
            closed_until_ms=int(run.closed_until_ms),
            status=str(setup.get("status") or "UNKNOWN"),
            setup_type=str(setup.get("setup_type") or "UNKNOWN"),
            direction=_direction(setup.get("direction_hint")),
            quality=str(setup.get("setup_quality") or "UNKNOWN"),
            quality_score=_score(setup.get("quality_score")),
            updated_at=_aware(run.updated_at),
            confirmation_state=str(setup.get("confirmation_state") or "NOT_APPLICABLE"),
            reason_codes=_sequence(setup.get("reason_codes")),
            warnings=_sequence(setup.get("quality_warnings")),
            invalidation_reasons=_sequence(setup.get("invalidation_reasons")),
            strategy_status=str(strategy.get("decision_status")) if strategy.get("decision_status") is not None else run.strategy_status,
            risk_status=str(risk.get("risk_status")) if risk.get("risk_status") is not None else run.risk_status,
            paper_status=str(paper.get("paper_status")) if paper.get("paper_status") is not None else run.paper_status,
            hypothetical_entry=_decimal(paper.get("hypothetical_entry_reference")),
            hypothetical_stop=_decimal(paper.get("hypothetical_stop_level")),
            hypothetical_target=_decimal(paper.get("hypothetical_target_level")),
            planned_rr=_decimal(paper.get("planned_rr")),
            executable=False,
        )

    def _setup_rows(self, query: SetupQuery | None = None, *, scan_limit: int = 5000):
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .join(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
        )
        if query is not None:
            if query.symbol:
                statement = statement.where(OnlinePipelineRun.symbol == query.symbol.upper())
            if query.from_at:
                statement = statement.where(OnlinePipelineRun.updated_at >= query.from_at)
            if query.to_at:
                statement = statement.where(OnlinePipelineRun.updated_at < query.to_at)
            if query.cursor:
                statement = statement.where(OnlinePipelineRun.updated_at <= query.cursor.updated_at)
        statement = statement.order_by(
            OnlinePipelineRun.updated_at.desc(), OnlinePipelineRun.run_id.desc()
        ).limit(scan_limit)
        with self._session() as session:
            return tuple(session.execute(statement))

    def list_setups(self, query: SetupQuery) -> RecordPage:
        records = [
            item
            for run, result in self._setup_rows(query, scan_limit=max(1000, query.limit * 10))
            if (item := self._setup_record(run, result)) is not None
        ]
        if query.status:
            records = [item for item in records if item.status == query.status]
        records.sort(key=lambda item: (item.updated_at, item.setup_id), reverse=True)
        if query.cursor:
            anchor = (query.cursor.updated_at, query.cursor.identifier)
            records = [item for item in records if (item.updated_at, item.setup_id) < anchor]
        selected = records[: query.limit + 1]
        return RecordPage(tuple(selected[: query.limit]), len(selected) > query.limit)

    def get_setup(self, setup_id: str) -> SetupRecord | None:
        for run, result in self._setup_rows(scan_limit=5000):
            record = self._setup_record(run, result)
            if record is not None and record.setup_id == setup_id:
                return record
        return None

    @staticmethod
    def _incident_record(run: OnlinePipelineRun) -> IncidentRecord:
        opened = _aware(run.started_at or run.created_at)
        updated = _aware(run.updated_at)
        severity = "CRITICAL" if run.error_code == "SAFETY_VIOLATION" else "ERROR"
        reason = run.error_code or run.waiting_reason_code or run.status
        return IncidentRecord(
            incident_id=f"pipeline:{run.run_id}",
            status="OPEN",
            severity=severity,
            source="engine_orchestrator",
            title="Pipeline run requires operational review",
            opened_at=opened,
            updated_at=updated,
            symbol=run.symbol,
            resolved_at=None,
            safe_description="A persisted pipeline run recorded a non-success terminal state.",
            reason_code=reason,
            timeframe=run.primary_timeframe,
            closed_until_ms=int(run.closed_until_ms),
        )

    def _incident_rows(self, query: IncidentQuery | None = None, *, scan_limit: int = 5000):
        statement = select(OnlinePipelineRun).where(OnlinePipelineRun.status.in_(ANOMALOUS_RUN_STATUSES))
        if query is not None:
            if query.symbol:
                statement = statement.where(OnlinePipelineRun.symbol == query.symbol.upper())
            if query.from_at:
                statement = statement.where(OnlinePipelineRun.updated_at >= query.from_at)
            if query.to_at:
                statement = statement.where(OnlinePipelineRun.updated_at < query.to_at)
            if query.cursor:
                statement = statement.where(OnlinePipelineRun.updated_at <= query.cursor.updated_at)
        statement = statement.order_by(
            OnlinePipelineRun.updated_at.desc(), OnlinePipelineRun.run_id.desc()
        ).limit(scan_limit)
        with self._session() as session:
            return tuple(session.scalars(statement))

    def list_incidents(self, query: IncidentQuery) -> RecordPage:
        records = [self._incident_record(run) for run in self._incident_rows(query, scan_limit=max(1000, query.limit * 10))]
        if query.status:
            records = [item for item in records if item.status == query.status]
        if query.severity:
            records = [item for item in records if item.severity == query.severity]
        records.sort(key=lambda item: (item.updated_at, item.incident_id), reverse=True)
        if query.cursor:
            anchor = (query.cursor.updated_at, query.cursor.identifier)
            records = [item for item in records if (item.updated_at, item.incident_id) < anchor]
        selected = records[: query.limit + 1]
        return RecordPage(tuple(selected[: query.limit]), len(selected) > query.limit)

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        prefix = "pipeline:"
        if not incident_id.startswith(prefix):
            return None
        run_id = incident_id[len(prefix):]
        statement = select(OnlinePipelineRun).where(
            OnlinePipelineRun.run_id == run_id,
            OnlinePipelineRun.status.in_(ANOMALOUS_RUN_STATUSES),
        )
        with self._session() as session:
            run = session.scalar(statement)
        return self._incident_record(run) if run is not None else None

    def count_active_incidents(self) -> int:
        statement = select(func.count()).select_from(OnlinePipelineRun).where(
            OnlinePipelineRun.status.in_(ANOMALOUS_RUN_STATUSES)
        )
        with self._session() as session:
            return int(session.scalar(statement) or 0)

    def list_recent_runs(self, limit: int) -> tuple[RunRecord, ...]:
        result_count = func.count(OnlinePipelineResultRow.id)
        statement = (
            select(OnlinePipelineRun, result_count)
            .outerjoin(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
            .group_by(OnlinePipelineRun.id)
            .order_by(OnlinePipelineRun.closed_until_ms.desc(), OnlinePipelineRun.run_id.desc())
            .limit(limit)
        )
        with self._session() as session:
            rows = tuple(session.execute(statement))
        return tuple(
            RunRecord(
                run_id=run.run_id,
                symbol=run.symbol,
                primary_timeframe=run.primary_timeframe,
                closed_until_ms=int(run.closed_until_ms),
                status=run.status,
                attempt_count=int(run.freshness_attempt_count or 0),
                result_count=int(count or 0),
            )
            for run, count in rows
        )

    def get_health(self) -> HealthRecord:
        model = CANDLE_MODELS[self._primary_timeframe]
        candle_statement = select(func.max(model.updated_at_utc)).where(model.is_closed.is_(True))
        run_statement = select(OnlinePipelineRun).order_by(OnlinePipelineRun.updated_at.desc()).limit(1)
        with self._session() as session:
            candle_observed = session.scalar(candle_statement)
            run = session.scalar(run_statement)
        observations = [value for value in (candle_observed, getattr(run, "updated_at", None)) if value is not None]
        observed_at = max((_aware(value) for value in observations), default=datetime.now(timezone.utc))
        market_status = "NOT_AVAILABLE" if candle_observed is None else _health(
            getattr(run, "market_data_freshness_status", None)
        )
        orchestrator_status = "NOT_AVAILABLE"
        if run is not None:
            orchestrator_status = "ERROR" if run.status in {"ERROR", "MODULE_ERROR"} else "UNKNOWN"
            if run.status == "COMPLETED":
                orchestrator_status = "OK"
            elif run.status in {"WAITING_FOR_REQUIRED_BOUNDARY", "CHECKING_FRESHNESS"}:
                orchestrator_status = "DEGRADED"
        services = (
            ServiceRecord("market-data", market_status, _aware(candle_observed or observed_at)),
            ServiceRecord("online-orchestrator", orchestrator_status, _aware(getattr(run, "updated_at", observed_at))),
        )
        rank = {"ERROR": 5, "OFFLINE": 4, "DEGRADED": 3, "STALE": 2, "NOT_AVAILABLE": 1, "UNKNOWN": 1, "OK": 0}
        overall = max(services, key=lambda item: rank.get(item.status, 1)).status
        return HealthRecord(overall, observed_at, services)
