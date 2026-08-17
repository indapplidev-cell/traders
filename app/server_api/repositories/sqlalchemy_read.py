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

from sqlalchemy import String, and_, cast, func, literal, or_, select, text, tuple_
from sqlalchemy.orm import Session, aliased

from app.engine_analysis.analysis_snapshot import AnalysisSnapshotStatus
from app.engine_market_data.db.candle_tables import CANDLE_MODELS
from app.engine_market_data.continuous_sync_state import MarketDataSyncState
from app.engine_orchestrator.orchestrator_config import DEFAULT_MINIMUM_WINDOWS
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE, TARGET_TIMEFRAMES, TradingUniverseVersion, runtime_universe
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.db.paper_mappings import orm_values_to_paper_event, orm_values_to_paper_fill, orm_values_to_paper_position
from app.db.paper_models import (
    PaperAccountBaselineRecord, PaperExitDecisionRecord, PaperExitEvaluationCursorRecord,
    PaperFillRecord, PaperJournalEntryRecord, PaperOrderRecord, PaperPositionRecord,
    TradingUniverseRuntimeStateRecord,
)
from app.engine_paper.accounting import PaperAccountBaseline, PaperAccountIdentity, PaperClosedTradeFacts
from app.server_api.health_policy import evaluate_boundary_health
from app.server_api.mapping.contract import utc_text
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
    PaperPositionQuery,
    PaperPositionRecordView,
    PaperTradeQuery,
    PaperListQuery,
    PaperOrderRecordView,
    PaperFillRecordView,
    PaperJournalRecordView,
    TradingUniverseSymbolReadinessRecord,
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
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if primary_timeframe not in CANDLE_MODELS:
            raise ValueError("unsupported primary timeframe")
        self._session_or_factory = session_or_factory
        self._primary_timeframe = primary_timeframe
        self._clock = clock or (lambda: datetime.now(timezone.utc))

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

    def _latest_available_analysis(
        self, symbol: str
    ) -> tuple[OnlinePipelineRun | None, OnlinePipelineResultRow | None]:
        candidate = aliased(OnlinePipelineResultRow)
        analysis = candidate.analysis_payload_json
        analyzed = AnalysisSnapshotStatus.ANALYZED.value
        eligible_result_id = (
            select(candidate.id)
            .where(
                candidate.run_id == OnlinePipelineRun.run_id,
                candidate.symbol == OnlinePipelineRun.symbol,
                candidate.primary_timeframe == OnlinePipelineRun.primary_timeframe,
                candidate.closed_until_ms == OnlinePipelineRun.closed_until_ms,
                analysis["status"].as_string() == analyzed,
                analysis["snapshot_id"].as_string().is_not(None),
                analysis["snapshot_id"].as_string() != "",
                analysis["created_at_ms"].as_string().is_not(None),
                analysis["market_data_health"].as_string().is_not(None),
                analysis["market_data_health"].as_string() != "",
                analysis["symbol"].as_string() == OnlinePipelineRun.symbol,
                analysis["timeframe"].as_string()
                == OnlinePipelineRun.primary_timeframe,
                analysis["closed_until_ms"].as_string()
                == cast(OnlinePipelineRun.closed_until_ms, String),
                analysis["future_bars_used"].as_boolean().is_(False),
                analysis["degraded"].as_boolean().is_(False),
                analysis["enough_data"].as_boolean().is_(True),
            )
            .correlate(OnlinePipelineRun)
            .limit(1)
            .scalar_subquery()
        )
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .join(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.id == eligible_result_id,
            )
            .where(
                OnlinePipelineRun.symbol == symbol.upper(),
                OnlinePipelineRun.primary_timeframe == self._primary_timeframe,
                OnlinePipelineRun.analysis_status == analyzed,
            )
            .order_by(
                OnlinePipelineRun.closed_until_ms.desc(),
                OnlinePipelineResultRow.created_at.desc(),
                OnlinePipelineResultRow.id.desc(),
            )
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
        strategy = _mapping(result.strategy_payload_json) if result is not None else {}
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
            strategy_status=(str(strategy.get("decision_status")) if strategy.get("decision_status") is not None
                             else (run.strategy_status if run is not None else None)),
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

    def trading_universe_readiness(self) -> tuple[TradingUniverseSymbolReadinessRecord, ...]:
        """Project preparation readiness solely from persisted runtime state."""

        symbols = PREPARED_NEXT_TRADING_UNIVERSE.symbols
        counts: dict[tuple[str, str], int] = {}
        with self._session() as session:
            states = tuple(session.scalars(
                select(MarketDataSyncState).where(MarketDataSyncState.symbol.in_(symbols))
            ))
            for timeframe, model in CANDLE_MODELS.items():
                rows = session.execute(
                    select(model.symbol, func.count())
                    .where(model.symbol.in_(symbols), model.is_closed.is_(True))
                    .group_by(model.symbol)
                )
                for symbol, count in rows:
                    counts[(str(symbol), timeframe)] = int(count)
            runs = tuple(session.scalars(
                select(OnlinePipelineRun)
                .where(OnlinePipelineRun.symbol.in_(symbols))
                .order_by(
                    OnlinePipelineRun.symbol.asc(),
                    OnlinePipelineRun.closed_until_ms.desc(),
                    OnlinePipelineRun.id.desc(),
                )
            ))

        state_by_key = {(row.symbol, row.timeframe): row for row in states}
        latest_run: dict[str, OnlinePipelineRun] = {}
        for run in runs:
            latest_run.setdefault(run.symbol, run)

        result = []
        for symbol in symbols:
            ready_timeframes = tuple(
                timeframe for timeframe in TARGET_TIMEFRAMES
                if (
                    (state := state_by_key.get((symbol, timeframe))) is not None
                    and state.status == "OK"
                    and state.missing_count == 0
                    and state.source.endswith("_public_rest")
                    and counts.get((symbol, timeframe), 0) >= DEFAULT_MINIMUM_WINDOWS[timeframe]
                )
            )
            history_ready = all(
                counts.get((symbol, timeframe), 0) >= DEFAULT_MINIMUM_WINDOWS[timeframe]
                for timeframe in TARGET_TIMEFRAMES
            )
            run = latest_run.get(symbol)
            analysis_ready = bool(
                run is not None and run.status == "COMPLETED"
                and run.analysis_status == "ANALYZED" and not run.error_code
            )
            setup_ready = bool(
                analysis_ready and run is not None
                and run.setup_status not in {None, "", "ERROR"}
            )
            strategy_compatible = bool(
                setup_ready and run is not None
                and run.strategy_status not in {None, "", "ERROR", "MODULE_ERROR"}
            )
            risk_compatible = bool(
                setup_ready and run is not None
                and run.risk_status not in {None, "", "ERROR", "MODULE_ERROR"}
            )
            result.append(TradingUniverseSymbolReadinessRecord(
                symbol=symbol,
                ready_timeframes=ready_timeframes,
                history_ready=history_ready,
                analysis_ready=analysis_ready,
                setup_ready=setup_ready,
                strategy_compatible=strategy_compatible,
                risk_compatible=risk_compatible,
            ))
        return tuple(result)

    def active_trading_universe(self) -> TradingUniverseVersion:
        with self._session() as session:
            row = session.get(TradingUniverseRuntimeStateRecord, "PRODUCTION")
        if row is None:
            raise RuntimeError("TRADING_UNIVERSE_STATE_UNAVAILABLE")
        return runtime_universe(row.active_version_id)

    def get_analysis(self, symbol: str) -> AnalysisRecord | None:
        run, result = self._latest_available_analysis(symbol)
        if run is None or result is None:
            return None
        return self._analysis_record(run, result)

    @staticmethod
    def _analysis_record(run: OnlinePipelineRun, result: OnlinePipelineResultRow) -> AnalysisRecord:
        payload = _mapping(result.analysis_payload_json)
        if not payload:
            raise ValueError("eligible analysis result has no payload")
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

    def list_latest_analyses(self, symbols: tuple[str, ...]) -> tuple[AnalysisRecord, ...]:
        """One SQL query, at most one latest-available row per active symbol."""
        bounded = tuple(dict.fromkeys(value.upper() for value in symbols))
        if not bounded or len(bounded) > 10:
            return ()
        candidate = aliased(OnlinePipelineResultRow)
        analysis = candidate.analysis_payload_json
        analyzed = AnalysisSnapshotStatus.ANALYZED.value
        ranked = (
            select(
                OnlinePipelineRun.id.label("run_pk"), candidate.id.label("result_pk"),
                func.row_number().over(
                    partition_by=OnlinePipelineRun.symbol,
                    order_by=(OnlinePipelineRun.closed_until_ms.desc(), candidate.created_at.desc(), candidate.id.desc()),
                ).label("row_number"),
            )
            .join(candidate, candidate.run_id == OnlinePipelineRun.run_id)
            .where(
                OnlinePipelineRun.symbol.in_(bounded),
                OnlinePipelineRun.primary_timeframe == self._primary_timeframe,
                OnlinePipelineRun.analysis_status == analyzed,
                candidate.symbol == OnlinePipelineRun.symbol,
                candidate.primary_timeframe == OnlinePipelineRun.primary_timeframe,
                candidate.closed_until_ms == OnlinePipelineRun.closed_until_ms,
                analysis["status"].as_string() == analyzed,
                analysis["snapshot_id"].as_string().is_not(None), analysis["snapshot_id"].as_string() != "",
                analysis["created_at_ms"].as_string().is_not(None),
                analysis["market_data_health"].as_string().is_not(None), analysis["market_data_health"].as_string() != "",
                analysis["symbol"].as_string() == OnlinePipelineRun.symbol,
                analysis["timeframe"].as_string() == OnlinePipelineRun.primary_timeframe,
                analysis["closed_until_ms"].as_string() == cast(OnlinePipelineRun.closed_until_ms, String),
                analysis["future_bars_used"].as_boolean().is_(False),
                analysis["degraded"].as_boolean().is_(False),
                analysis["enough_data"].as_boolean().is_(True),
            ).subquery()
        )
        statement = (
            select(OnlinePipelineRun, OnlinePipelineResultRow)
            .join(ranked, ranked.c.run_pk == OnlinePipelineRun.id)
            .join(OnlinePipelineResultRow, OnlinePipelineResultRow.id == ranked.c.result_pk)
            .where(ranked.c.row_number == 1)
            .order_by(OnlinePipelineRun.symbol.asc()).limit(len(bounded))
        )
        with self._session() as session:
            rows = tuple(session.execute(statement))
        return tuple(self._analysis_record(run, result) for run, result in rows)

    @staticmethod
    def _setup_record(
        *,
        symbol: str,
        primary_timeframe: str,
        closed_until_ms: int,
        updated_at: datetime,
        setup_payload: Any,
        strategy_payload: Any = None,
        risk_payload: Any = None,
        paper_payload: Any = None,
        strategy_status: str | None = None,
        risk_status: str | None = None,
        paper_status: str | None = None,
    ) -> SetupRecord | None:
        setup = _mapping(setup_payload)
        if not setup:
            return None
        strategy = _mapping(strategy_payload)
        risk = _mapping(risk_payload)
        paper = _mapping(paper_payload)
        setup_id = str(setup.get("setup_id") or "")
        if not setup_id:
            return None
        return SetupRecord(
            setup_id=setup_id,
            symbol=symbol,
            timeframe=str(setup.get("timeframe") or primary_timeframe),
            closed_until_ms=int(closed_until_ms),
            status=str(setup.get("status") or "UNKNOWN"),
            setup_type=str(setup.get("setup_type") or "UNKNOWN"),
            direction=_direction(setup.get("direction_hint")),
            quality=str(setup.get("setup_quality") or "UNKNOWN"),
            quality_score=_score(setup.get("quality_score")),
            updated_at=_aware(updated_at),
            confirmation_state=str(setup.get("confirmation_state") or "NOT_APPLICABLE"),
            reason_codes=_sequence(setup.get("reason_codes")),
            warnings=_sequence(setup.get("quality_warnings")),
            invalidation_reasons=_sequence(setup.get("invalidation_reasons")),
            strategy_status=str(strategy.get("decision_status")) if strategy.get("decision_status") is not None else strategy_status,
            risk_status=str(risk.get("risk_status")) if risk.get("risk_status") is not None else risk_status,
            paper_status=str(paper.get("paper_status")) if paper.get("paper_status") is not None else paper_status,
            hypothetical_entry=_decimal(paper.get("hypothetical_entry_reference")),
            hypothetical_stop=_decimal(paper.get("hypothetical_stop_level")),
            hypothetical_target=_decimal(paper.get("hypothetical_target_level")),
            planned_rr=_decimal(paper.get("planned_rr")),
            executable=False,
        )

    def list_setups(self, query: SetupQuery) -> RecordPage:
        setup = OnlinePipelineResultRow.setup_payload_json
        setup_id = setup["setup_id"].as_string()
        candidates = (
            select(
                OnlinePipelineRun.run_id.label("run_id"),
                OnlinePipelineRun.symbol.label("symbol"),
                OnlinePipelineRun.primary_timeframe.label("primary_timeframe"),
                OnlinePipelineRun.closed_until_ms.label("closed_until_ms"),
                OnlinePipelineRun.setup_status.label("status"),
                OnlinePipelineRun.updated_at.label("updated_at"),
            )
            .join(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id,
            )
            .where(OnlinePipelineRun.setup_status.is_not(None))
        )
        if query.symbol:
            candidates = candidates.where(
                OnlinePipelineRun.symbol == query.symbol.upper()
            )
        if query.status:
            candidates = candidates.where(
                OnlinePipelineRun.setup_status == query.status
            )
        if query.from_at:
            candidates = candidates.where(
                OnlinePipelineRun.updated_at >= query.from_at
            )
        if query.to_at:
            candidates = candidates.where(
                OnlinePipelineRun.updated_at < query.to_at
            )
        if query.cursor:
            candidates = candidates.where(
                tuple_(OnlinePipelineRun.updated_at, OnlinePipelineRun.run_id)
                < (query.cursor.updated_at, query.cursor.identifier)
            )
        candidates = (
            candidates.order_by(
                OnlinePipelineRun.updated_at.desc(),
                OnlinePipelineRun.run_id.desc(),
            )
            .limit(query.limit + 1)
            .subquery()
        )
        statement = (
            select(
                candidates.c.run_id,
                setup_id.label("setup_id"),
                candidates.c.symbol,
                func.coalesce(
                    setup["timeframe"].as_string(),
                    candidates.c.primary_timeframe,
                ).label("timeframe"),
                candidates.c.closed_until_ms,
                func.coalesce(
                    setup["status"].as_string(),
                    candidates.c.status,
                    literal("UNKNOWN"),
                ).label("status"),
                func.coalesce(
                    setup["setup_type"].as_string(), literal("UNKNOWN")
                ).label("setup_type"),
                setup["direction_hint"].as_string().label("direction"),
                func.coalesce(
                    setup["setup_quality"].as_string(), literal("UNKNOWN")
                ).label("quality"),
                setup["quality_score"].as_string().label("quality_score"),
                candidates.c.updated_at,
            )
            .join(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.run_id == candidates.c.run_id,
            )
            .order_by(
                candidates.c.updated_at.desc(),
                candidates.c.run_id.desc(),
            )
        )
        with self._session() as session:
            rows = tuple(session.execute(statement))
        records = [
            SetupRecord(
                setup_id=row.setup_id,
                symbol=row.symbol,
                timeframe=row.timeframe,
                closed_until_ms=int(row.closed_until_ms),
                status=row.status,
                setup_type=row.setup_type,
                direction=_direction(row.direction),
                quality=row.quality,
                quality_score=_score(row.quality_score),
                updated_at=_aware(row.updated_at),
                cursor_identifier=row.run_id,
            )
            for row in rows
            if row.setup_id
        ]
        return RecordPage(
            tuple(records[: query.limit]), len(records) > query.limit
        )

    def get_setup(self, setup_id: str) -> SetupRecord | None:
        setup = OnlinePipelineResultRow.setup_payload_json
        statement = (
            select(
                OnlinePipelineRun.symbol,
                OnlinePipelineRun.primary_timeframe,
                OnlinePipelineRun.closed_until_ms,
                OnlinePipelineRun.updated_at,
                OnlinePipelineRun.strategy_status,
                OnlinePipelineRun.risk_status,
                OnlinePipelineRun.paper_status,
                setup.label("setup_payload"),
                OnlinePipelineResultRow.strategy_payload_json.label(
                    "strategy_payload"
                ),
                OnlinePipelineResultRow.risk_payload_json.label("risk_payload"),
                OnlinePipelineResultRow.paper_payload_json.label("paper_payload"),
            )
            .join(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id,
            )
            .where(setup["setup_id"].as_string() == setup_id)
            .order_by(
                OnlinePipelineRun.updated_at.desc(),
                OnlinePipelineRun.run_id.desc(),
            )
            .limit(1)
        )
        with self._session() as session:
            row = session.execute(statement).first()
        if row is None:
            return None
        return self._setup_record(
            symbol=row.symbol,
            primary_timeframe=row.primary_timeframe,
            closed_until_ms=row.closed_until_ms,
            updated_at=row.updated_at,
            setup_payload=row.setup_payload,
            strategy_payload=row.strategy_payload,
            risk_payload=row.risk_payload,
            paper_payload=row.paper_payload,
            strategy_status=row.strategy_status,
            risk_status=row.risk_status,
            paper_status=row.paper_status,
        )

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
        decision = evaluate_boundary_health(
            run,
            candle_available=candle_observed is not None,
            now=self._clock(),
        )
        observations = [value for value in (candle_observed, getattr(run, "updated_at", None)) if value is not None]
        observed_at = max((_aware(value) for value in observations), default=datetime.now(timezone.utc))
        services = (
            ServiceRecord("market-data", decision.market_data_status, _aware(candle_observed or observed_at)),
            ServiceRecord("online-orchestrator", decision.orchestrator_status, _aware(getattr(run, "updated_at", observed_at))),
        )
        return HealthRecord(
            decision.status,
            observed_at,
            services,
            timing_state=decision.timing_state,
            reason_code=decision.reason_code,
            operational=decision.operational,
            ready=decision.ready,
            acceptance_blocking=decision.acceptance_blocking,
        )

    def schema_revision(self) -> str | None:
        """Read only Alembic's singleton version; no PAPER relation is touched."""
        with self._session() as session:
            return session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()

    def list_account_baselines(self, limit: int = 2) -> tuple[PaperAccountBaseline, ...]:
        statement = select(PaperAccountBaselineRecord).order_by(
            PaperAccountBaselineRecord.initialized_at,
            PaperAccountBaselineRecord.baseline_id,
        ).limit(limit)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
        return tuple(PaperAccountBaseline(
            baseline_id=row.baseline_id,
            identity=PaperAccountIdentity(row.account_id, row.accounting_session_id, row.currency),
            initial_balance=row.initial_balance,
            initialized_at=_aware(row.initialized_at),
            semantic_version=row.semantic_version,
        ) for row in rows)

    @staticmethod
    def _facts_for_rows(session: Session, rows: tuple[PaperPositionRecord, ...]) -> tuple[PaperClosedTradeFacts, ...]:
        if not rows:
            return ()
        position_ids = tuple(row.position_id for row in rows)
        fill_ids = tuple({value for row in rows for value in (row.entry_fill_id, row.exit_fill_id) if value})
        fills = tuple(session.scalars(select(PaperFillRecord).where(PaperFillRecord.fill_id.in_(fill_ids))))
        fill_map = {row.fill_id: orm_values_to_paper_fill(row) for row in fills}
        journals = tuple(session.scalars(
            select(PaperJournalEntryRecord)
            .where(PaperJournalEntryRecord.position_id.in_(position_ids))
            .order_by(PaperJournalEntryRecord.occurred_at, PaperJournalEntryRecord.journal_entry_id)
        ))
        event_map: dict[str, list] = {value: [] for value in position_ids}
        for row in journals:
            if row.position_id in event_map:
                event_map[row.position_id].append(orm_values_to_paper_event(row))
        return tuple(PaperClosedTradeFacts(
            position=orm_values_to_paper_position(row),
            entry_fill=fill_map.get(row.entry_fill_id),
            exit_fill=fill_map.get(row.exit_fill_id),
            exit_reason=row.reason_code,
            journal_events=tuple(event_map[row.position_id]),
        ) for row in rows)

    def list_closed_trade_facts(self, limit: int) -> tuple[PaperClosedTradeFacts, ...]:
        statement = select(PaperPositionRecord).where(PaperPositionRecord.state == "CLOSED").order_by(
            PaperPositionRecord.closed_at, PaperPositionRecord.position_id
        ).limit(limit)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
            return self._facts_for_rows(session, rows)

    @staticmethod
    def _position_view(row: PaperPositionRecord) -> PaperPositionRecordView:
        return PaperPositionRecordView(
            position=orm_values_to_paper_position(row), entry_time=_aware(row.opened_at), updated_at=_aware(row.updated_at),
            exit_reason=row.reason_code if row.state in {"CLOSED", "FAILED"} else None,
            entry_order_id=row.entry_order_id, entry_fill_id=row.entry_fill_id,
            close_fill_id=row.exit_fill_id,
        )

    def list_paper_positions(self, query: PaperPositionQuery) -> RecordPage:
        statement = select(PaperPositionRecord)
        if query.state:
            statement = statement.where(PaperPositionRecord.state == query.state)
        if query.symbol:
            statement = statement.where(PaperPositionRecord.symbol == query.symbol)
        if query.cursor:
            statement = statement.where(tuple_(PaperPositionRecord.updated_at, PaperPositionRecord.position_id) <
                (query.cursor.updated_at, query.cursor.identifier))
        statement = statement.order_by(PaperPositionRecord.updated_at.desc(), PaperPositionRecord.position_id.desc()).limit(query.limit + 1)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
        selected = rows[:query.limit]
        return RecordPage(tuple(self._position_view(row) for row in selected), len(rows) > query.limit)

    def get_paper_position(self, position_id: str) -> PaperPositionRecordView | None:
        with self._session() as session:
            row = session.scalar(select(PaperPositionRecord).where(PaperPositionRecord.position_id == position_id))
            if row is None:
                return None
            entry_order = session.scalar(select(PaperOrderRecord).where(PaperOrderRecord.order_id == row.entry_order_id))
            close_order = None
            if entry_order is not None:
                close_order = session.scalar(select(PaperOrderRecord).where(
                    PaperOrderRecord.command_id == entry_order.command_id,
                    PaperOrderRecord.order_role == "EXIT",
                ).order_by(PaperOrderRecord.created_at.desc(), PaperOrderRecord.order_id.desc()).limit(1))
            cursor = session.scalar(select(PaperExitEvaluationCursorRecord).where(
                PaperExitEvaluationCursorRecord.position_id == position_id).limit(1))
            decision = session.scalar(select(PaperExitDecisionRecord).where(
                PaperExitDecisionRecord.position_id == position_id)
                .order_by(PaperExitDecisionRecord.decided_at.desc(), PaperExitDecisionRecord.exit_decision_id.desc()).limit(1))
            events = tuple(session.scalars(select(PaperJournalEntryRecord).where(
                PaperJournalEntryRecord.position_id == position_id)
                .order_by(PaperJournalEntryRecord.occurred_at.desc(), PaperJournalEntryRecord.journal_entry_id.desc()).limit(50)))
        base = self._position_view(row)
        return PaperPositionRecordView(
            position=base.position, entry_time=base.entry_time, updated_at=base.updated_at,
            exit_reason=(decision.cause if decision is not None else base.exit_reason),
            entry_order_id=base.entry_order_id, entry_fill_id=base.entry_fill_id,
            close_order_id=None if close_order is None else close_order.order_id,
            close_fill_id=base.close_fill_id,
            exit_cursor_status=None if cursor is None else f"VERSION_{cursor.version}",
            exit_decision=None if decision is None else decision.cause,
            lifecycle_events=tuple({"event_type": event.event_type, "occurred_at": utc_text(_aware(event.occurred_at)),
                                    "reason_code": event.reason_code} for event in reversed(events)),
        )

    def list_paper_trades(self, query: PaperTradeQuery) -> RecordPage:
        statement = select(PaperPositionRecord).where(PaperPositionRecord.state == "CLOSED")
        if query.symbol:
            statement = statement.where(PaperPositionRecord.symbol == query.symbol)
        if query.side:
            statement = statement.where(PaperPositionRecord.side == query.side)
        if query.exit_reason:
            statement = statement.where(PaperPositionRecord.reason_code == query.exit_reason)
        if query.from_at:
            statement = statement.where(PaperPositionRecord.closed_at >= query.from_at)
        if query.to_at:
            statement = statement.where(PaperPositionRecord.closed_at < query.to_at)
        if query.cursor:
            statement = statement.where(tuple_(PaperPositionRecord.closed_at, PaperPositionRecord.position_id) <
                (query.cursor.updated_at, query.cursor.identifier))
        statement = statement.order_by(PaperPositionRecord.closed_at.desc(), PaperPositionRecord.position_id.desc()).limit(query.limit + 1)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
            facts = self._facts_for_rows(session, rows[:query.limit])
        return RecordPage(facts, len(rows) > query.limit)

    def list_paper_orders(self, query: PaperListQuery) -> RecordPage:
        statement = select(PaperOrderRecord)
        if query.symbol:
            statement = statement.where(PaperOrderRecord.symbol == query.symbol)
        if query.cursor:
            statement = statement.where(tuple_(PaperOrderRecord.updated_at, PaperOrderRecord.order_id) <
                (query.cursor.updated_at, query.cursor.identifier))
        statement = statement.order_by(PaperOrderRecord.updated_at.desc(), PaperOrderRecord.order_id.desc()).limit(query.limit + 1)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
        items = tuple(PaperOrderRecordView(
            row.order_id, row.command_id, row.symbol, row.side, row.order_role, row.order_type,
            row.state, row.requested_quantity, row.filled_quantity, row.average_fill_price,
            row.reason_code, _aware(row.created_at), _aware(row.updated_at),
        ) for row in rows[:query.limit])
        return RecordPage(items, len(rows) > query.limit)

    def list_paper_fills(self, query: PaperListQuery) -> RecordPage:
        statement = select(PaperFillRecord)
        if query.symbol:
            statement = statement.where(PaperFillRecord.symbol == query.symbol)
        if query.cursor:
            statement = statement.where(tuple_(PaperFillRecord.filled_at, PaperFillRecord.fill_id) <
                (query.cursor.updated_at, query.cursor.identifier))
        statement = statement.order_by(PaperFillRecord.filled_at.desc(), PaperFillRecord.fill_id.desc()).limit(query.limit + 1)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
        items = tuple(PaperFillRecordView(
            row.fill_id, row.order_id, row.symbol, row.side, row.fill_role, row.quantity,
            row.price, row.fee_amount, row.fee_asset, _aware(row.filled_at),
        ) for row in rows[:query.limit])
        return RecordPage(items, len(rows) > query.limit)

    def list_paper_journal(self, query: PaperListQuery) -> RecordPage:
        statement = select(PaperJournalEntryRecord)
        if query.cursor:
            statement = statement.where(tuple_(PaperJournalEntryRecord.occurred_at, PaperJournalEntryRecord.journal_entry_id) <
                (query.cursor.updated_at, query.cursor.identifier))
        statement = statement.order_by(PaperJournalEntryRecord.occurred_at.desc(), PaperJournalEntryRecord.journal_entry_id.desc()).limit(query.limit + 1)
        with self._session() as session:
            rows = tuple(session.scalars(statement))
        items = tuple(PaperJournalRecordView(
            row.journal_entry_id, row.aggregate_type, row.aggregate_id, row.event_type,
            int(row.aggregate_version), row.reason_code, row.causation_id, row.correlation_id,
            _aware(row.occurred_at),
        ) for row in rows[:query.limit])
        return RecordPage(items, len(rows) > query.limit)

    def count_open_paper_positions(self) -> int:
        with self._session() as session:
            return int(session.scalar(select(func.count()).select_from(PaperPositionRecord).where(
                PaperPositionRecord.state.in_(("OPEN", "CLOSING")))) or 0)

    def total_unrealized_pnl(self) -> Decimal:
        with self._session() as session:
            value = session.scalar(select(func.sum(PaperPositionRecord.unrealized_pnl)).where(
                PaperPositionRecord.state.in_(("OPEN", "CLOSING"))))
        return Decimal("0") if value is None else Decimal(value)
