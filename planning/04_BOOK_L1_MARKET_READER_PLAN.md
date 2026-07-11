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

## Current implementation boundary

BOOK-L1 currently includes a safe API/service response contract and a human-readable terminal preview.

The response contract can be consumed by a future external layer, but it remains read-only and fail-closed.
The terminal preview is a presentation layer over the same fail-closed payload.

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
