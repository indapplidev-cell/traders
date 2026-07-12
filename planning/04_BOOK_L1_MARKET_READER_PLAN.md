# BOOK-L1 Market Reader Plan

## Layer definition

BOOK-L1 is the first market-reading layer:

```text
candles -> chart/technical context -> market regime -> UP / DOWN / FLAT / UNKNOWN
```

BOOK-L1 is not a trading system.

It must not produce:

- LONG / SHORT signal;
- order intent;
- entry approval;
- runtime trading approval.

Safety output must remain:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
```

## Stage checklist

| Stage | Name | Status | Main artifact |
| --- | --- | --- | --- |
| BOOK-L1-00 | Planning baseline | DONE | `planning/*.md` |
| BOOK-L1-01 | Read-only audit | DONE | audit decisions / architecture direction |
| BOOK-L1-02 | Market reader schemas | DONE | `app/market_reader/schemas.py` |
| BOOK-L1-03 | Candle Window | DONE | `app/market_reader/candle_window.py` |
| BOOK-L1-04 | Candle Morphology | DONE | `app/market_reader/candle_morphology.py` |
| BOOK-L1-05 | Swing Detector | DONE | `app/market_reader/swing_detector.py` |
| BOOK-L1-06 | Trend Structure Analyzer | DONE | `app/market_reader/trend_structure.py` |
| BOOK-L1-07 | Range Structure Analyzer | DONE | `app/market_reader/range_structure.py` |
| BOOK-L1-08 | Breakout / Retest Analyzer | DONE | `app/market_reader/breakout_retest.py` |
| BOOK-L1-09 | Technical Context Analyzer | DONE | `app/market_reader/technical_context.py` |
| BOOK-L1-10 | Market Regime Composer | DONE | `app/market_reader/market_regime_composer.py` |
| BOOK-L1-11 | Market Reader Orchestrator | DONE | `app/market_reader/market_reader.py` |
| BOOK-L1-12 | CLI Preview Command | DONE | `book-l1-preview` |
| BOOK-L1-13 | Real DB CLI Smoke Report | DONE | `reports/book_l1/book_l1_13_*` |
| BOOK-L1-14 | API Preview / Service Response Contract | DONE | `app/market_reader/api_response.py`, `book-l1-api-preview` |
| BOOK-L1-15 | Planning Status Update / Documentation Sync | DONE | `planning/*.md` |
| BOOK-L1-16 | Repository Cleanup / Final BOOK-L1 Review | DONE | `reports/book_l1/book_l1_16_final_review.md` |
| BOOK-L1-17 | Interactive Terminal Preview / Human Table Report | DONE | `book-l1-interactive-preview` |
| BOOK-L1-18 | Multi-Symbol Interactive Preview / Compare Market Regimes | DONE | `book-l1-multi-preview` |
| BOOK-L1-19 | Market Regime History Snapshot / Compare Current vs Previous Window | DONE | `book-l1-history-preview` |
| BOOK-L1-20 | Market Regime Timeline Preview / Multi-Window History Table | DONE | `book-l1-timeline-preview` |
| BOOK-L1-21 | Market Regime Timeline Export / JSON + Markdown Report | DONE | `reports/book_l1/timeline_preview.*` |
| BOOK-L1-22 | Unified JSON Export Contract / API Output Files | DONE | `app/market_reader/json_export.py` |
| BOOK-L1-23 | Terminal UX Cleanup / Unified Command Guide | DONE | `app/market_reader/terminal_guide.py`, `book-l1-guide` |
| BOOK-L1-24 | Runtime JSON Consumer / API Reader Smoke | DONE | `app/market_reader/json_consumer.py`, `book-l1-json-consumer-smoke` |
| BOOK-L1-25 | API Readiness Final Review / Layer 1 Freeze Candidate | DONE | `app/market_reader/api_readiness_review.py`, `book-l1-api-readiness-review` |
| BOOK-L2-00 | Start Layer 2 / Consume BOOK-L1 Timeline JSON | DONE | `app/market_interpreter/l1_timeline_consumer.py`, `book-l2-timeline-context` |
| BOOK-DATA-01 | Candle Data Availability Audit for Market Reader | DONE | `app/data_audit/candle_availability.py`, `book-data-candle-availability-audit` |
| BOOK-DATA-02 | Interval Data Preparation Decision | DONE | `app/data_audit/interval_preparation_decision.py`, `book-data-interval-preparation-decision` |

## Current implementation boundary

BOOK-L1 currently includes a safe API/service response contract, a human-readable single-symbol terminal preview, a multi-symbol comparison terminal preview, a previous-vs-current market regime history snapshot, a multi-window market regime timeline preview, stable unified JSON API output files for all main preview modes, a unified terminal command guide, a read-only runtime JSON consumer smoke command, and a final API readiness review command.

The response contract can be consumed by a future external layer, but it remains read-only and fail-closed.
The terminal previews are presentation layers over the same fail-closed market-reader payloads. The history snapshot compares two non-overlapping local candle windows. The timeline preview compares several non-overlapping historical windows, reports stability and last transition, and remains read-only. The unified JSON export writes only fixed runtime filenames and overwrites them on each `--export-json` run:

```text
reports/book_l1/current_preview.json
reports/book_l1/multi_preview.json
reports/book_l1/history_preview.json
reports/book_l1/timeline_preview.json
```

Export filenames do not include date, time, version, symbol, interval, stage number, UUID, or hash suffix. Runtime Markdown export is not used as working output. The export safety contract is explicit in every JSON envelope.

Terminal command guide:

```powershell
python -m app.cli.commands book-l1-guide
```

Working UX:

```text
Terminal output: for humans
JSON export: for API
Runtime Markdown export: not used
```

Unified JSON export contract:

```text
contract_version = book_l1_json_export_v1
service = BOOK_L1_MARKET_READER
```

Runtime JSON consumer smoke:

```powershell
python -m app.cli.commands book-l1-json-consumer-smoke --strict
```

BOOK-L1-24 validates stable JSON export files before external API consumption. It checks envelope keys, `contract_version`, `service`, expected `report_type`, list-shaped warnings/errors, object-shaped request/summary/safety, and fail-closed safety fields. It does not change market analysis logic, does not change JSON export semantics, does not use runtime Markdown as API output, and does not connect live trading.

API readiness final review:

```powershell
python -m app.cli.commands book-l1-api-readiness-review
```

BOOK-L1-25 checks required modules, tests, planning files, CLI command registration, stable JSON files, JSON contract, and fail-closed safety. Missing runtime JSON files are WARN after a clean checkout because export may not have run yet. Invalid JSON, wrong `service`, wrong `contract_version`, missing safety, or unsafe safety values are FAIL.

BOOK-L1 is now a Layer 1 Freeze Candidate.

BOOK-DATA-01 adds a separate read-only audit for local candle availability:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

The audit explains whether each `symbol/interval` has enough candles for the L1 timeline requirement. It is not BOOK-L1 analysis logic and does not change market regime composition.

Current data condition:

```text
15m is ready for the tested symbols.
1h and 4h are missing in the local database.
```

No trading logic is introduced.

BOOK-DATA-02 fixed the interval preparation decision:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --show-details
```

Decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

`15m` is the active working interval for the current Market Reader workflow. `1h` and `4h` are optional/missing and should not block current BOOK-L1/BOOK-L2 work.

BOOK-DATA-02 does not approve download, DB write, interval aggregation, trading logic, edge validation, or runtime integration. Next data work requires a separate explicit BOOK-DATA stage.

BOOK-L2 has started as a separate layer above BOOK-L1. BOOK-L2-00 consumes the stable BOOK-L1 timeline JSON export:

```text
reports/book_l1/timeline_preview.json
```

BOOK-L2 does not read candles, does not import `CandleRepository`, does not import `MarketReaderOrchestrator`, does not recalculate technical context, and does not change BOOK-L1 market analysis or JSON export semantics.

Current BOOK-L2 command:

```powershell
python -m app.cli.commands book-l2-timeline-context
```

Current BOOK-L2 export:

```text
reports/book_l2/timeline_context.json
```

Layer boundary:

```text
Terminal = for humans
JSON = for API/runtime consumers
Runtime Markdown = not a working output
Trading execution = prohibited
```

Do not expand BOOK-L1 without a separate decision. The next valid direction is follow-up work in BOOK-L2 while preserving the BOOK-L1 freeze boundary.

Current API preview safety block:

```json
{
  "api_preview_only": true,
  "trade_signal": "NOT_EVALUATED",
  "safe_for_runtime_trading": false,
  "orders_enabled": false,
  "live_trading_connected": false,
  "traders_core_connected": false,
  "approved_for_live_trading": false,
  "approved_for_auto_activation": false,
  "model_training_executed": false,
  "binance_download_executed": false
}
```
