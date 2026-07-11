# Current State

## BOOK-L1 Market Reader status

Status: `READ_ONLY_API_CONTRACT_READY`

BOOK-L1 Market Reader is implemented as a read-only market-reading layer.

It currently supports:

- candle window normalization and validation;
- candle morphology analysis;
- swing high / swing low detection;
- trend structure analysis;
- range structure analysis;
- breakout / retest context;
- EMA / ATR technical context;
- market regime composition;
- full orchestration through `MarketReaderOrchestrator`;
- CLI preview from stored candles through `book-l1-preview`;
- real DB smoke report for BTCUSDT 15m;
- API/service response contract through `book-l1-api-preview`.

Current safety contract:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
approved_for_live_trading = false
approved_for_auto_activation = false
```

BOOK-L1 does not train models, does not download candles during preview, does not connect to runtime trading, and does not approve entries.

Latest completed implementation stages:

| Stage | Status | Result |
| --- | --- | --- |
| BOOK-L1-12 | DONE | CLI preview command added. |
| BOOK-L1-13 | DONE | Manual real DB smoke report added. |
| BOOK-L1-14 | DONE | API/service response contract added. |

Latest relevant artifacts:

- `reports/book_l1/book_l1_13_BTCUSDT_15m_preview.json`
- `reports/book_l1/book_l1_13_cli_preview_smoke_report.md`
- `reports/book_l1/book_l1_14_BTCUSDT_15m_api_preview.json`

Latest relevant commit:

```text
80c781e feat: add BOOK-L1 API response contract
