# Current Task

## BOOK-L1-26 - 15m Market Reader Quality Review

Status: `DONE`

Goal:

Review the quality of the stabilized `15m` Market Reader workflow and explain why the current L2 answer remains cautious.

Command:

```powershell
python -m app.cli.commands book-l1-15m-quality-review `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

Evidence outputs:

```text
reports/book_l1/market_reader_15m_quality_review.json
reports/book_l1/market_reader_15m_quality_review.md
reports/book_l1/book_l1_26_15m_market_reader_quality_review_report.md
```

Implemented:

- added `app/market_reader/quality_review.py`;
- added CLI command `book-l1-15m-quality-review`;
- added `--symbols`, `--symbol`, `--interval`, `--window-size`, `--window-count`, `--min-candles`, `--output-json`, `--output-md`, `--strict`, `--show-details`;
- added focused unit tests with fake JSON under `tests/test_book_l1_15m_quality_review.py`;
- added stable JSON and Markdown quality review evidence files;
- updated terminal guide and planning.

Current 15m answer:

```text
Overall state: UNKNOWN
Observation candidates: none
Skip candidates: SOLUSDT, BTCUSDT, ETHUSDT
```

Main quality findings:

- `ALL_SYMBOLS_SKIPPED`;
- `NO_OBSERVATION_CANDIDATES`;
- `STABLE_PIPELINE_BUT_WEAK_CONTEXT`.

Per-symbol summary:

- BTCUSDT: L1 current regime `FLAT`, confidence `0.94`, L2 bucket `UNKNOWN`, L2 grade `SKIP`;
- ETHUSDT: L1 current regime `FLAT`, confidence `0.87`, L2 bucket `UNKNOWN`, L2 grade `SKIP`;
- SOLUSDT: L1 current regime `UNKNOWN`, confidence `0.00`, L2 bucket `UNKNOWN`, L2 grade `SKIP`.

Interpretation:

BOOK-L1-26 confirms that the current 15m pipeline is stable, but the readable market context is still weak. The issue is quality/explainability, not pipeline execution.

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

The next work should remain in BOOK-L1 quality/explainability on `15m`, especially reason-code inspection and UNKNOWN/FLAT reduction diagnostics.
