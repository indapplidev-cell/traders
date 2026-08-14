"""Fail-closed production persisted market-data boundary for future PAPER use.

The adapter deliberately has no dependency on exchange transports or PAPER
business services.  It reads the existing market-data tables in one bounded,
read-only, repeatable-read transaction and returns immutable values only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Final, Protocol

from sqlalchemy import Select, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

from app.engine_market_data.candle import Candle
from app.engine_market_data.continuous_sync_config import FRESHNESS_ALLOWANCE_MS
from app.engine_market_data.continuous_sync_state import MarketDataSyncState
from app.engine_market_data.db.candle_repository import candle_checksum
from app.engine_market_data.db.candle_tables import CANDLE_MODELS, CandleTableMixin
from app.engine_market_data.freshness_monitor import (
    close_boundary_ms,
    latest_expected_closed_open_time_ms,
)
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import expected_next_open_time, timeframe_to_milliseconds
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


ADAPTER_SCHEMA_VERSION: Final = "PAPER_PRODUCTION_MARKET_DATA/1.0"
ADAPTER_VERSION: Final = "1.0.0"
AUTHORITATIVE_SOURCE: Final = "PRODUCTION_PERSISTED_MARKET_DATA"
SYMBOL_ALLOWLIST: Final = PREPARED_NEXT_TRADING_UNIVERSE.symbols
TIMEFRAME_ALLOWLIST: Final = ("1m", "5m", "15m", "1h", "4h", "1d")
MAX_SYMBOLS_PER_REQUEST: Final = len(SYMBOL_ALLOWLIST)
MAX_TIMEFRAMES_PER_REQUEST: Final = 6
MAX_CANDLES_PER_TIMEFRAME: Final = 512
MAX_ROWS_PER_REQUEST: Final = MAX_SYMBOLS_PER_REQUEST * MAX_TIMEFRAMES_PER_REQUEST * MAX_CANDLES_PER_TIMEFRAME
MAX_TIME_RANGE_MS: Final = 512 * timeframe_to_milliseconds("1d")
_TIMEFRAME_ORDER: Final = {value: index for index, value in enumerate(TIMEFRAME_ALLOWLIST)}
_READY_SYNC_STATES: Final = frozenset({"OK"})
_TRANSACTION_CONTROL: Final = "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
REQUIRED_SOURCE_EVIDENCE_HASHES: Final[Mapping[str, str]] = {
    "SECURITY_REMEDIATION_RETRY": "afce8eae9d58135a3d9d1e5591cbb0ede5546a90030a9885fb9427d4e6edeaa0",
    "SINGLE_CYCLE_CANARY_RETRY_02": "c9ef780f6c16e1a06564d4b879c416df609821dae9ccf141949bceefa44b22b4",
    "BOUNDED_SEQUENCE_CANARY": "d97cab0ec98de5cbab640da5548789efbd5a3bc4f8335cc2b51e4f9ed1618776",
    "OPERATOR_CONTROLLED_RUNNER": "18e7b78381c0bc0de043c96c870c35ebbcb7cfb665f233bd1d5a23d6fee517db",
    "PRODUCTION_RUNTIME_READINESS_REVIEW": "7754627e41a7e78078674602caad8cf66231297008727c1b4deb5718b206e1ad",
    "BACKUP_RESTORE_RECONCILIATION_READINESS": "0c3ec914a435bf5f6da8d616e2375190bcec80066e6e63c9b1b4474bf67734ec",
    "PRODUCTION_BACKUP_PITR_INFRASTRUCTURE_REMEDIATION": "344611241bef7a19c911026c66d953d153fbaf843794a9fde00b8fe01a1448fc",
    "PRODUCTION_BACKUP_PITR_CONTROLLED_CHANGE": "b58cdaaab7da29f7f433a8017ffc2222472d09a62f81abd96b301eac5e2819ae",
}


class PaperProductionMarketDataOutcome(StrEnum):
    READY = "READY"
    WITHIN_GRACE_READY = "WITHIN_GRACE_READY"
    STALE = "STALE"
    GAP_DETECTED = "GAP_DETECTED"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    CHECKSUM_CONFLICT = "CHECKSUM_CONFLICT"
    FUTURE_CANDLE_DETECTED = "FUTURE_CANDLE_DETECTED"
    INCOMPLETE_TIMEFRAME_SET = "INCOMPLETE_TIMEFRAME_SET"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    TARGET_NOT_ALLOWED = "TARGET_NOT_ALLOWED"
    SCHEMA_NOT_SUPPORTED = "SCHEMA_NOT_SUPPORTED"
    BOUNDED_LIMIT_EXCEEDED = "BOUNDED_LIMIT_EXCEEDED"
    READ_ONLY_POLICY_VIOLATION = "READ_ONLY_POLICY_VIOLATION"
    CANCELLED = "CANCELLED"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperProductionMarketDataReadiness(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    CANCELLED = "CANCELLED"


class PaperProductionMarketDataFindingCode(StrEnum):
    MARKET_DATA_READY = "MARKET_DATA_READY"
    MARKET_DATA_WITHIN_GRACE_READY = "MARKET_DATA_WITHIN_GRACE_READY"
    MARKET_DATA_STALE = "MARKET_DATA_STALE"
    MARKET_DATA_GAP = "MARKET_DATA_GAP"
    MARKET_DATA_DUPLICATE = "MARKET_DATA_DUPLICATE"
    MARKET_DATA_CHECKSUM_CONFLICT = "MARKET_DATA_CHECKSUM_CONFLICT"
    MARKET_DATA_FUTURE_CANDLE = "MARKET_DATA_FUTURE_CANDLE"
    MARKET_DATA_MISSING_TIMEFRAME = "MARKET_DATA_MISSING_TIMEFRAME"
    MARKET_DATA_INSUFFICIENT_HISTORY = "MARKET_DATA_INSUFFICIENT_HISTORY"
    MARKET_DATA_TARGET_NOT_ALLOWED = "MARKET_DATA_TARGET_NOT_ALLOWED"
    MARKET_DATA_LIMIT_EXCEEDED = "MARKET_DATA_LIMIT_EXCEEDED"
    MARKET_DATA_READ_ONLY_VIOLATION = "MARKET_DATA_READ_ONLY_VIOLATION"
    MARKET_DATA_SAFE_FAILURE = "MARKET_DATA_SAFE_FAILURE"
    MARKET_DATA_CANCELLED = "MARKET_DATA_CANCELLED"


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataScope:
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    candles_per_timeframe: int


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataRequest:
    scope: PaperProductionMarketDataScope
    request_id: str
    as_of_ms: int | None = None


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataWatermark:
    source: str
    as_of_ms: int
    latest_closed_open_time_ms: tuple[tuple[str, int], ...]
    latest_closed_close_time_ms: tuple[tuple[str, int], ...]
    watermark_id: str


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataFinding:
    code: PaperProductionMarketDataFindingCode
    symbol: str | None = None
    timeframe: str | None = None
    count: int = 0


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataSnapshot:
    source: str
    symbol: str
    requested_timeframes: tuple[str, ...]
    as_of_ms: int
    snapshot_id: str
    watermark: PaperProductionMarketDataWatermark
    candles: tuple[tuple[str, tuple[Candle, ...]], ...]
    freshness_states: tuple[tuple[str, str], ...]
    continuity_states: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataInput:
    request_id: str
    source: str
    as_of_ms: int
    snapshots: tuple[PaperProductionMarketDataSnapshot, ...]


@dataclass(frozen=True, slots=True)
class PaperProductionMarketDataOutcomeResult:
    outcome: PaperProductionMarketDataOutcome
    readiness: PaperProductionMarketDataReadiness
    request_id: str
    as_of_ms: int | None
    data: PaperProductionMarketDataInput | None = None
    findings: tuple[PaperProductionMarketDataFinding, ...] = ()
    query_count: int = 0
    rows_read: int = 0
    duration_ms: float = 0.0
    read_only: bool = True
    consistent_snapshot: bool = True

    def safe_report(self) -> dict[str, object]:
        snapshots = self.data.snapshots if self.data else ()
        return {
            "schema_version": ADAPTER_SCHEMA_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "request_id": self.request_id,
            "source_class": AUTHORITATIVE_SOURCE,
            "symbols": [value.symbol for value in snapshots],
            "timeframes": sorted(
                {tf for value in snapshots for tf in value.requested_timeframes},
                key=lambda value: _TIMEFRAME_ORDER[value],
            ),
            "as_of_ms": self.as_of_ms,
            "outcome": self.outcome.value,
            "freshness": {
                value.symbol: dict(value.freshness_states) for value in snapshots
            },
            "continuity": {
                value.symbol: dict(value.continuity_states) for value in snapshots
            },
            "row_counts": {
                value.symbol: {tf: len(rows) for tf, rows in value.candles}
                for value in snapshots
            },
            "latest_closed_open_time_ms": {
                value.symbol: dict(value.watermark.latest_closed_open_time_ms)
                for value in snapshots
            },
            "latest_closed_close_time_ms": {
                value.symbol: dict(value.watermark.latest_closed_close_time_ms)
                for value in snapshots
            },
            "snapshot_ids": {value.symbol: value.snapshot_id for value in snapshots},
            "gap_count": sum(
                value.count or 1 for value in self.findings
                if value.code is PaperProductionMarketDataFindingCode.MARKET_DATA_GAP
            ),
            "duplicate_count": sum(
                value.count or 1 for value in self.findings
                if value.code is PaperProductionMarketDataFindingCode.MARKET_DATA_DUPLICATE
            ),
            "checksum_conflict_count": sum(
                value.count or 1 for value in self.findings
                if value.code is PaperProductionMarketDataFindingCode.MARKET_DATA_CHECKSUM_CONFLICT
            ),
            "future_candle_count": sum(
                value.count or 1 for value in self.findings
                if value.code is PaperProductionMarketDataFindingCode.MARKET_DATA_FUTURE_CANDLE
            ),
            "query_count": self.query_count,
            "rows_read": self.rows_read,
            "duration_ms": round(self.duration_ms, 3),
            "read_only": self.read_only,
            "consistent_snapshot": self.consistent_snapshot,
            "finding_codes": [value.code.value for value in self.findings],
        }


class CancellationToken(Protocol):
    def is_set(self) -> bool: ...


class _Cancelled(RuntimeError):
    pass


class ReadOnlyPolicyViolation(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _PersistedCandleRow:
    candle: Candle
    data_checksum: str | None


@dataclass(frozen=True, slots=True)
class _SyncRow:
    status: str
    last_stored_open_time_ms: int | None
    last_stored_close_boundary_ms: int | None


class _ReadOnlyExecutor:
    """Narrow execution guard; only ORM SELECT and fixed transaction control pass."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.query_count = 0

    def execute(self, statement: Any, parameters: Mapping[str, object] | None = None) -> Any:
        if isinstance(statement, Select):
            pass
        elif isinstance(statement, TextClause):
            normalized = " ".join(statement.text.upper().split())
            if normalized != _TRANSACTION_CONTROL:
                raise ReadOnlyPolicyViolation("MARKET_DATA_READ_ONLY_VIOLATION")
        else:
            raise ReadOnlyPolicyViolation("MARKET_DATA_READ_ONLY_VIOLATION")
        self.query_count += 1
        return self.session.execute(statement, parameters or {})


class PaperProductionMarketDataReader(Protocol):
    def read_clock_ms(self, executor: _ReadOnlyExecutor) -> int: ...
    def read_sync_rows(
        self, executor: _ReadOnlyExecutor, symbols: Sequence[str], timeframes: Sequence[str]
    ) -> Mapping[tuple[str, str], _SyncRow]: ...
    def read_candles(
        self, executor: _ReadOnlyExecutor, symbol: str, timeframe: str, limit: int
    ) -> Sequence[_PersistedCandleRow]: ...


class SqlAlchemyPaperProductionMarketDataReader:
    """Revision-0008-compatible SELECT allowlist."""

    def read_clock_ms(self, executor: _ReadOnlyExecutor) -> int:
        # Kept as ORM SELECT so the runtime guard does not admit arbitrary text.
        result = executor.execute(select(text("CAST(EXTRACT(EPOCH FROM transaction_timestamp()) * 1000 AS BIGINT)")))
        return int(result.scalar_one())

    def read_sync_rows(
        self, executor: _ReadOnlyExecutor, symbols: Sequence[str], timeframes: Sequence[str]
    ) -> Mapping[tuple[str, str], _SyncRow]:
        statement = select(
            MarketDataSyncState.symbol,
            MarketDataSyncState.timeframe,
            MarketDataSyncState.status,
            MarketDataSyncState.last_stored_open_time_ms,
            MarketDataSyncState.last_stored_close_boundary_ms,
        ).where(
            MarketDataSyncState.symbol.in_(symbols),
            MarketDataSyncState.timeframe.in_(timeframes),
        )
        values: dict[tuple[str, str], _SyncRow] = {}
        for row in executor.execute(statement):
            values[(row.symbol, row.timeframe)] = _SyncRow(
                str(row.status), row.last_stored_open_time_ms,
                row.last_stored_close_boundary_ms,
            )
        return values

    def read_candles(
        self, executor: _ReadOnlyExecutor, symbol: str, timeframe: str, limit: int
    ) -> Sequence[_PersistedCandleRow]:
        model = CANDLE_MODELS[timeframe]
        statement = (
            select(model)
            .where(model.symbol == symbol, model.is_closed.is_(True))
            .order_by(model.open_time_ms.desc())
            .limit(limit)
        )
        rows = list(executor.execute(statement).scalars())
        rows.reverse()
        return tuple(self._map_row(row, timeframe) for row in rows)

    @staticmethod
    def _map_row(row: CandleTableMixin, timeframe: str) -> _PersistedCandleRow:
        return _PersistedCandleRow(
            Candle(
                symbol=row.symbol,
                timeframe=timeframe,
                open_time_ms=row.open_time_ms,
                close_time_ms=row.close_time_ms,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
                quote_volume=row.quote_volume,
                trades_count=row.trades_count,
                is_closed=True,
                source=row.source,
            ),
            row.data_checksum,
        )


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _finding(
    code: PaperProductionMarketDataFindingCode,
    symbol: str | None = None,
    timeframe: str | None = None,
    count: int = 0,
) -> PaperProductionMarketDataFinding:
    return PaperProductionMarketDataFinding(code, symbol, timeframe, count)


_OUTCOME_FINDING: Final = {
    PaperProductionMarketDataOutcome.READY: PaperProductionMarketDataFindingCode.MARKET_DATA_READY,
    PaperProductionMarketDataOutcome.WITHIN_GRACE_READY: PaperProductionMarketDataFindingCode.MARKET_DATA_WITHIN_GRACE_READY,
    PaperProductionMarketDataOutcome.STALE: PaperProductionMarketDataFindingCode.MARKET_DATA_STALE,
    PaperProductionMarketDataOutcome.GAP_DETECTED: PaperProductionMarketDataFindingCode.MARKET_DATA_GAP,
    PaperProductionMarketDataOutcome.DUPLICATE_DETECTED: PaperProductionMarketDataFindingCode.MARKET_DATA_DUPLICATE,
    PaperProductionMarketDataOutcome.CHECKSUM_CONFLICT: PaperProductionMarketDataFindingCode.MARKET_DATA_CHECKSUM_CONFLICT,
    PaperProductionMarketDataOutcome.FUTURE_CANDLE_DETECTED: PaperProductionMarketDataFindingCode.MARKET_DATA_FUTURE_CANDLE,
    PaperProductionMarketDataOutcome.INCOMPLETE_TIMEFRAME_SET: PaperProductionMarketDataFindingCode.MARKET_DATA_MISSING_TIMEFRAME,
    PaperProductionMarketDataOutcome.INSUFFICIENT_HISTORY: PaperProductionMarketDataFindingCode.MARKET_DATA_INSUFFICIENT_HISTORY,
    PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED: PaperProductionMarketDataFindingCode.MARKET_DATA_TARGET_NOT_ALLOWED,
    PaperProductionMarketDataOutcome.BOUNDED_LIMIT_EXCEEDED: PaperProductionMarketDataFindingCode.MARKET_DATA_LIMIT_EXCEEDED,
    PaperProductionMarketDataOutcome.READ_ONLY_POLICY_VIOLATION: PaperProductionMarketDataFindingCode.MARKET_DATA_READ_ONLY_VIOLATION,
    PaperProductionMarketDataOutcome.CANCELLED: PaperProductionMarketDataFindingCode.MARKET_DATA_CANCELLED,
    PaperProductionMarketDataOutcome.SCHEMA_NOT_SUPPORTED: PaperProductionMarketDataFindingCode.MARKET_DATA_SAFE_FAILURE,
    PaperProductionMarketDataOutcome.SAFE_FAILURE: PaperProductionMarketDataFindingCode.MARKET_DATA_SAFE_FAILURE,
}


class PaperProductionMarketDataInputAdapter:
    """Read an immutable, bounded production market-data snapshot for PAPER."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        reader: PaperProductionMarketDataReader | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if session_factory is None:
            raise TypeError("session_factory is required")
        if monotonic is None:
            from time import monotonic as system_monotonic
            monotonic = system_monotonic
        self._session_factory = session_factory
        self._reader = reader or SqlAlchemyPaperProductionMarketDataReader()
        self._monotonic = monotonic

    @staticmethod
    def _validated_scope(scope: PaperProductionMarketDataScope) -> tuple[tuple[str, ...], tuple[str, ...]] | PaperProductionMarketDataOutcome:
        if not scope.symbols or not scope.timeframes:
            return PaperProductionMarketDataOutcome.INCOMPLETE_TIMEFRAME_SET
        try:
            symbols = tuple(normalize_market_symbol(value) for value in scope.symbols)
        except (TypeError, ValueError):
            return PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED
        timeframes = tuple(scope.timeframes)
        if len(set(symbols)) != len(symbols) or any(value not in SYMBOL_ALLOWLIST for value in symbols):
            return PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED
        if len(set(timeframes)) != len(timeframes) or any(value not in TIMEFRAME_ALLOWLIST for value in timeframes):
            return PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED
        if (
            len(symbols) > MAX_SYMBOLS_PER_REQUEST
            or len(timeframes) > MAX_TIMEFRAMES_PER_REQUEST
            or not isinstance(scope.candles_per_timeframe, int)
            or isinstance(scope.candles_per_timeframe, bool)
            or scope.candles_per_timeframe < 1
            or scope.candles_per_timeframe > MAX_CANDLES_PER_TIMEFRAME
            or len(symbols) * len(timeframes) * scope.candles_per_timeframe > MAX_ROWS_PER_REQUEST
            or scope.candles_per_timeframe * max(timeframe_to_milliseconds(value) for value in timeframes) > MAX_TIME_RANGE_MS
        ):
            return PaperProductionMarketDataOutcome.BOUNDED_LIMIT_EXCEEDED
        return (
            tuple(sorted(symbols, key=SYMBOL_ALLOWLIST.index)),
            tuple(sorted(timeframes, key=_TIMEFRAME_ORDER.__getitem__)),
        )

    @staticmethod
    def _cancelled(token: CancellationToken | None) -> None:
        if token is not None and token.is_set():
            raise _Cancelled("MARKET_DATA_CANCELLED")

    @staticmethod
    def _failure(
        outcome: PaperProductionMarketDataOutcome,
        request_id: str,
        *,
        as_of_ms: int | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        count: int = 0,
        query_count: int = 0,
        rows_read: int = 0,
        duration_ms: float = 0.0,
    ) -> PaperProductionMarketDataOutcomeResult:
        readiness = (
            PaperProductionMarketDataReadiness.CANCELLED
            if outcome is PaperProductionMarketDataOutcome.CANCELLED
            else PaperProductionMarketDataReadiness.NOT_READY
        )
        return PaperProductionMarketDataOutcomeResult(
            outcome, readiness, request_id, as_of_ms, None,
            (_finding(_OUTCOME_FINDING[outcome], symbol, timeframe, count),),
            query_count, rows_read, duration_ms,
            outcome is not PaperProductionMarketDataOutcome.READ_ONLY_POLICY_VIOLATION,
            False,
        )

    def read(
        self,
        request: PaperProductionMarketDataRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> PaperProductionMarketDataOutcomeResult:
        started = self._monotonic()
        validated = self._validated_scope(request.scope)
        if isinstance(validated, PaperProductionMarketDataOutcome):
            return self._failure(validated, request.request_id)
        symbols, timeframes = validated
        if request.as_of_ms is not None and (
            not isinstance(request.as_of_ms, int)
            or isinstance(request.as_of_ms, bool)
            or request.as_of_ms <= 0
        ):
            return self._failure(PaperProductionMarketDataOutcome.SAFE_FAILURE, request.request_id)

        executor: _ReadOnlyExecutor | None = None
        rows_read = 0
        as_of_ms = request.as_of_ms
        try:
            self._cancelled(cancellation)
            with self._session_factory() as session:
                executor = _ReadOnlyExecutor(session)
                with session.begin():
                    executor.execute(text(_TRANSACTION_CONTROL))
                    if as_of_ms is None:
                        as_of_ms = self._reader.read_clock_ms(executor)
                    self._cancelled(cancellation)
                    sync_rows = self._reader.read_sync_rows(executor, symbols, timeframes)
                    snapshots: list[PaperProductionMarketDataSnapshot] = []
                    any_grace = False

                    for symbol in symbols:
                        candle_groups: list[tuple[str, tuple[Candle, ...]]] = []
                        freshness_states: list[tuple[str, str]] = []
                        continuity_states: list[tuple[str, str]] = []
                        latest_opens: list[tuple[str, int]] = []
                        latest_closes: list[tuple[str, int]] = []
                        watermark_material: list[object] = []
                        for timeframe in timeframes:
                            self._cancelled(cancellation)
                            persisted = tuple(self._reader.read_candles(
                                executor, symbol, timeframe,
                                request.scope.candles_per_timeframe + 1,
                            ))
                            rows_read += len(persisted)
                            sync = sync_rows.get((symbol, timeframe))
                            if not persisted or sync is None:
                                return self._failure(
                                    PaperProductionMarketDataOutcome.INCOMPLETE_TIMEFRAME_SET,
                                    request.request_id, as_of_ms=as_of_ms,
                                    symbol=symbol, timeframe=timeframe,
                                    query_count=executor.query_count, rows_read=rows_read,
                                    duration_ms=(self._monotonic() - started) * 1000,
                                )

                            expected_open = latest_expected_closed_open_time_ms(timeframe, as_of_ms)
                            max_closed_close = close_boundary_ms(expected_open, timeframe) - 1
                            identities: dict[int, tuple[str, tuple[str, ...]]] = {}
                            canonical: list[Candle] = []
                            for item in persisted:
                                candle = item.candle
                                calculated = candle_checksum(candle)
                                if candle.open_time_ms > expected_open or candle.close_time_ms > max_closed_close:
                                    return self._failure(
                                        PaperProductionMarketDataOutcome.FUTURE_CANDLE_DETECTED,
                                        request.request_id, as_of_ms=as_of_ms,
                                        symbol=symbol, timeframe=timeframe,
                                        query_count=executor.query_count, rows_read=rows_read,
                                        duration_ms=(self._monotonic() - started) * 1000,
                                    )
                                stored_checksum = item.data_checksum
                                if stored_checksum is not None and (
                                    len(stored_checksum) != 64
                                    or any(value not in "0123456789abcdef" for value in stored_checksum)
                                ):
                                    return self._failure(
                                        PaperProductionMarketDataOutcome.CHECKSUM_CONFLICT,
                                        request.request_id, as_of_ms=as_of_ms,
                                        symbol=symbol, timeframe=timeframe,
                                        query_count=executor.query_count, rows_read=rows_read,
                                        duration_ms=(self._monotonic() - started) * 1000,
                                    )
                                identity_checksum = stored_checksum or calculated
                                content_identity = tuple(
                                    "" if value is None else str(value)
                                    for value in candle.market_values()
                                )
                                previous = identities.get(candle.open_time_ms)
                                if previous is not None:
                                    outcome = (
                                        PaperProductionMarketDataOutcome.DUPLICATE_DETECTED
                                        if previous == (identity_checksum, content_identity)
                                        else PaperProductionMarketDataOutcome.CHECKSUM_CONFLICT
                                    )
                                    return self._failure(
                                        outcome, request.request_id, as_of_ms=as_of_ms,
                                        symbol=symbol, timeframe=timeframe, count=1,
                                        query_count=executor.query_count, rows_read=rows_read,
                                        duration_ms=(self._monotonic() - started) * 1000,
                                    )
                                identities[candle.open_time_ms] = (identity_checksum, content_identity)
                                canonical.append(candle)

                            canonical = canonical[-request.scope.candles_per_timeframe:]
                            if len(canonical) < request.scope.candles_per_timeframe:
                                return self._failure(
                                    PaperProductionMarketDataOutcome.INSUFFICIENT_HISTORY,
                                    request.request_id, as_of_ms=as_of_ms,
                                    symbol=symbol, timeframe=timeframe,
                                    count=len(canonical), query_count=executor.query_count,
                                    rows_read=rows_read,
                                    duration_ms=(self._monotonic() - started) * 1000,
                                )
                            if any(
                                current.open_time_ms != expected_next_open_time(previous.open_time_ms, timeframe)
                                for previous, current in zip(canonical, canonical[1:])
                            ):
                                return self._failure(
                                    PaperProductionMarketDataOutcome.GAP_DETECTED,
                                    request.request_id, as_of_ms=as_of_ms,
                                    symbol=symbol, timeframe=timeframe,
                                    query_count=executor.query_count, rows_read=rows_read,
                                    duration_ms=(self._monotonic() - started) * 1000,
                                )
                            latest = canonical[-1]
                            if latest.open_time_ms > expected_open:
                                return self._failure(
                                    PaperProductionMarketDataOutcome.FUTURE_CANDLE_DETECTED,
                                    request.request_id, as_of_ms=as_of_ms,
                                    symbol=symbol, timeframe=timeframe,
                                    query_count=executor.query_count, rows_read=rows_read,
                                    duration_ms=(self._monotonic() - started) * 1000,
                                )

                            if latest.open_time_ms == expected_open and sync.status in _READY_SYNC_STATES:
                                freshness = "CURRENT"
                            else:
                                deadline = close_boundary_ms(expected_open, timeframe) + FRESHNESS_ALLOWANCE_MS[timeframe]
                                within_grace = (
                                    latest.open_time_ms == expected_open - timeframe_to_milliseconds(timeframe)
                                    and as_of_ms <= deadline
                                    and sync.status in _READY_SYNC_STATES
                                )
                                if not within_grace:
                                    return self._failure(
                                        PaperProductionMarketDataOutcome.STALE,
                                        request.request_id, as_of_ms=as_of_ms,
                                        symbol=symbol, timeframe=timeframe,
                                        query_count=executor.query_count, rows_read=rows_read,
                                        duration_ms=(self._monotonic() - started) * 1000,
                                    )
                                freshness = "WITHIN_GRACE"
                                any_grace = True

                            candle_values = tuple(canonical)
                            candle_groups.append((timeframe, candle_values))
                            freshness_states.append((timeframe, freshness))
                            continuity_states.append((timeframe, "CONTIGUOUS"))
                            latest_opens.append((timeframe, latest.open_time_ms))
                            latest_closes.append((timeframe, latest.close_time_ms))
                            watermark_material.append((
                                timeframe,
                                tuple(
                                    (value.open_time_ms, value.close_time_ms, identities[value.open_time_ms])
                                    for value in candle_values
                                ),
                            ))

                        watermark_id = _fingerprint((AUTHORITATIVE_SOURCE, symbol, as_of_ms, watermark_material))
                        watermark = PaperProductionMarketDataWatermark(
                            AUTHORITATIVE_SOURCE, as_of_ms, tuple(latest_opens),
                            tuple(latest_closes), watermark_id,
                        )
                        snapshot_id = _fingerprint((request.request_id, symbol, timeframes, as_of_ms, watermark_id))
                        snapshots.append(PaperProductionMarketDataSnapshot(
                            AUTHORITATIVE_SOURCE, symbol, timeframes, as_of_ms,
                            snapshot_id, watermark, tuple(candle_groups),
                            tuple(freshness_states), tuple(continuity_states),
                        ))

                    self._cancelled(cancellation)
                    outcome = (
                        PaperProductionMarketDataOutcome.WITHIN_GRACE_READY
                        if any_grace else PaperProductionMarketDataOutcome.READY
                    )
                    data = PaperProductionMarketDataInput(
                        request.request_id, AUTHORITATIVE_SOURCE, as_of_ms, tuple(snapshots)
                    )
                    finding = _finding(_OUTCOME_FINDING[outcome])
                    return PaperProductionMarketDataOutcomeResult(
                        outcome, PaperProductionMarketDataReadiness.READY,
                        request.request_id, as_of_ms, data, (finding,),
                        executor.query_count, rows_read,
                        (self._monotonic() - started) * 1000,
                    )
        except _Cancelled:
            return self._failure(
                PaperProductionMarketDataOutcome.CANCELLED, request.request_id,
                as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read,
                duration_ms=(self._monotonic() - started) * 1000,
            )
        except ReadOnlyPolicyViolation:
            return self._failure(
                PaperProductionMarketDataOutcome.READ_ONLY_POLICY_VIOLATION,
                request.request_id, as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read,
                duration_ms=(self._monotonic() - started) * 1000,
            )
        except Exception as exc:
            code = getattr(getattr(exc, "orig", None), "sqlstate", None)
            outcome = (
                PaperProductionMarketDataOutcome.SCHEMA_NOT_SUPPORTED
                if code in {"42P01", "42703"}
                else PaperProductionMarketDataOutcome.SAFE_FAILURE
            )
            return self._failure(
                outcome, request.request_id, as_of_ms=as_of_ms,
                query_count=executor.query_count if executor else 0,
                rows_read=rows_read,
                duration_ms=(self._monotonic() - started) * 1000,
            )


__all__ = [
    "ADAPTER_SCHEMA_VERSION", "ADAPTER_VERSION", "AUTHORITATIVE_SOURCE",
    "SYMBOL_ALLOWLIST", "TIMEFRAME_ALLOWLIST", "MAX_SYMBOLS_PER_REQUEST",
    "MAX_TIMEFRAMES_PER_REQUEST", "MAX_CANDLES_PER_TIMEFRAME",
    "MAX_ROWS_PER_REQUEST", "MAX_TIME_RANGE_MS",
    "REQUIRED_SOURCE_EVIDENCE_HASHES",
    "PaperProductionMarketDataRequest", "PaperProductionMarketDataScope",
    "PaperProductionMarketDataWatermark", "PaperProductionMarketDataSnapshot",
    "PaperProductionMarketDataInput", "PaperProductionMarketDataFinding",
    "PaperProductionMarketDataOutcome", "PaperProductionMarketDataOutcomeResult",
    "PaperProductionMarketDataReadiness", "PaperProductionMarketDataFindingCode",
    "PaperProductionMarketDataInputAdapter",
    "PaperProductionMarketDataReader", "SqlAlchemyPaperProductionMarketDataReader",
    "ReadOnlyPolicyViolation",
]
