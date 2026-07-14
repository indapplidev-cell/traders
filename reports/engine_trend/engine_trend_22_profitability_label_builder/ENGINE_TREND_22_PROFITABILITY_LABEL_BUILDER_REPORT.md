# ENGINE-TREND-22 — Profitability Label Builder

## Outcome and scope

Final status: `COMPLETED_OFFLINE_BUILDER_REAL_MARKET_VALIDATION_BLOCKED`.

ENGINE-TREND-22 adds a deterministic offline/audit-only transformation from an already frozen ENGINE-TREND-21 setup plan to a profitability label. It is not imported by the market reader, does not create a setup or signal, does not call an exchange, does not place an order, and does not alter the baseline regime, hypothesis, composer, thresholds, indicator context, or setup contracts.

Synthetic validation passes. Real-market profitability validation remains `BLOCKED_NO_TRADE_CANDIDATES`: all four supplied live cases are `NO_TRADE` or `WAIT_CONFIRMATION`, so they correctly produce `NO_TRADE_SKIPPED` and no fictitious PnL.

## Causality and leakage boundary

The builder accepts entry, stop, targets, direction, and expiry as immutable input. It neither derives nor moves those levels from future candles. Only candles whose timestamp is strictly greater than the entry/confirmation candle timestamp enter evaluation; entry-time and older candles are ignored. The first eligible candle is bar 1.

Only a `TRADE_CANDIDATE` with LONG/SHORT direction, a timezone-aware entry timestamp, finite positive prices, positive directional risk/reward, at least one target, and a positive integer expiry can receive an outcome. `NO_TRADE`, `WAIT_CONFIRMATION`, and `INVALIDATED` short-circuit to `NO_TRADE_SKIPPED`. The ENGINE-TREND-20B-blocked trend-only setup type is rejected as `INVALID_SETUP_PLAN`; indicator evidence cannot originate a setup in this layer.

## Outcome algorithm

Each target is evaluated independently over at most `expires_after_candles`; T1 is copied to the primary label and every result remains in `target_results`.

- Target hit first: `TP_BEFORE_SL`, exit at the frozen target.
- Stop hit first: `SL_BEFORE_TP`, exit at the frozen stop.
- Both touched in the same OHLC candle: `AMBIGUOUS_INTRACANDLE`. The builder records `TARGET_AND_STOP_TOUCHED_SAME_CANDLE`, retains both frozen levels, and leaves exit/return fields null so it cannot enter clean win/loss metrics.
- Neither touched with the full horizon present: `NEITHER_EXPIRED`, exit at the expiry candle close.
- Neither touched before available data ends: `INSUFFICIENT_FUTURE_DATA`, with no invented exit or return. Observed MFE/MAE are retained and data quality is `INCOMPLETE`.
- Structurally invalid/missing plans: `INVALID_SETUP_PLAN` with explicit validation errors.

A decisive TP/SL/ambiguous event is labelable even if fewer candles than the full expiry remain, because the outcome is already terminal. Full expiry coverage is required only to assert `NEITHER_EXPIRED`.

## Metrics

Directional planned values are:

- LONG: `risk = entry - stop`, `reward = target - entry`, `realized_return = exit - entry`.
- SHORT: `risk = stop - entry`, `reward = entry - target`, `realized_return = entry - exit`.
- `rr_planned = reward / risk`.

MFE and MAE use high/low extremes from eligible post-entry bars through the outcome bar, or through the observed/expiry window when no level is hit. Favorable and adverse excursions are clamped at zero. Percent metrics divide the absolute excursion by entry; R metrics divide by planned risk. `bars_to_max_favorable` and `bars_to_max_adverse` use the first bar attaining the extreme.

Gross return is directional realized return divided by entry and expressed in percent. Audit costs are fixed at 10 fee bps per side plus 2 slippage bps per side, or 24 bps round trip. Therefore `net_return_pct = gross_return_pct - 24 / 100`. These values are deterministic assumptions, not exchange fees, and are applied only where an unambiguous exit exists.

## Validation coverage

The synthetic fixture pack covers: LONG TP, LONG SL, SHORT TP, SHORT SL, neither/expiry, same-candle ambiguity, missing entry, missing stop, missing target, no-trade skip, insufficient future data, and independent multiple targets. Tests additionally verify strict exclusion of entry/prior candles, all no-trade states, MFE/MAE/R formulas, the 24 bps net-return adjustment, T1 primary selection, artifact reproducibility, output-schema shape, live-case skips, and the blocked contract guard.

## Real-market gate and next stage

No supplied live case is an ENGINE-TREND-21 `TRADE_CANDIDATE`. The manual fixture format is documented in the synthetic fixture artifact. A future real fixture must freeze a causally established setup plan before attaching subsequent candles. Until enough such out-of-sample fixtures exist, profitability is not proven and ML meta-filter/runtime integration is not authorized.

## Explicit non-changes

- Runtime behavior changed: no.
- Trading runtime changed: no.
- Market hypothesis runtime changed: no.
- Thresholds changed: no.
- Composer changed: no.
- `technical_indicator_context` changed: no.
- ENGINE-TREND-21 setup contracts changed: no.
- Exchange/trading API used: no.
- Commit created: no.

## Verification

- ENGINE-TREND targeted and regression command (PowerShell-expanded `tests/test_engine_trend_*.py`): `305 passed in 29.59s`.
- ENGINE-TREND-22 focused suite: `24 passed in 0.86s`.
- `git diff --check`: pass, exit code 0. Existing worktree line-ending warnings are informational and predate/are outside this isolated untracked artifact set.
- Runtime import scan for `profitability_labels`: none.
