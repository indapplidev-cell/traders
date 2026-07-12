# ENGINE-TREND-13 — Engine Trend DB Preview Acceptance Pack

## Purpose

This pack freezes the confirmed real-PostgreSQL DB CLI preview as reproducible acceptance evidence. It adds documentation, a manifest, checksums, and an offline verification test; it does not change `engine_trend` behavior.

## Baseline commits

- `54800af` — ENGINE-TREND-09 storage discovery
- `fb63c22` — ENGINE-TREND-10 PostgreSQL candle adapter
- `1e244da` — ENGINE-TREND-11B successful operational smoke
- `247ff0f` — ENGINE-TREND-12 DB CLI preview
- `5044345` — successful real DB CLI smoke and committed evidence

## Confirmed PostgreSQL source

PostgreSQL 16.10 runs in container `traders-ml-postgres-1`, exposed on host port `5433`, with volume `traders_ml_traders_ml_postgres_data`. The read source is `public.market_candles`. No connection URL or credential is stored in this pack.

## Supported symbols and interval

The accepted input set is BTCUSDT, ETHUSDT, and SOLUSDT at 15m, with 96 candles per preview. Confirmed availability was 50,961 BTCUSDT rows, 50,962 ETHUSDT rows, and 50,962 SOLUSDT rows.

## Acceptance commands

Canonical PowerShell commands and runtime environment guidance are in `ENGINE_TREND_13_COMMANDS.md`.

## Acceptance artifacts

The manifest references the real preview/result pairs under `reports/engine_trend/db_cli_preview/`. They are immutable evidence/output, never a candle input source. SHA256 protects each referenced file against silent drift.

## Per-symbol acceptance results

| Symbol | Interval | Candles | Boundary | Regime | Confidence | Warnings/errors | Safety |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| BTCUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; runtime false; live false |
| ETHUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; runtime false; live false |
| SOLUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; runtime false; live false |

## Safety contract

Every accepted artifact remains fail-closed: no evaluated trade signal, no runtime-trading authorization, and no live-trading connection. The pack contains no DB write behavior, execution integration, or credentials. `engine_trend` is a market-context preview component, not a trading system.

## What this pack proves

- DB CLI can read real PostgreSQL `market_candles`.
- Provider boundary returns `READY`.
- `engine_trend` returns a safe `EngineTrendResult`.
- JSON artifacts are produced.
- Safety contract remains fail-closed.

## What this pack does not prove

- It does not prove trading edge.
- It does not prove profitable signals.
- It does not authorize runtime trading.
- It does not validate model training.
- It does not validate 1h/4h.
- It does not validate all symbols.

## Known limitations

Acceptance covers one committed 96-candle window per supported symbol at 15m. Results are `UNKNOWN` with confidence 0.3. Full pytest is not an acceptance gate because of the unrelated existing `solusdt_sidecar_calibration_replay.py` empty-data `StatisticsError`.

## Re-run instructions

Supply a DB URL through an allowed environment variable, run the commands document, refresh manifest checksums only from the regenerated files, then run `python -m pytest tests\test_engine_trend_13_acceptance_pack.py` and the documented relevant suite. Never commit the URL.

## Next recommended stage

ENGINE-TREND-14 — Engine Trend Known Limitations and Next Decision Gate. That stage should decide whether to expand symbols/intervals, examine `UNKNOWN` confidence behavior, add acceptance windows, or stop core work, without trading claims or runtime trading.
