# ENGINE-TREND-10 — PostgreSQL Candle Adapter Implementation for `market_candles`

## Files created

- `app/market_reader/engine_trend/postgres_candle_adapter.py`
- `tests/test_engine_trend_10_postgres_candle_adapter.py`
- `reports/engine_trend/engine_trend_10_postgresql_candle_adapter_report.md`

No existing engine core file was changed.

## Implementation

`PostgresMarketCandlesProvider` implements the `CandleDataProvider`-compatible
`load_rows(request)` method. `PostgresCandleAdapterError` exposes database read
failures to the existing provider boundary, which converts them to the
fail-closed `PROVIDER_ERROR` result.

The provider executes one parameterized, read-only `SELECT` against
`market_candles`. It filters by `symbol` and `interval`, applies optional
`start_time` and `end_time` filters, orders by `open_time ASC`, and applies the
request `limit`. The `end_time` boundary is **inclusive** (`open_time <=
:period_end`). A missing optional period boundary omits only that filter.

Rows are mapped as follows:

- `open_time` -> `timestamp`
- `open`, `high`, `low`, `close`, `volume` -> same-named engine row fields
- `symbol`, `interval` -> boundary metadata used by quality checks

The SQLAlchemy-compatible connection is supplied explicitly to the constructor.
The module does not discover credentials, build an engine, or connect during
import. Old L1/L2 code was not reused because the adapter belongs to the new
storage-neutral boundary and must not inherit legacy market or execution logic.

## Verification

- Adapter unit tests: `5 passed in 1.57s`.
- Relevant ENGINE-TREND suite: `198 passed in 6.26s` (final run).
- Full pytest: collection stopped after `2284 items` due to the pre-existing
  `StatisticsError: mean requires at least one data point` in
  `app/diagnostics/solusdt_sidecar_calibration_replay.py`; no unrelated fix was
  made in this stage.
- `py_compile`: passed.
- Whitespace/error check (`git diff --check`): passed.
- Forbidden trading scan: the requested broad expression reports two benign
  `ORDER` matches, both required `ORDER BY open_time ASC` assertions/SQL. No
  trading action, signal, or execution term was found.
- Old L1/L2 import scan: zero matches.
- Write SQL scan: zero matches.

## Known limitations

- The adapter implementation is read-only.
- There is no runtime trading connection.
- There is no live data connection.
- There is no automatic production DB configuration binding.
- Integration with real PostgreSQL requires an operational environment and
  credentials.
- Unit tests use a fake SQLAlchemy-compatible connection; real database type and
  schema compatibility remain for operational smoke verification.

## Next recommended stage

`ENGINE-TREND-11 — PostgreSQL Adapter Manual Smoke With Real market_candles`:
safely read small BTCUSDT, ETHUSDT, and SOLUSDT 15m periods and pass them through
`run_engine_trend_from_provider`, without connecting runtime trading.
