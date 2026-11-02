# Bull-run weight calibration implementation — 2026-11-02

## Verdict

`IMPLEMENTATION_PASS / OCTOBER_HISTORICAL_VERIFICATION_BLOCKED_DATA`

The repository now contains an isolated, read-only workflow for calibrating
Scalping v2 LONG entry and analytical-exit weights against algorithmically
labelled 5–30 minute bullish legs. No production parameter, PAPER control state,
database row, service, image, or LIVE authority was changed.

## Implemented contracts and behavior

- Versioned October 2026 requests cover all 20 trading-universe-v3 symbols.
- Entry weights use structure/context/momentum/volume/entry-quality/liquidity/
  confirmation and preserve the 25/15/15/15/10/10/10 baseline.
- Exit weights use the existing graphical/technical/momentum/economics groups and
  preserve the 35/35/20/10 baseline.
- Both weight vectors are non-negative, sum to 100, and reject a component above
  45. Thresholds enforce `at_risk < exit <= strong_reversal`.
- Bull labels use executable 5m closes, one-to-six-candle horizons, historical
  round-trip costs plus 8 bps, ATR-normalized movement, checksums, and weighted
  non-overlapping interval selection.
- A frozen-history adapter reruns the authoritative PipelineRunner with a
  research-only zero score probe while retaining hard setup, invalidation,
  economics, risk, statistics, and safety gates. Complete module payloads and
  causal analytical-exit evidence are stored in immutable JSONL.
- Replay rejects future bars and same-symbol/concurrent-position conflicts, uses
  stop-first OHLC exits, next-boundary analytical fills, two confirmations, the
  frozen 5 bps risk budget, exact fee/impact/net-PnL accounting, and a two-position
  capacity.
- Search performs deterministic sensitivity followed by seeded Optuna TPE with
  one worker. Pareto ranking is followed by validation finalist freeze and a
  one-shot holdout that is replayed twice for deterministic verification.
- Mandatory economic, drawdown, coverage, false-entry, and concentration gates
  return `NO_ELIGIBLE_CANDIDATE` when unmet.
- Publication produces labels, finalists, trades, report, hashes, and an
  `INACTIVE_CANDIDATE.yaml` with `active: false` and mandatory November holdout.

## Database corroboration and blocker

Read-only PostgreSQL aggregates for `2026-10-01T00:00:00Z` through
`2026-11-01T00:00:00Z` proved:

- 20 symbols;
- 178,560 closed 5m candles, exactly 8,928 per symbol;
- 892,800 closed 1m candles, exactly 44,640 per symbol;
- 135,222 persisted `trade-5m-v2` pipeline results in the same month.

Therefore at least 43,338 October 5m boundaries have no matching persisted
pipeline row from which the current frozen-history source can recover causal
spread/depth/commission evidence. A bounded sample of the earliest 100 persisted
rows contained complete geometry cost fields in only five rows. The full JSON
cost aggregation exceeded a 60-second read-only statement timeout, so no stronger
full-row percentage is claimed.

The workflow consequently marks the October dataset `INCOMPLETE` and exits with
`BLOCKED_DATA`. It does not substitute current fees, invent historical order-book
inputs, run an assumption-based certification, or publish selected weights. A
full October candidate requires a separately proven historical cost source or an
explicitly assumption-based study that cannot qualify as the requested verified
result.

## Validation

- New bull-run contracts, labels, causality, accounting, portfolio capacity,
  deterministic TPE, holdout isolation, report publication, and dataset helpers:
  `15 passed`.
- New CLI integration plus the same focused suite: `17 passed`.
- Existing chronological replay, historical reconstruction, holdout protocol,
  analytical exit, and non-legacy focused coverage completed in the selected run;
  the selected aggregate was `48 passed, 6 failed`, with all six failures in
  pre-existing removed `trade-5m-v1` expectations.
- The broader research attempt exposed `8 failed, 1 passed` in the pre-existing
  finding-verifier export suite because its generated legacy YAML lacks the now
  mandatory root `reload` field. This failure is unrelated to the new workflow.
- Python compilation of the new modules and CLI: PASS.

## Safety and next gate

`PRODUCTION_MUTATIONS = 0`

`PAPER_OR_LIVE_PARAMETER_CHANGES = 0`

`REAL_BINANCE_ORDER_CALLS = 0`

The next data task is to establish complete causal October cost evidence without
backfilling it from current market state. After that, freeze the full dataset,
run the 500-trial campaign, and publish either an inactive eligible candidate or
`NO_ELIGIBLE_CANDIDATE`. Full November external holdout remains unavailable until
after `2026-12-01`.
