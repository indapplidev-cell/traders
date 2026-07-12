# Data Availability Plan

## Current status

BOOK-DATA-01, BOOK-DATA-02, BOOK-DATA-03C, BOOK-L1-26, BOOK-L1-27, and BOOK-L1-28 are complete.

BOOK-DATA-01 added a read-only candle availability audit for Market Reader:

```powershell
python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details
```

Stable audit outputs:

```text
reports/book_data/candle_availability_audit.json
reports/book_data/candle_availability_audit.md
```

BOOK-DATA-02 fixed the interval preparation decision:

```powershell
python -m app.cli.commands book-data-interval-preparation-decision --show-details
```

Stable decision outputs:

```text
reports/book_data/interval_data_preparation_decision.json
reports/book_data/interval_data_preparation_decision.md
reports/book_data/book_data_02_interval_data_preparation_decision_report.md
```

BOOK-DATA-03C stabilized the active 15m-only Market Reader workflow:

```powershell
python -m app.cli.commands book-data-15m-stabilization `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details
```

Stable stabilization outputs:

```text
reports/book_data/market_reader_15m_stabilization.json
reports/book_data/market_reader_15m_stabilization.md
reports/book_data/book_data_03c_15m_only_market_reader_stabilization_report.md
```

BOOK-L1-26 reviewed the quality of the stabilized `15m` Market Reader workflow:

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

Stable review outputs:

```text
reports/book_l1/market_reader_15m_quality_review.json
reports/book_l1/market_reader_15m_quality_review.md
reports/book_l1/book_l1_26_15m_market_reader_quality_review_report.md
```

BOOK-L1-27 reviewed L1-L2 regime alignment on the stabilized `15m` evidence:

```powershell
python -m app.cli.commands book-l1-l2-regime-alignment-review `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details
```

Stable alignment outputs:

```text
reports/book_l1/l1_l2_regime_alignment_review.json
reports/book_l1/l1_l2_regime_alignment_review.md
reports/book_l1/book_l1_27_l1_l2_regime_alignment_review_report.md
```

BOOK-L1-28 diagnosed FLAT context alignment on the stabilized `15m` evidence:

```powershell
python -m app.cli.commands book-l1-flat-context-alignment-diagnostic `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details
```

Stable diagnostic outputs:

```text
reports/book_l1/flat_context_alignment_diagnostic.json
reports/book_l1/flat_context_alignment_diagnostic.md
reports/book_l1/book_l1_28_flat_context_alignment_diagnostic_report.md
```

## Finding

The current blocker for multi-interval L1-L2 reports is data availability, not the L1-L2 pipeline.

The current blocker for useful 15m interpretation is Market Reader quality/explainability:

- L2 overall state is `UNKNOWN`;
- observation candidates are `none`;
- all tested symbols are skip candidates.
- BTCUSDT and ETHUSDT are L1 `FLAT` with high confidence, but L2 reports `UNKNOWN/SKIP`.

BOOK-L1-28 finding:

```text
High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.
```

Recommended interpretation:

```text
High-confidence FLAT should not become UNKNOWN.
It may remain non-observation / skip, but L2 should preserve and explain it as FLAT context.
```

Current audited condition:

- `15m` is ready for BTCUSDT, ETHUSDT, and SOLUSDT;
- `1h` is missing in the local database for the tested symbols;
- `4h` is missing in the local database for the tested symbols.

## Decision

BOOK-DATA-02 decision:

```text
ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING
```

Recommended option:

```text
OPTION_D_HYBRID_LATER
```

Immediate action:

- use `15m` as the active working interval for the current Market Reader workflow;
- treat `1h` and `4h` as optional/missing;
- do not block current BOOK-L1/BOOK-L2 work on missing `1h`/`4h`.
- improve Market Reader quality on `15m` before expanding intervals, unless explicitly decided otherwise.
- prepare `BOOK-L2-08 - FLAT Context Handling Proposal` before changing L2 behavior.

## Boundary

BOOK-DATA-03C is stabilization-only.

It does not approve:

- download data;
- write DB rows;
- create candles;
- aggregate `15m` into `1h` or `4h`;
- change BOOK-L1 analysis logic;
- change BOOK-L2 context logic;
- introduce trading signals;
- validate edge;
- integrate runtime trading.

BOOK-DATA-03C also does not change BOOK-L1 analysis logic, BOOK-L2 context logic, or existing L1/L2 JSON export semantics.

## Future decisions

Next data work requires a separate explicit BOOK-DATA stage.

Possible future stages:

- `BOOK-DATA-03A` - Native 1h/4h Data Loading Plan;
- `BOOK-DATA-03B` - 15m to 1h/4h Aggregation Contract;
- `BOOK-L2-08` - FLAT Context Handling Proposal;
- `BOOK-L1-29` - 15m UNKNOWN/FLAT Reduction Diagnostic.

Do not start 1h/4h expansion before the 15m quality findings are addressed or explicitly accepted.
