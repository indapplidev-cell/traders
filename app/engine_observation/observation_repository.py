from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .observation_errors import ObservationDatabaseError, ObservationSchemaError
from .observation_models import ResultRecord, RunRecord

REQUIRED_COLUMNS = {
    "online_pipeline_runs": {"run_id", "symbol", "primary_timeframe", "closed_until_ms", "closed_until_utc",
        "status", "started_at", "finished_at", "duration_ms", "daemon_instance_id", "final_result"},
    "online_pipeline_results": {"run_id", "symbol", "primary_timeframe", "closed_until_ms",
        "analysis_payload_json", "setup_payload_json", "strategy_payload_json", "risk_payload_json",
        "paper_payload_json", "module_reasons_json", "safety_counters_json"},
    "market_data_sync_state": {"symbol", "timeframe", "status", "freshness_lag_candles", "missing_count",
        "last_error_code", "updated_at"},
}


class ObservationRepository:
    """Only SELECT operations, with enforced read-only PostgreSQL transactions."""

    def __init__(self, session_or_factory: Session | sessionmaker[Session]) -> None:
        self._source = session_or_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._source, Session):
            yield self._source
        else:
            with self._source() as session: yield session

    def check_connection_and_schema(self) -> dict:
        try:
            with self._session() as session:
                bind = session.get_bind()
                session.execute(text("SELECT 1"))
                inspector = inspect(bind)
                missing = {}
                for table, required in REQUIRED_COLUMNS.items():
                    existing = {column["name"] for column in inspector.get_columns(table)} if inspector.has_table(table) else set()
                    if required - existing: missing[table] = sorted(required - existing)
                if missing: raise ObservationSchemaError(f"missing tables/columns: {missing}")
                return {"database": str(bind.url).split("@")[0] + "@***", "schema_ok": True,
                        "dialect": bind.dialect.name}
        except ObservationSchemaError: raise
        except Exception as exc: raise ObservationDatabaseError(str(exc)) from exc

    @staticmethod
    def _readonly(session: Session) -> None:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SET TRANSACTION READ ONLY"))

    def availability(self, symbols: tuple[str, ...], timeframe: str) -> dict:
        sql = text("SELECT min(closed_until_utc) AS first_utc, max(closed_until_utc) AS latest_utc "
                   "FROM online_pipeline_runs WHERE symbol = ANY(:symbols) AND primary_timeframe=:tf")
        with self._session() as session:
            self._readonly(session)
            row = session.execute(sql, {"symbols": list(symbols), "tf": timeframe}).mappings().one()
            session.rollback()
        return dict(row)

    def load_runs(self, symbols: tuple[str, ...], timeframe: str, start: datetime, end: datetime) -> list[RunRecord]:
        sql = text("SELECT run_id,symbol,primary_timeframe,closed_until_ms,closed_until_utc,status,started_at,finished_at,"
            "duration_ms,trigger_source,daemon_instance_id,market_data_freshness_status,analysis_status,setup_status,"
            "strategy_status,risk_status,paper_status,final_result,final_reason,error_code,error_message,future_bars_used,"
            "is_trade_signal,is_executable,order_approved,execution_approved,position_opened,position_size_approved "
            "FROM online_pipeline_runs WHERE symbol = ANY(:symbols) AND primary_timeframe=:tf "
            "AND closed_until_utc>=:start AND closed_until_utc<:end ORDER BY closed_until_ms,symbol")
        with self._session() as session:
            self._readonly(session)
            rows = session.execute(sql, {"symbols": list(symbols), "tf": timeframe, "start": start, "end": end}).mappings().all()
            session.rollback()
        return [RunRecord(**dict(row)) for row in rows]

    def load_results(self, symbols: tuple[str, ...], timeframe: str, start_ms: int, end_ms: int) -> list[ResultRecord]:
        sql = text("SELECT run_id,symbol,primary_timeframe,closed_until_ms,market_data_payload_json,analysis_payload_json,"
            "setup_payload_json,strategy_payload_json,risk_payload_json,paper_payload_json,module_reasons_json,"
            "module_warnings_json,safety_counters_json FROM online_pipeline_results WHERE symbol = ANY(:symbols) "
            "AND primary_timeframe=:tf AND closed_until_ms>=:start_ms AND closed_until_ms<:end_ms ORDER BY closed_until_ms,symbol")
        with self._session() as session:
            self._readonly(session)
            rows = session.execute(sql, {"symbols": list(symbols), "tf": timeframe,
                                   "start_ms": start_ms, "end_ms": end_ms}).mappings().all()
            session.rollback()
        return [ResultRecord(**dict(row)) for row in rows]

    def load_sync_state(self) -> list[dict]:
        sql = text("SELECT symbol,timeframe,status,freshness_lag_candles,missing_count,last_error_code,"
                   "last_error_message,updated_at,daemon_instance_id FROM market_data_sync_state ORDER BY symbol,timeframe")
        with self._session() as session:
            self._readonly(session)
            rows = [dict(row) for row in session.execute(sql).mappings().all()]
            session.rollback()
        return rows
