from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.sql.elements import TextClause

from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataBoundaryStatus,
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_provider,
)
from app.market_reader.engine_trend.postgres_candle_adapter import (
    PostgresCandleAdapterError,
    PostgresMarketCandlesProvider,
)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class FakeConnection:
    def __init__(
        self, rows: list[dict[str, object]] | None = None, error: Exception | None = None
    ) -> None:
        self.rows = rows or []
        self.error = error
        self.calls: list[tuple[TextClause, dict[str, object]]] = []

    def execute(
        self, statement: TextClause, parameters: dict[str, object]
    ) -> FakeResult:
        self.calls.append((statement, parameters))
        if self.error:
            raise self.error
        return FakeResult(self.rows)


def make_request(**changes: object) -> CandleDataRequest:
    values: dict[str, object] = {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "limit": 2,
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": "2026-01-01T01:00:00Z",
    }
    values.update(changes)
    return CandleDataRequest(**values)  # type: ignore[arg-type]


def db_rows() -> list[dict[str, object]]:
    return [
        {
            "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 104,
            "volume": 12.5,
            "symbol": "BTCUSDT",
            "interval": "15m",
        }
    ]


def test_load_rows_executes_parameterized_read_query() -> None:
    connection = FakeConnection(db_rows())
    provider = PostgresMarketCandlesProvider(connection)
    rows = provider.load_rows(make_request())

    statement, parameters = connection.calls[0]
    sql = " ".join(str(statement).split())
    assert "FROM market_candles WHERE" in sql
    assert "symbol = :symbol" in sql
    assert "interval = :interval" in sql
    assert "open_time >= :period_start" in sql
    assert "open_time <= :period_end" in sql
    assert "ORDER BY open_time ASC" in sql
    assert "LIMIT :limit" in sql
    assert parameters == {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "limit": 2,
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-01-01T01:00:00Z",
    }
    assert rows[0] == {
        "timestamp": db_rows()[0]["open_time"],
        "open": 100,
        "high": 105,
        "low": 99,
        "close": 104,
        "volume": 12.5,
        "symbol": "BTCUSDT",
        "interval": "15m",
    }


def test_optional_period_bounds_are_omitted_and_rows_feed_batch() -> None:
    connection = FakeConnection(db_rows())
    rows = PostgresMarketCandlesProvider(connection).load_rows(
        make_request(start_time=None, end_time=None)
    )
    sql = str(connection.calls[0][0])
    assert ":period_start" not in sql
    assert ":period_end" not in sql
    batch = build_candle_data_batch(make_request(), rows)
    assert batch.status is CandleDataBoundaryStatus.READY
    assert batch.candles[0].close == 104.0


def test_empty_result_becomes_boundary_empty() -> None:
    result = run_engine_trend_from_provider(
        PostgresMarketCandlesProvider(FakeConnection()), make_request()
    )
    assert result.status is CandleDataBoundaryStatus.EMPTY
    assert result.batch.rows == ()


def test_database_exception_is_explicit_and_boundary_fail_closed() -> None:
    provider = PostgresMarketCandlesProvider(
        FakeConnection(error=RuntimeError("database unavailable"))
    )
    try:
        provider.load_rows(make_request())
    except PostgresCandleAdapterError as exc:
        assert "market_candles" in str(exc)
    else:
        raise AssertionError("adapter exception was not raised")

    result = run_engine_trend_from_provider(provider, make_request())
    assert result.status is CandleDataBoundaryStatus.PROVIDER_ERROR
    assert result.batch.candles == ()
    assert result.errors[0] == "PROVIDER_ERROR"


def test_constructor_requires_injected_connection() -> None:
    try:
        PostgresMarketCandlesProvider(None)
    except TypeError as exc:
        assert str(exc) == "connection is required"
    else:
        raise AssertionError("missing connection was accepted")
