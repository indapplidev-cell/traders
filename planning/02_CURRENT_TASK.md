# Current Task

## BOOK-L1-28 - FLAT Context Alignment Diagnostic

Status: `DONE`

Goal:

Diagnose what high-confidence L1 `FLAT` should mean for BOOK-L2 on the stabilized `15m` workflow without changing L1 or L2 rules.

Command:

```powershell
python -m app.cli.commands book-l1-flat-context-alignment-diagnostic `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_l1/flat_context_alignment_diagnostic.json
reports/book_l1/flat_context_alignment_diagnostic.md
reports/book_l1/book_l1_28_flat_context_alignment_diagnostic_report.md
```

Implemented:

- added `app/market_reader/flat_context_alignment.py`;
- added CLI command `book-l1-flat-context-alignment-diagnostic`;
- added `--symbols`, `--symbol`, `--interval`, `--high-confidence-threshold`, `--alignment-review-json`, `--quality-review-json`, `--l1-timeline-json`, `--l2-context-json`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake JSON under `tests/test_book_l1_flat_context_alignment_diagnostic.py`;
- added stable JSON and Markdown FLAT context diagnostic evidence files;
- added stage report;
- updated terminal guide and planning.

Current finding:

```text
High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.
```

Recommended interpretation:

```text
High-confidence FLAT should not become UNKNOWN.
It may remain non-observation / skip, but L2 should preserve and explain it as FLAT context.
```

Recommended next stage:

```text
BOOK-L2-08 - FLAT Context Handling Proposal
```

Out of scope preserved:

- no BOOK-L1 analysis changes;
- no BOOK-L1 composer scoring changes;
- no BOOK-L1 threshold changes;
- no BOOK-L2 context rule changes;
- no BOOK-L2 quality score changes;
- no BOOK-L2 brief rule changes;
- no JSON export semantic changes;
- no bucket or skip behavior changes;
- no Binance download;
- no DB writes;
- no candle creation;
- no `15m` to `1h`/`4h` aggregation;
- no training;
- no label changes;
- no edge validation;
- no runtime execution.

The next safe stage should be `BOOK-L2-08 - FLAT Context Handling Proposal`.
