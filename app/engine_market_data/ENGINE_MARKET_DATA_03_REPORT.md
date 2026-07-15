# ENGINE-MARKET-DATA-03 — Historical Backfill To Current Date

## Outcome

The stage adds a PostgreSQL historical backfill that ends at the last fully
closed UTC candle for each configured symbol and timeframe. It is a market-data
operation only. It does not invoke analysis, setup, or any trading subsystem.

## Rolling windows

Finite rolling windows keep synchronization bounded while retaining precise
intraday context and progressively longer higher-timeframe context:

| Timeframe | Candles |
|---|---:|
| 1m | 10,000 |
| 5m | 10,000 |
| 15m | 10,000 |
| 1h | 5,000 |
| 4h | 3,000 |
| 1d | 1,500 |

`open_time_ms` and `close_time_ms` are authoritative UTC millisecond fields.
For duration `D`, the latest closed open is `floor(now_ms / D) * D - D`.
The window starts `(limit - 1) * D` before that open and therefore contains
exactly `limit` aligned opens. No local or naive datetime participates.

## Missing-only and restart safety

Each planned window is checked with `CandleRepository.find_missing_open_times`.
Adjacent missing opens become one range; ranges are split into at most 1,000
candle REST requests. Responses are intersected with the exact missing-open set.
Existing rows are not downloaded. A completed rerun performs no kline request
and reports `NOOP_ALREADY_FILLED`.

Only candles marked closed, ending before `now_ms`, and at or before the planned
closed boundary are accepted. Invalid OHLCV is rejected by the strict `Candle`
model. No synthetic, interpolated, or zero-filled replacement is created.
Persistence reuses the checksum-aware PostgreSQL `ON CONFLICT` upsert from stage
02, and completeness is queried again after the write.

## Operations and reporting

Run `python -m app.engine_market_data.historical_backfill_cli --help` for all
options. `--dry-run` only builds the UTC plan and touches neither REST klines nor
PostgreSQL. `--verify-only` queries the planned database windows without
downloading or writing candles. `--report-json` and `--report-md` write machine-
and human-readable reports containing per-task counts, REST activity, rejected
candles, final gaps, and safety flags.

This stage uses public Binance market data without credentials. It creates no
setup candidates, signals, orders, positions, risk decisions, or PnL and imports
no downstream engine.
