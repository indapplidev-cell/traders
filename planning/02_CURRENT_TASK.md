# Current Task

## BOOK-L2-07 - Multi-Interval Answer Smoke

Status: `DONE`

Goal:

Verify that the BOOK-L1 -> BOOK-L2 chain produces actual human-readable market context evidence across multiple intervals, not only one selected interval.

Primary runtime inputs and outputs:

```text
reports/book_l1/timeline_preview.json
reports/book_l2/timeline_context.json
```

Evidence output:

```text
reports/book_l2/l1_l2_multi_interval_answer.md
```

Implemented:

- added `app/integration/l1_l2_multi_interval_answer_smoke.py`;
- added `L1L2MultiIntervalAnswerSmokeConfig`;
- added `L1L2IntervalAnswerSummary`;
- added `L1L2MultiIntervalAnswerSmokeResult`;
- added `L1L2MultiIntervalAnswerSmokeRunner`;
- added `L1L2MultiIntervalAnswerSmokeFormatter`;
- added cross-interval aggregation;
- added forbidden human answer term validation;
- added fail-closed safety validation per interval;
- added CLI command `book-l1-l2-multi-interval-answer-smoke`;
- added `--symbols`;
- added `--symbol`;
- added `--intervals`;
- added `--window-size`;
- added `--window-count`;
- added `--min-candles`;
- added `--strict`;
- added `--show-details`;
- added `--output-md`;
- added `--continue-on-fail`;
- added focused unit tests for defaults, formatter, Markdown, aggregation, strict/non-strict behavior, safety, forbidden terms, and CLI option coverage.

BOOK-L2-07 added multi-interval L1-L2 answer smoke.

The system can now produce a human-readable evidence report for multiple intervals, showing per-interval L2 state, observation candidates, skip candidates, safety, and cross-interval observations.

The report is evidence Markdown, not runtime API output. Runtime API output remains JSON.

Command:

```powershell
python -m app.cli.commands book-l1-l2-multi-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

Out of scope preserved:

- no candle reads inside BOOK-L2;
- no DB access from BOOK-L2;
- no Binance access;
- no BOOK-L1 market analysis changes;
- no BOOK-L1 JSON semantics changes;
- no BOOK-L2 bucket rule changes;
- no BOOK-L2 quality score changes;
- no BOOK-L2 market brief rule changes;
- no BOOK-L2 JSON export semantics changes;
- no API readiness logic changes;
- no live trading connection.

Freeze status:

```text
BOOK-L2-07 verified the actual L1-L2 multi-interval answer smoke.
BOOK-L2 remains Layer 2 Freeze Candidate.
BOOK-L2 remains consume-only / observe-only / fail-closed.
```
