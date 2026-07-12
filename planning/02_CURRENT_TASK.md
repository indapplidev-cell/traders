# Current Task

## BOOK-L2-08 - FLAT Context Handling Proposal

Status: `DONE`

Goal:

Prepare a safe proposal for how BOOK-L2 should handle high-confidence L1 `FLAT` on the stabilized `15m` workflow without changing L1 or L2 runtime rules.

Command:

```powershell
python -m app.cli.commands book-l2-flat-context-handling-proposal `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --high-confidence-threshold 0.80 `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_l2/flat_context_handling_proposal.json
reports/book_l2/flat_context_handling_proposal.md
reports/book_l2/book_l2_08_flat_context_handling_proposal_report.md
```

Implemented:

- added `app/market_interpreter/flat_context_proposal.py`;
- added CLI command `book-l2-flat-context-handling-proposal`;
- added `--symbols`, `--symbol`, `--interval`, `--high-confidence-threshold`, `--flat-diagnostic-json`, `--alignment-review-json`, `--l1-timeline-json`, `--l2-context-json`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake JSON under `tests/test_book_l2_flat_context_handling_proposal.py`;
- added stable JSON and Markdown proposal evidence files;
- added stage report;
- updated terminal guide and planning.

Current problem:

```text
High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.
```

Proposal:

```text
High-confidence L1 FLAT should be preserved as L2 FLAT_CONTEXT.
It should remain non-observation / skip by default and must not become a trading signal.
```

Recommended option:

```text
OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE
```

Recommended next stage:

```text
BOOK-L2-09 — Implement FLAT Context Handling
```

Out of scope preserved:

- no BOOK-L1 analysis changes;
- no BOOK-L1 composer scoring changes;
- no BOOK-L1 threshold changes;
- no BOOK-L2 context rule runtime changes;
- no BOOK-L2 quality score runtime changes;
- no BOOK-L2 brief runtime changes;
- no JSON export semantic changes;
- no production bucket or skip decision changes;
- no Binance download;
- no DB writes;
- no candle creation;
- no `15m` to `1h`/`4h` aggregation;
- no training;
- no label changes;
- no edge validation;
- no runtime execution;
- no BOOK-L3 start.
