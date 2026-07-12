# ENGINE-TREND-14 — Decision Gate

## Decision context

ENGINE-TREND-09 through ENGINE-TREND-13 established a real PostgreSQL read path, safe DB CLI preview, and offline-verifiable acceptance pack. The only accepted latest-window outcomes are `UNKNOWN 0.3`; no labeled historical benchmark exists.

## Evidence already available

- Confirmed PostgreSQL 16.10 source: `public.market_candles`.
- Confirmed availability for BTCUSDT, ETHUSDT, and SOLUSDT at `15m`.
- Three 96-candle runs with `READY`, `UNKNOWN`, confidence `0.3`, and zero warnings/errors.
- Six SHA256-verified JSON artifacts.
- Fail-closed safety fields and no runtime or live execution connection.

This evidence validates pipeline operation and reproducibility, not classification accuracy.

## Open questions

- How does the core classify independently selected, visually clear UP, DOWN, and FLAT/range windows?
- Which UNKNOWN results are reasonable for ambiguous windows, and which are questionable for clear windows?
- Are reason codes reviewable and consistent across symbols and regimes?
- How stable is confidence across historical contexts and, secondarily, a 192-candle window?
- Is any future tuning supported by repeated evidence rather than one latest sample?

## Decision options

- **Option A — Stop core development and only keep current CLI baseline.** Safe, but leaves market-reading quality unanswered.
- **Option B — Tune core immediately because results are UNKNOWN.** Rejected: one unlabelled latest window per symbol cannot justify tuning.
- **Option C — Build historical validation pack before changing core.** Collects the missing comparative evidence while preserving the baseline.
- **Option D — Expand DB source to more intervals/symbols before validation.** Increases breadth before establishing a sound evaluation method.

## Selected decision

**Option C — Build historical validation pack before changing core.**

Do not tune the core just because the latest-window preview returned UNKNOWN.

## Rationale

The current pipeline works and its safety contract is preserved. `UNKNOWN 0.3` alone cannot justify tuning. Changing thresholds or composition before labeled validation risks overfitting and arbitrary changes. Historical windows spanning distinct regimes are the minimum evidence needed to evaluate market-reading quality.

## Exit criteria for next stage

ENGINE-TREND-15 exits when:

- at least three windows per symbol and at least nine total windows have been frozen;
- BTCUSDT, ETHUSDT, and SOLUSDT `15m` are represented with a 96-candle baseline;
- manual reference labels and labeling notes are recorded before comparison;
- engine regime, confidence, top reason codes, warning/error counts, and match status are captured consistently;
- UNKNOWN cases are separated into acceptable, questionable, and review-needed cases;
- every selected window runs or has a documented data/pipeline failure;
- no core tuning occurs during validation.

## Stop conditions

Stop and open a separate decision stage if the required data is unavailable, labels cannot be reproduced, outputs cannot be captured consistently, integrity/safety checks fail, or proposed work requires core, threshold, adapter, CLI, trading, execution, or training changes. Do not interpret incomplete evidence as permission to tune.
