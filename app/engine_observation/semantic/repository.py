from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from typing import Any

from app.engine_observation.observer_reliability import CollectorStatus, redact
from .contracts import SemanticContract
from .models import CandleSnapshot, ResultSnapshot, RunSnapshot, SemanticCollection


CANDLE_TABLES = {"1m": "candles_1m", "5m": "candles_5m", "15m": "candles_15m", "1h": "candles_1h", "4h": "candles_4h", "1d": "candles_1d"}
MAX_TIMEFRAME_MS = 86_400_000


def _status(exc: Exception) -> tuple[CollectorStatus, str]:
    lowered = str(exc).lower()
    if "timeout" in lowered or "canceling statement" in lowered:
        return CollectorStatus.TIMEOUT, "SEMANTIC_DB_TIMEOUT"
    if "connect" in lowered or "server closed" in lowered:
        return CollectorStatus.UNAVAILABLE, "SEMANTIC_DB_UNAVAILABLE"
    return CollectorStatus.FAILED, "SEMANTIC_DB_FAILED"


class PostgreSQLSemanticRepository:
    """Bounded, read-only PostgreSQL semantic snapshot repository."""

    def __init__(self, dsn: str, contract: SemanticContract, *, timeout_seconds: float = 10.0) -> None:
        self.dsn, self.contract, self.timeout_seconds = dsn, contract, timeout_seconds

    def collect(self, *, updated_since: datetime | None = None) -> SemanticCollection:
        del updated_since  # Contract range is finite (<= expected windows); retained as restart watermark API.
        try:
            import psycopg
            from psycopg.rows import dict_row
        except Exception as exc:
            status, code = _status(exc)
            return SemanticCollection(None, run_status=status, result_status=status, candle_status=status, errors={"all": code})
        timeout_ms = max(1, int(self.timeout_seconds * 1000))
        durations: dict[str, int] = {}
        runs: tuple[RunSnapshot, ...] = ()
        results: tuple[ResultSnapshot, ...] = ()
        candles: tuple[CandleSnapshot, ...] = ()
        database_now = None
        run_status = result_status = candle_status = CollectorStatus.UNAVAILABLE
        errors: dict[str, str] = {}
        params = {"symbols": list(self.contract.symbols), "timeframe": self.contract.primary_timeframe,
                  "lower": self.contract.anchor_closed_until_ms, "upper": self.contract.last_measured_boundary_ms,
                  "limit": self.contract.expected_total_windows + len(self.contract.symbols) * 4}
        try:
            started = time.monotonic()
            with psycopg.connect(self.dsn, connect_timeout=max(1, int(self.timeout_seconds)),
                                 options="-c default_transaction_read_only=on", row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    cursor.execute("SELECT set_config('statement_timeout', %s, true)", (f"{timeout_ms}ms",))
                    cursor.execute("SET LOCAL lock_timeout = '1000ms'")
                    cursor.execute("SET LOCAL application_name = 'traders_ml_semantic_observer'")
                    cursor.execute("SELECT clock_timestamp() AS database_now")
                    database_now = cursor.fetchone()["database_now"]
                    cursor.execute("""SELECT run_id,symbol,primary_timeframe,closed_until_ms,status,
                        COALESCE(waiting_reason_code,error_code,final_reason) AS reason_code,freshness_attempt_count,
                        first_wait_at,last_freshness_checked_at,freshness_deadline_at,waiting_timeframes,
                        last_freshness_payload,market_data_freshness_status,created_at,started_at,finished_at,updated_at,
                        future_bars_used,execution_approved,position_opened
                        FROM online_pipeline_runs WHERE symbol = ANY(%(symbols)s) AND primary_timeframe=%(timeframe)s
                        AND closed_until_ms > %(lower)s AND closed_until_ms <= %(upper)s
                        ORDER BY closed_until_ms,symbol LIMIT %(limit)s""", params)
                    raw_runs = cursor.fetchall()
                    cursor.execute("""SELECT id,run_id,created_at,
                            COALESCE(paper_payload_json->>'final_result', strategy_payload_json->>'status') AS result_type,
                            md5(concat_ws('|',market_data_payload_json::text,analysis_payload_json::text,setup_payload_json::text,
                                strategy_payload_json::text,risk_payload_json::text,paper_payload_json::text,module_reasons_json::text,
                                module_warnings_json::text,safety_counters_json::text)) AS payload_hash
                            FROM online_pipeline_results WHERE symbol = ANY(%s) AND primary_timeframe=%s
                            AND closed_until_ms > %s AND closed_until_ms <= %s ORDER BY run_id,id LIMIT %s""",
                                   (list(self.contract.symbols), self.contract.primary_timeframe,
                                    self.contract.anchor_closed_until_ms, self.contract.last_measured_boundary_ms,
                                    self.contract.expected_total_windows * 2 + 10))
                    raw_results = cursor.fetchall()
                    connection.rollback()
            durations["runs_results"] = int((time.monotonic() - started) * 1000)
            def tuple_field(value: Any) -> tuple[str, ...]:
                if isinstance(value, list): return tuple(str(item) for item in value)
                return ()
            built_runs = []
            for row in raw_runs:
                payload = row["last_freshness_payload"] if isinstance(row["last_freshness_payload"], dict) else {}
                reasons = payload.get("blocking_reasons") or payload.get("freshness_reasons") or []
                reason_values = tuple(str(item.get("reason_code", item)) if isinstance(item, dict) else str(item) for item in reasons)
                built_runs.append(RunSnapshot(
                    run_id=row["run_id"], symbol=row["symbol"], primary_timeframe=row["primary_timeframe"], closed_until_ms=row["closed_until_ms"],
                    status=row["status"], reason_code=row["reason_code"], freshness_attempt_count=row["freshness_attempt_count"],
                    first_wait_at=row["first_wait_at"], last_freshness_checked_at=row["last_freshness_checked_at"],
                    freshness_deadline_at=row["freshness_deadline_at"], waiting_timeframes=tuple_field(row["waiting_timeframes"]),
                    freshness_reasons=reason_values, readiness_classification=payload.get("classification"),
                    market_data_freshness_status=row["market_data_freshness_status"], created_at=row["created_at"], started_at=row["started_at"],
                    finished_at=row["finished_at"], updated_at=row["updated_at"], raw_diagnostics=payload,
                    future_bars_used=row["future_bars_used"], execution_approved=row["execution_approved"],
                    position_opened=row["position_opened"]))
            runs = tuple(built_runs)
            results = tuple(ResultSnapshot(str(row["id"]), row["run_id"], row["created_at"], row["result_type"], row["payload_hash"]) for row in raw_results)
            run_status = result_status = CollectorStatus.SUCCESS
        except Exception as exc:
            status, code = _status(exc)
            run_status = result_status = status
            errors["runs_results"] = f"{code}: {redact(type(exc).__name__)}"
        try:
            started = time.monotonic()
            raw_candles = []
            with psycopg.connect(self.dsn, connect_timeout=max(1, int(self.timeout_seconds)),
                                 options="-c default_transaction_read_only=on", row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("BEGIN TRANSACTION READ ONLY")
                    cursor.execute("SELECT set_config('statement_timeout', %s, true)", (f"{timeout_ms}ms",))
                    cursor.execute("SET LOCAL lock_timeout = '1000ms'")
                    cursor.execute("SET LOCAL application_name = 'traders_ml_semantic_observer_candles'")
                    lower = max(0, self.contract.anchor_closed_until_ms - MAX_TIMEFRAME_MS)
                    upper = self.contract.last_measured_boundary_ms
                    for timeframe in self.contract.required_timeframes:
                        table = CANDLE_TABLES[timeframe]
                        cursor.execute(f"SELECT symbol,%s AS timeframe,open_time_ms,close_time_ms,is_closed FROM {table} "
                                       "WHERE symbol = ANY(%s) AND open_time_ms >= %s AND open_time_ms < %s ORDER BY symbol,open_time_ms",
                                       (timeframe, list(self.contract.symbols), lower, upper))
                        raw_candles.extend(cursor.fetchall())
                    connection.rollback()
            durations["candles"] = int((time.monotonic() - started) * 1000)
            candles = tuple(CandleSnapshot(row["symbol"], row["timeframe"], row["open_time_ms"], row["close_time_ms"], row["is_closed"]) for row in raw_candles)
            candle_status = CollectorStatus.SUCCESS
        except Exception as exc:
            candle_status, code = _status(exc)
            errors["candles"] = f"{code}: {redact(type(exc).__name__)}"
        return SemanticCollection(database_now, runs, results, candles, run_status, result_status, candle_status, durations, errors)
