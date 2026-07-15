# engine_market_data

`engine_market_data` is the independent live market-data boundary introduced by
**ENGINE-MARKET-DATA-01**. It obtains Binance public klines, validates and
normalizes them, stores runtime candle state, detects/recover gaps, measures
exchange clock drift, and exposes clean candle windows.

## Responsibilities

- `BinancePublicRestClient`: public `/api/v3/klines` and `/api/v3/time` calls,
  retry/backoff, and REST-to-`Candle` mapping.
- `BinanceKlineWebSocketClient`: public kline subscriptions, exchange `x` flag
  mapping, disconnect health, and reconnect policy.
- `CandleStream`: raw-update ingestion, continuity checks, recovery, and
  `ClosedCandleEvent` publication.
- `CandleStore`: idempotent runtime storage and closed-only query methods.
- `GapDetector` / `GapRecovery`: exact missing-open-time detection and public
  REST recovery. Missing candles are never synthesized, interpolated, zeroed,
  or silently ignored.
- `ExchangeTimeSync`: public server-time drift and exchange-adjusted time.
- `MarketDataSnapshot`: immutable analysis-ready read model with
`future_bars_used=False` and an `enough_data` flag.

## ENGINE-MARKET-DATA-02

Closed Binance public-market candles are stored through SQLAlchemy 2.x in PostgreSQL
tables `candles_1m`, `candles_5m`, `candles_15m`, `candles_1h`, `candles_4h` and
`candles_1d`. The existing Alembic chain owns their lifecycle.

Time policy is UTC-only. `open_time_ms` and `close_time_ms` are authoritative;
`TIMESTAMPTZ` columns are readable/indexable projections. Local timezone conversion
is not part of scheduling or persistence.

After the safety delay, a 15m boundary reconciles its 15m candle, three 5m candles
and fifteen 1m candles. The 1h, 4h and 1d boundaries each reconcile their latest
closed candle. Events are deduplicated by timeframe and boundary open time.

Warmup builds the desired latest closed window for every symbol/timeframe. Both
warmup and boundary reconciliation ask PostgreSQL which opens are missing before
calling REST. Non-contiguous gaps are fetched separately, existing rows are not
re-downloaded, and completeness is checked again after idempotent upsert.

Only closed candles enter these tables. Open websocket updates are never persisted.
Recovery never creates synthetic, interpolated or zero-filled candles. This module
contains no market analysis or trading logic and does not invoke downstream engines.

## ENGINE-MARKET-DATA-03 — Historical Backfill To Current Date

Historical backfill fills a bounded rolling PostgreSQL window through the latest
fully closed UTC candle. The fixed limits are 10,000 candles for 1m, 5m, and 15m;
5,000 for 1h; 3,000 for 4h; and 1,500 for 1d. These windows preserve detailed
intraday context and longer higher-timeframe context without downloading an
exchange's entire history.

For every timeframe duration `D`, the latest closed open is
`floor(now_ms / D) * D - D`; the window contains exactly the configured number
of aligned `open_time_ms` values ending there. Millisecond exchange timestamps
remain the source of truth, and all readable datetimes are timezone-aware UTC.

PostgreSQL is asked for the exact missing opens before any kline download.
Contiguous gaps are grouped and split into public REST batches of no more than
1,000. Every response is filtered against the exact missing set and closed
boundary before the existing checksum-aware idempotent upsert. Completeness is
verified after writing. Thus a completed rerun is a no-op and existing candles
are not downloaded again. Missing exchange history remains an explicit gap;
synthetic, zero, and interpolated candles are never generated.

The CLI is available as
`python -m app.engine_market_data.historical_backfill_cli`. `--dry-run` builds
the plan without kline downloads or database writes; `--verify-only` checks the
database without downloading or writing. JSON and Markdown audit reports are
available through `--report-json` and `--report-md`.

## Closed-candle-only rule

Websocket updates with Binance `k.x=false` may be retained only in the store's
raw state. They are excluded from `get_candles`, latest-closed queries,
`ClosedCandleEvent`, and snapshots. A closed candle cannot be overwritten by a
later unclosed update. Only exchange `k.x=true` marks websocket data closed.

## Health states

`OK`, `DEGRADED`, `STALE`, `DISCONNECTED`, `RECOVERING`, and `ERROR` cover gaps,
failed recovery, disconnects, clock drift, freshness, invalid OHLCV, and
duplicate conflicts. Failed recovery degrades health but leaves the stream
usable and never invents market data.

## Boundary

This package uses no API keys and no private Binance endpoints. It does not
import or run `engine_analysis`; create setup candidates or signals; calculate
risk, size, PnL; place orders; or perform paper/live trading. Connecting these
snapshots to analysis belongs to `ENGINE-ANALYSIS-ONLINE-01`.

## Public interfaces

The package root exports `Candle`, `CandleStore`, `CandleStream`,
`ClosedCandleEvent`, both Binance public clients, `GapDetector`, `GapRecovery`,
`ExchangeTimeSync`, `MarketDataSnapshot`, `MarketDataHealth`, and timeframe
helpers. Transports are injectable so unit tests never require the network.

Status: **ENGINE-MARKET-DATA-01 implemented**.

## ENGINE-MARKET-DATA-04 — Continuous DB Sync Daemon / Freshness Monitor / 24/7 Service

`scripts/engine_market_data_continuous_sync.py` is an independent long-lived
service. It uses Binance public server time and public REST klines, and writes
only real candles whose close is strictly before exchange time. It never writes
the current unclosed candle and never synthesizes, interpolates, or zero-fills.

Startup warmup reads the latest stored candle. An empty table receives its
configured rolling depth; an existing table receives only opens after its latest
row through the latest expected close. A rolling gap scan also checks internal
holes. Exact missing opens are grouped into REST batches, filtered against the
requested set, upserted idempotently, and checked again.

The UTC scheduler covers `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`. It emits each
symbol/timeframe boundary once after its freshness allowance (10s, 15s, 20s,
60s, 90s, and 120s respectively). Short-timeframe gaps are checked every five
minutes, `1h`/`4h` hourly, and `1d` daily. Network or database failures use
bounded exponential backoff with jitter.

`market_data_sync_state` persists expected/stored boundaries, lag, status,
missing/recovering counts, attempt/success/error timestamps, batch counters,
source, and daemon instance. Statuses are `OK`, `STALE`, `GAP_DETECTED`,
`RECOVERING`, `DEGRADED`, `DISCONNECTED`, `ERROR`, and `NOT_CONFIGURED`.

Once mode:

```bash
python scripts/engine_market_data_continuous_sync.py --symbols BTCUSDT --timeframes 15m --once --warmup --health-report reports/engine_market_data/continuous_sync/latest_health.json
```

Dry-run computes expected/missing opens without REST kline downloads or writes:

```bash
python scripts/engine_market_data_continuous_sync.py --symbols BTCUSDT --timeframes 1m,5m,15m,1h,4h,1d --dry-run --once
```

Docker Compose and systemd instructions are in
`docs/operations/engine_market_data_04_docker_compose.md` and
`docs/operations/engine_market_data_04_systemd.md`. Both restart automatically.
After a reboot or downtime, startup warmup derives truth from PostgreSQL and
Binance and catches up without a manual backfill.

This runtime does not import or run analysis, setup, strategy, risk, paper,
execution, position, or exit engines. It creates no signals, levels, orders,
positions, outcomes, or PnL. Codex, VSCode, notebooks, and interactive terminals
are development tools, not runtime dependencies.
