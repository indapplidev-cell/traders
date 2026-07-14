# ENGINE-TREND-25 SHORT_V2 Contract Audit

## Decision

**ENGINE_TREND_25_SHORT_V2_AUDITED_NOT_READY_FOR_PAPER**. Runtime and paper contracts remain unchanged. Only `SHORT_DOWN_CONTINUATION_RETEST` is retained for redesign research; LONG continuation and range mean reversion remain blocked from paper, and trend-only SHORT remains blocked until separate validation.

## Locked default (not selected from results)

`break_confirmation_low__atr_0_15__nearest_support`: break below confirmation low, structural retest high + 0.15 ATR stop, nearest pre-entry confirmed support target.

- full: universe=449, trade candidates=5, clean=5, PF=5.3195, expectancy=0.9027%
- validation: trade candidates=2, clean=2, PF=7.8283, expectancy=1.9170%
- SOLUSDT validation: trade candidates=1, clean=1, PF=n/a, expectancy=4.3956%

## Old SHORT reference

- old validation all SHORT: N=51, PF=0.7603, expectancy=-0.0962%
- ENGINE-TREND-24 validation pocket: N=12, PF=1.2706, expectancy=0.1284%

## Interpretation

The three-stage state machine is now explicit in the audit: setup context, armed causal-zone retest, then a separately filled trade candidate. Too-tight structural stops are rejected rather than rewarded; volume below 0.7, stale/invalidation events, exhaustion conjunctions, target distance above 4 ATR, unresolved conflicts, bullish reversal, and RR below 1.5 are hard failures. Volume 0.7–0.9, targets above 3 ATR, stops above 2 ATR, and RR above 3/5 are warnings/penalties.

All 36 entry/stop/target variants are recorded for design and validation. They are not ranked into a production choice. This is precision analysis over the 449 V1-frozen candidates, not a new detector backtest; a fresh causal scan is required before any paper decision.

The JSON comparison contains controlled slices for entry modes (fixed 0.15 ATR + previous-low target), target modes (break entry + 0.15 ATR), and stop modes (break entry + previous-low target). Variants with design-only expectancy uplift are explicitly marked `REJECT_IN_SAMPLE_ONLY_UPLIFT`.
