# Current Task

## BOOK-L2-06 - L1-L2 Interval Report Answer Smoke

Status: `DONE`

Goal:

Verify that the BOOK-L1 -> BOOK-L2 chain produces an actual human-readable market context answer for a requested interval, not only green tests.

Primary input:

```text
reports/book_l1/timeline_preview.json
```

Primary output:

```text
reports/book_l2/timeline_context.json
```

Evidence output:

```text
reports/book_l2/l1_l2_interval_answer.md
```

Implemented:

- added `app/integration/l1_l2_interval_answer_smoke.py`;
- added `app/integration/__init__.py`;
- added `L1L2IntervalAnswerSmokeConfig`;
- added `L1L2IntervalAnswerSmokeStep`;
- added `L1L2IntervalAnswerSmokeResult`;
- added `L1L2IntervalAnswerSmokeRunner`;
- added `L1L2IntervalAnswerSmokeFormatter`;
- added CLI command `book-l1-l2-interval-answer-smoke`;
- added `--symbols`;
- added `--symbol`;
- added `--interval`;
- added `--window-size`;
- added `--window-count`;
- added `--min-candles`;
- added `--strict`;
- added `--show-details`;
- added `--output-md`;
- added pipeline coordination for L1 timeline export, L1 JSON consumer strict, L2 context export, L2 JSON consumer strict, and L2 API readiness strict;
- added symbol propagation validation from L1 output to L2 output;
- added source lineage validation back to `reports/book_l1/timeline_preview.json`;
- added fail-closed safety validation;
- added forbidden human answer term validation;
- added evidence Markdown writer with actual L2 overall state, brief, candidates, key points, per-symbol context, safety, and lineage;
- added focused unit tests for config defaults, Markdown, validations, formatter, and CLI option coverage.

BOOK-L2 boundary:

```text
BOOK-L1 JSON -> BOOK-L2 context interpretation -> BOOK-L2 JSON -> evidence Markdown
```

Out of scope preserved:

- no candle reads;
- no `CandleRepository` import in BOOK-L2;
- no `MarketReaderOrchestrator` import in BOOK-L2;
- no DB access;
- no external exchange access;
- no BOOK-L1 market analysis changes;
- no BOOK-L1 JSON semantics changes;
- no scoring/ranking rule changes;
- no market brief rule changes;
- no model training;
- no traders-core connection;
- no live trading connection;
- no order creation;
- no trading decisions.

Safety validation:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
orders_enabled = false
live_trading_connected = false
traders_core_connected = false
approved_for_live_trading = false
approved_for_auto_activation = false
```

Command:

```powershell
python -m app.cli.commands book-l1-l2-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

Completion checks:

- compile check passed;
- fresh BOOK-L1 timeline JSON export passed;
- L1 runtime JSON consumer strict smoke passed;
- L2 context export passed;
- L2 JSON consumer strict smoke passed;
- L2 API readiness strict smoke passed;
- symbol propagation passed;
- source lineage passed;
- fail-closed safety passed;
- evidence Markdown was written;
- targeted integration smoke tests passed;
- full BOOK-L1 + BOOK-L2 pack passed;
- forbidden import check passed.

Freeze status:

```text
BOOK-L2-06 verified the actual L1-L2 interval report answer smoke.
BOOK-L2 is now Layer 2 Freeze Candidate.
BOOK-L2 remains consume-only / observe-only / fail-closed.
```

This evidence report is not runtime API output; API output remains JSON.

Next possible layer: BOOK-L3, but only after explicit approval.
