from __future__ import annotations

from contextlib import nullcontext
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import insert, text

from app.engine_market_data.candle import Candle
from app.engine_market_data.db.candle_repository import candle_checksum
from app.engine_market_data.db.candle_tables import Candle1m
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_paper import production_market_data as market


BASE_BOUNDARY = 2_000_000_000_000


class FakeSession:
    def __init__(self, *, execute_error: Exception | None = None):
        self.execute_error = execute_error
        self.statements: list[object] = []
        self.begin_count = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def begin(self):
        self.begin_count += 1
        return nullcontext()

    def execute(self, statement, parameters=None):
        self.statements.append(statement)
        if self.execute_error:
            raise self.execute_error
        return object()


def aligned_boundary(timeframe: str, seed: int = BASE_BOUNDARY) -> int:
    duration = timeframe_to_milliseconds(timeframe)
    return seed - seed % duration


def candle(symbol: str, timeframe: str, open_time: int, *, close: str = "10") -> Candle:
    duration = timeframe_to_milliseconds(timeframe)
    return Candle(
        symbol=symbol, timeframe=timeframe, open_time_ms=open_time,
        close_time_ms=open_time + duration - 1,
        open=Decimal("10"), high=Decimal("12"), low=Decimal("8"),
        close=Decimal(close), volume=Decimal("100"), quote_volume=Decimal("1000"),
        trades_count=10, is_closed=True, source="binance_public_rest",
    )


class FakeReader:
    def __init__(self, symbols=("BTCUSDT",), timeframes=("1m",), history=3, *, as_of=None):
        self.symbols = tuple(symbols)
        self.timeframes = tuple(timeframes)
        self.history = history
        self.as_of = as_of or aligned_boundary("1m") + 1
        self.rows: dict[tuple[str, str], list[market._PersistedCandleRow]] = {}
        self.sync: dict[tuple[str, str], market._SyncRow] = {}
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                duration = timeframe_to_milliseconds(timeframe)
                boundary = aligned_boundary(timeframe, self.as_of)
                latest_open = boundary - duration
                values = [
                    candle(symbol, timeframe, latest_open - duration * offset)
                    for offset in range(history - 1, -1, -1)
                ]
                self.rows[(symbol, timeframe)] = [
                    market._PersistedCandleRow(value, candle_checksum(value)) for value in values
                ]
                self.sync[(symbol, timeframe)] = market._SyncRow(
                    "OK", latest_open, boundary
                )
        self.fail: Exception | None = None
        self.clock_fail: Exception | None = None

    @staticmethod
    def _query(executor):
        executor.query_count += 1

    def read_clock_ms(self, executor):
        self._query(executor)
        if self.clock_fail:
            raise self.clock_fail
        return self.as_of

    def read_sync_rows(self, executor, symbols, timeframes):
        self._query(executor)
        if self.fail:
            raise self.fail
        return {
            key: value for key, value in self.sync.items()
            if key[0] in symbols and key[1] in timeframes
        }

    def read_candles(self, executor, symbol, timeframe, limit):
        self._query(executor)
        if self.fail:
            raise self.fail
        return tuple(self.rows.get((symbol, timeframe), ())[-limit:])


def adapter(reader: FakeReader, session: FakeSession | None = None, *, ticks=None):
    session = session or FakeSession()
    tick_values = iter(ticks or (1.0, 1.001))
    return market.PaperProductionMarketDataInputAdapter(
        lambda: session, reader=reader, monotonic=lambda: next(tick_values)
    ), session


def request(symbols=("BTCUSDT",), timeframes=("1m",), history=3, *, as_of=None):
    return market.PaperProductionMarketDataRequest(
        market.PaperProductionMarketDataScope(tuple(symbols), tuple(timeframes), history),
        "request-safe-001", as_of,
    )


def test_contract_constants_and_no_transport_or_business_dependency():
    source = Path(market.__file__).read_text(encoding="utf-8")
    assert market.AUTHORITATIVE_SOURCE == "PRODUCTION_PERSISTED_MARKET_DATA"
    assert market.SYMBOL_ALLOWLIST == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert market.TIMEFRAME_ALLOWLIST == ("1m", "5m", "15m", "1h", "4h", "1d")
    assert "binance_public_rest" not in source.lower()
    assert "binance_kline_ws" not in source.lower()
    for forbidden in ("CommandIngestion", "OrderExecution", "ControlledWorker", "PaperFill"):
        assert forbidden not in source


@pytest.mark.parametrize("name,expected", tuple(market.REQUIRED_SOURCE_EVIDENCE_HASHES.items()))
def test_required_source_evidence_hash_contract(name, expected):
    assert name and len(expected) == 64 and expected == expected.lower()
    int(expected, 16)


def test_all_public_contracts_are_immutable():
    scope = market.PaperProductionMarketDataScope(("BTCUSDT",), ("1m",), 3)
    value = market.PaperProductionMarketDataRequest(scope, "request", BASE_BOUNDARY)
    with pytest.raises(FrozenInstanceError):
        value.request_id = "changed"
    service, _ = adapter(FakeReader())
    result = service.read(value)
    assert result.readiness is market.PaperProductionMarketDataReadiness.READY
    with pytest.raises(FrozenInstanceError):
        result.outcome = market.PaperProductionMarketDataOutcome.STALE


@pytest.mark.parametrize("case", range(1300))
def test_1300_deterministic_closed_snapshot_matrix(case):
    symbol = market.SYMBOL_ALLOWLIST[case % 3]
    timeframe = market.TIMEFRAME_ALLOWLIST[(case // 3) % 6]
    history = case % 4 + 1
    as_of = aligned_boundary(timeframe, BASE_BOUNDARY + case * 1000) + 1
    reader = FakeReader((symbol,), (timeframe,), history, as_of=as_of)
    service, session = adapter(reader)
    first = service.read(request((symbol,), (timeframe,), history, as_of=as_of))
    service2, _ = adapter(reader)
    second = service2.read(request((symbol,), (timeframe,), history, as_of=as_of))
    assert first.outcome is market.PaperProductionMarketDataOutcome.READY
    assert first.data == second.data
    assert first.findings == second.findings
    candles = first.data.snapshots[0].candles[0][1]
    assert len(candles) == history
    assert all(value.is_closed and value.close_time_ms < as_of for value in candles)
    assert list(candles) == sorted(candles, key=lambda value: value.open_time_ms)
    assert session.begin_count == 1
    assert all("FOR UPDATE" not in str(value).upper() for value in session.statements)


def test_full_18_stream_snapshot_is_atomic_bounded_and_ordered():
    as_of = aligned_boundary("1d") + 1
    reader = FakeReader(market.SYMBOL_ALLOWLIST, market.TIMEFRAME_ALLOWLIST, 4, as_of=as_of)
    service, session = adapter(reader)
    result = service.read(request(market.SYMBOL_ALLOWLIST, market.TIMEFRAME_ALLOWLIST, 4, as_of=as_of))
    assert result.outcome is market.PaperProductionMarketDataOutcome.READY
    assert len(result.data.snapshots) == 3
    assert sum(len(groups) for groups in (item.candles for item in result.data.snapshots)) == 18
    assert result.query_count == 20  # transaction control + one health read + 18 candle reads
    assert result.rows_read == 72
    assert session.begin_count == 1


@pytest.mark.parametrize("offset", (-1, 0, 1, 9_999, 10_000))
def test_1m_before_at_and_within_grace_never_exposes_open_candle(offset):
    boundary = aligned_boundary("1m")
    as_of = boundary + offset
    expected_as_of = as_of if as_of > 0 else 1
    reader = FakeReader(as_of=expected_as_of)
    if offset >= 0:
        previous = boundary - 120_000
        values = [candle("BTCUSDT", "1m", previous)]
        reader.rows[("BTCUSDT", "1m")] = [market._PersistedCandleRow(values[0], candle_checksum(values[0]))]
        reader.sync[("BTCUSDT", "1m")] = market._SyncRow("OK", previous, previous + 60_000)
        result, _ = adapter(reader)
        outcome = result.read(request(history=1, as_of=as_of))
        assert outcome.outcome is market.PaperProductionMarketDataOutcome.WITHIN_GRACE_READY
        assert outcome.data.snapshots[0].candles[0][1][0].close_time_ms < boundary


def test_after_grace_is_stale_and_not_ready():
    boundary = aligned_boundary("1m")
    reader = FakeReader(as_of=boundary + 10_001)
    previous = boundary - 120_000
    value = candle("BTCUSDT", "1m", previous)
    reader.rows[("BTCUSDT", "1m")] = [market._PersistedCandleRow(value, candle_checksum(value))]
    reader.sync[("BTCUSDT", "1m")] = market._SyncRow("OK", previous, previous + 60_000)
    service, _ = adapter(reader)
    result = service.read(request(history=1, as_of=boundary + 10_001))
    assert result.outcome is market.PaperProductionMarketDataOutcome.STALE
    assert result.data is None


def test_future_candle_fails_closed_without_fallback():
    reader = FakeReader(history=2)
    duration = timeframe_to_milliseconds("1m")
    future_open = aligned_boundary("1m", reader.as_of)
    value = candle("BTCUSDT", "1m", future_open)
    reader.rows[("BTCUSDT", "1m")].append(market._PersistedCandleRow(value, candle_checksum(value)))
    result = adapter(reader)[0].read(request(history=2, as_of=reader.as_of))
    assert result.outcome is market.PaperProductionMarketDataOutcome.FUTURE_CANDLE_DETECTED
    assert result.data is None


def test_gap_duplicate_and_checksum_conflict_are_distinct_fail_closed_outcomes():
    gap_reader = FakeReader(history=3)
    del gap_reader.rows[("BTCUSDT", "1m")][1]
    assert adapter(gap_reader)[0].read(request(history=2, as_of=gap_reader.as_of)).outcome is market.PaperProductionMarketDataOutcome.GAP_DETECTED

    duplicate_reader = FakeReader(history=2)
    duplicate_reader.rows[("BTCUSDT", "1m")].append(duplicate_reader.rows[("BTCUSDT", "1m")][-1])
    assert adapter(duplicate_reader)[0].read(request(history=2, as_of=duplicate_reader.as_of)).outcome is market.PaperProductionMarketDataOutcome.DUPLICATE_DETECTED

    conflict_reader = FakeReader(history=2)
    item = conflict_reader.rows[("BTCUSDT", "1m")][-1]
    conflict_reader.rows[("BTCUSDT", "1m")].append(market._PersistedCandleRow(item.candle, "0" * 64))
    assert adapter(conflict_reader)[0].read(request(history=2, as_of=conflict_reader.as_of)).outcome is market.PaperProductionMarketDataOutcome.CHECKSUM_CONFLICT

    malformed_reader = FakeReader(history=2)
    item = malformed_reader.rows[("BTCUSDT", "1m")][-1]
    malformed_reader.rows[("BTCUSDT", "1m")][-1] = market._PersistedCandleRow(item.candle, "not-a-checksum")
    assert adapter(malformed_reader)[0].read(request(history=2, as_of=malformed_reader.as_of)).outcome is market.PaperProductionMarketDataOutcome.CHECKSUM_CONFLICT


def test_missing_timeframe_and_insufficient_history_are_distinct():
    missing = FakeReader(timeframes=("1m", "5m"), history=2, as_of=aligned_boundary("5m") + 1)
    del missing.rows[("BTCUSDT", "5m")]
    assert adapter(missing)[0].read(request(timeframes=("1m", "5m"), history=2, as_of=missing.as_of)).outcome is market.PaperProductionMarketDataOutcome.INCOMPLETE_TIMEFRAME_SET
    short = FakeReader(history=1)
    assert adapter(short)[0].read(request(history=2, as_of=short.as_of)).outcome is market.PaperProductionMarketDataOutcome.INSUFFICIENT_HISTORY


@pytest.mark.parametrize("symbols,timeframes,history,expected", [
    (("DOGEUSDT",), ("1m",), 1, market.PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT", "BTCUSDT"), ("1m",), 1, market.PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT",), ("30m",), 1, market.PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT",), ("1m", "1m"), 1, market.PaperProductionMarketDataOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT",), ("1m",), 0, market.PaperProductionMarketDataOutcome.BOUNDED_LIMIT_EXCEEDED),
    (("BTCUSDT",), ("1m",), market.MAX_CANDLES_PER_TIMEFRAME + 1, market.PaperProductionMarketDataOutcome.BOUNDED_LIMIT_EXCEEDED),
])
def test_allowlist_and_bounds_fail_closed(symbols, timeframes, history, expected):
    result = adapter(FakeReader())[0].read(request(symbols, timeframes, history, as_of=BASE_BOUNDARY))
    assert result.outcome is expected
    assert result.query_count == 0


def test_read_only_guard_rejects_insert_and_non_allowlisted_text():
    executor = market._ReadOnlyExecutor(FakeSession())
    with pytest.raises(market.ReadOnlyPolicyViolation):
        executor.execute(insert(Candle1m).values())
    with pytest.raises(market.ReadOnlyPolicyViolation):
        executor.execute(text("SELECT current_user"))
    assert executor.query_count == 0


class Token:
    def __init__(self, value=True): self.value = value
    def is_set(self): return self.value


def test_cancellation_closes_transaction_and_never_returns_partial_ready():
    reader = FakeReader()
    service, session = adapter(reader)
    result = service.read(request(as_of=reader.as_of), cancellation=Token())
    assert result.outcome is market.PaperProductionMarketDataOutcome.CANCELLED
    assert result.data is None
    assert session.closed is False  # cancellation happened before resource acquisition


@pytest.mark.parametrize("failure", [RuntimeError("db unavailable"), TimeoutError("statement timeout"), ValueError("mapping")])
def test_db_timeout_health_and_mapping_failures_are_safe(failure):
    reader = FakeReader()
    reader.fail = failure
    result = adapter(reader)[0].read(request(as_of=reader.as_of))
    assert result.outcome is market.PaperProductionMarketDataOutcome.SAFE_FAILURE
    assert result.data is None
    assert "traceback" not in str(result.safe_report()).lower()
    assert "sql" not in str(result.safe_report()).lower()


def test_clock_provider_failure_is_safe_and_explicit_as_of_bypasses_clock():
    reader = FakeReader()
    reader.clock_fail = RuntimeError("clock unavailable")
    assert adapter(reader)[0].read(request()).outcome is market.PaperProductionMarketDataOutcome.SAFE_FAILURE
    assert adapter(reader)[0].read(request(as_of=reader.as_of)).outcome is market.PaperProductionMarketDataOutcome.READY


def test_safe_report_contains_only_bounded_summary():
    reader = FakeReader(history=2)
    result = adapter(reader)[0].read(request(history=2, as_of=reader.as_of))
    report = result.safe_report()
    rendered = str(report).lower()
    assert report["row_counts"] == {"BTCUSDT": {"1m": 2}}
    assert report["read_only"] is True
    assert report["consistent_snapshot"] is True
    for forbidden in ("database_url", "password", "credential", "select ", "open\":", "close\":"):
        assert forbidden not in rendered


def test_revision_0008_selects_only_existing_market_data_models():
    assert set(market.CANDLE_MODELS) == set(market.TIMEFRAME_ALLOWLIST)
    assert market.MarketDataSyncState.__tablename__ == "market_data_sync_state"
    assert not any("paper" in model.__tablename__.lower() for model in market.CANDLE_MODELS.values())


def test_findings_cover_every_public_outcome_deterministically():
    assert set(market._OUTCOME_FINDING) == set(market.PaperProductionMarketDataOutcome)
    assert len({value.value for value in market.PaperProductionMarketDataFindingCode}) == len(market.PaperProductionMarketDataFindingCode)


def test_controlled_proof_harness_has_no_secret_or_mutation_arguments():
    source = Path("scripts/production_market_data_adapter_proof.py").read_text(encoding="utf-8")
    assert "--history" in source
    for forbidden in ("--database", "--password", "--env", "INSERT ", "UPDATE ", "DELETE ", "Binance"):
        assert forbidden not in source
