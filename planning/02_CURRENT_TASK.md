# Current Task

## BOOK-L1-27 - L1-L2 Regime Alignment Review

Status: `DONE`

Goal:

Review why high-confidence L1 `FLAT` regimes become L2 `UNKNOWN/SKIP` on the stabilized `15m` workflow.

Command:

```powershell
python -m app.cli.commands book-l1-l2-regime-alignment-review `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_l1/l1_l2_regime_alignment_review.json
reports/book_l1/l1_l2_regime_alignment_review.md
reports/book_l1/book_l1_27_l1_l2_regime_alignment_review_report.md
```

Implemented:

- added `app/market_reader/regime_alignment_review.py`;
- added CLI command `book-l1-l2-regime-alignment-review`;
- added `--symbols`, `--symbol`, `--interval`, `--quality-review-json`, `--l1-timeline-json`, `--l2-context-json`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake JSON under `tests/test_book_l1_l2_regime_alignment_review.py`;
- added stable JSON and Markdown alignment evidence files;
- updated terminal guide and planning.

Current 15m alignment finding:

```text
BTCUSDT and ETHUSDT are L1 FLAT with high confidence, but L2 reports UNKNOWN/SKIP.
SOLUSDT is L1 UNKNOWN and propagates to L2 SKIP.
```

Interpretation:

The pipeline is technically stable. The next issue is alignment between L1 regime output and L2 context/skip interpretation, especially FLAT context handling and L1-to-L2 contract mapping.

Out of scope preserved:

- no Binance download;
- no DB writes;
- no candle creation;
- no `15m` to `1h`/`4h` aggregation;
- no BOOK-L1 analysis changes;
- no BOOK-L2 context changes;
- no JSON export semantic changes for BOOK-L1/BOOK-L2;
- no training;
- no label changes;
- no edge validation;
- no runtime execution.

The next safe stage should be `BOOK-L1-28 - FLAT Context Alignment Diagnostic`.
