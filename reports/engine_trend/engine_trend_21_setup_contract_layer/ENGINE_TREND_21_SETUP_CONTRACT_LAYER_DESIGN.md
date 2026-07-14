# ENGINE-TREND-21 — Setup Contract Layer Design

## Status and scope

This is a design/audit-only contract layer above the unchanged ENGINE-TREND-19/20 market reader. It does not implement setup evaluation in runtime, emit orders, size positions, calculate PnL, backtest, call an exchange, or alter the composer. The proposed `1.5` minimum reward/risk and `8`-candle lifetime are setup-layer design defaults from the task contract, not changes to existing engine thresholds; both require later validation.

The boundary is:

`market context -> causal market hypothesis -> setup contract -> entry/invalidation/stop/target -> future profitability labels -> future ML meta-filter -> future risk gate -> future execution`

ENGINE-TREND-21 defines only the setup-contract box and its output boundary.

## Why regime is not a trade

`UP`, `DOWN`, and `FLAT` describe market context, not a timed, bounded-risk opportunity. A trade candidate additionally needs a causal price sequence, a closed entry trigger, structural invalidation, executable stop provenance, reachable target provenance, acceptable reward/risk, freshness, and absence of a stronger conflict. Therefore:

- `DOWN` does not mean sell; it only permits evaluation of a bearish setup.
- `UP` does not mean buy; it only permits evaluation of a bullish setup.
- `FLAT` does not automatically permit range trading; `CONFIRMED_RANGE`, a tested boundary, and inward rejection are required.
- `UNKNOWN` always maps to `NO_TRADE_CONTRACT / NO_TRADE`, even if indicators look directional or an audit-only counterfactual passes.
- Indicators may confirm or veto a structure-led setup but may never originate one or vote it into existence.

## Causality contract

At `as_of`, every field must be derived only from candles and engine evidence closed by that timestamp. The evaluator must preserve provenance for the structural event, retest/boundary test, confirmation candle, invalidation anchor, target anchor, and conflict checks. No future high/low may be used to choose the entry, stop, target, or label. A moving-average/VWAP touch is contextual confluence only; without a prior break/reclaim, structure, and rejection sequence there is no setup.

The causal sequence is:

1. Accept the immutable engine snapshot and data-quality result.
2. Apply hard blockers (`UNKNOWN`, failed data, unresolved hard conflict, disabled draft contract).
3. Select only contracts compatible with regime and confirmed hypothesis.
4. Establish a structure-led setup zone and objective from evidence already present.
5. Wait for a later closed confirmation candle; do not enter on the same event that first creates the zone.
6. Derive invalidation first, then stop, then targets. Never move a stop to manufacture RR.
7. Calculate RR and freshness; emit exactly one status.

## Common status semantics

- `TRADE_CANDIDATE`: all causal gates pass and numeric entry, invalidation, stop, at least one reachable target, and qualifying RR exist. This is still not an order.
- `WAIT_CONFIRMATION`: a compatible causal premise and its structural levels exist, but an explicitly awaited confirmation/resolution is incomplete. It cannot be used when invalidation/target are fundamentally unknowable.
- `NO_TRADE`: no valid setup exists at this snapshot, or a hard pre-activation gate failed.
- `INVALIDATED`: a previously identified pending/candidate premise was breached, expired, or contradicted. Evaluation history is needed to distinguish this from a fresh `NO_TRADE`.

Status priority is `data/UNKNOWN hard block -> INVALIDATED for a tracked prior setup -> NO_TRADE hard gate -> WAIT_CONFIRMATION -> TRADE_CANDIDATE`. A fresh snapshot with no prior setup cannot be `INVALIDATED`.

## Price, stop, target, and RR rules

Entry is normally the close of the first qualifying post-retest confirmation candle. `limit_retest` and `breakout_stop` remain schema vocabulary for future validated contracts; they are not authorized runtime behavior here.

Invalidation is the price event that falsifies the market premise: reclaim above a bearish rejection/retest high, loss below a bullish retest low, or acceptance outside a tested range boundary. Stop is derived beyond that invalidation using a later validated market-noise buffer. Invalidation and stop are separate: invalidation explains falsification; stop represents the proposed protective level. If either cannot be located causally, the result is `NO_TRADE`.

Targets must pre-exist as causal objectives: prior swing low/high, measured move, support/resistance zone, range midline, or opposite boundary. A target already breached before entry, on the wrong side of entry, or blocked by nearer opposing structure is not eligible.

For a long:

`risk = entry - stop`, `reward = target - entry`, `RR = reward / risk`.

For a short:

`risk = stop - entry`, `reward = entry - target`, `RR = reward / risk`.

Risk and reward must both be positive. At least one reachable target must satisfy `RR >= min_reward_risk` (design default `1.5`). Fees, slippage, funding, and execution probability are intentionally outside this design; a future implementation should evaluate net RR before activation. Missing entry/stop/target, zero/non-positive risk, non-finite values, or all targets below minimum produces `NO_TRADE`.

## Contract definitions

### SHORT_DOWN_CONTINUATION_RETEST

- Required market regime: `DOWN`, or a future adapter may accept confirmed `DOWN_CONTINUATION` only if the resulting source regime remains non-`UNKNOWN` and the policy is explicitly validated.
- Required hypothesis: confirmed `DOWN_CONTINUATION` for the initial contract.
- Allowed context: LL/LH bearish structure; broken support acting as resistance; resistance, EMA, or VWAP confluence zone; failed rebound and bearish rejection.
- Forbidden context: confirmed bullish reversal, dominant confirmed range, bear trap, unresolved directional conflict, stale/bad data.
- Entry: closed bearish confirmation candle after the retest/rejection.
- Invalidation: reclaim/close above rejection high or reclaim-zone upper edge.
- Stop: beyond invalidation plus validated buffer.
- Target: prior low, measured move, or support zone below entry.
- RR/expiration/conflicts: common rules; default eight candles, earlier invalidation on opposing confirmation or material zone change.

### SHORT_TREND_ONLY_CONTINUATION_CANDIDATE

This is a draft contract only. Proposed evidence is LL/LH, bearish technical confirmation, a subsequent failed rebound, no stronger confirmed range, and no bullish reversal. It must not activate from current ENGINE-TREND-20 counterfactual evidence. Until separate ENGINE-TREND-20B validation, every attempted evaluation resolves to `NO_TRADE` with `CONTRACT_NOT_VALIDATED_ENGINE_TREND_20B`. Indicators remain supporting evidence, never the source hypothesis.

If 20B later authorizes it, entry would follow a closed bearish confirmation after the failed rebound; invalidation would be above the failed-rebound high/structural pivot; stop and targets would follow common rules. Its proposed expiry also requires validation.

### LONG_UP_CONTINUATION_RETEST

- Required market regime: `UP` and a confirmed bullish continuation hypothesis/equivalent future contract.
- Allowed context: HH/HL structure, breakout/reclaim and retest, support or EMA/VWAP confluence, failed breakdown, bullish rejection.
- Forbidden context: confirmed bearish reversal, dominant range, bull trap, unresolved conflict, stale/bad data.
- Entry: closed bullish confirmation after the retest and failed breakdown.
- Invalidation: close below retest low or reclaim-zone lower edge.
- Stop: below structural invalidation plus validated buffer.
- Target: prior high, measured move, or resistance zone above entry.
- RR/expiration/conflicts: mirror the short contract.

### RANGE_MEAN_REVERSION_CANDIDATE

This remains design-only. It requires `FLAT`, confirmed `CONFIRMED_RANGE`, price at a causally established boundary, and a closed inward rejection. Long is considered only at support; short only at resistance. Stop belongs beyond the tested boundary. The first target is the range midline; the opposite boundary may be secondary. A possible boundary break awaits resolution; a confirmed breakout/breakdown forbids the setup. `FLAT` without a boundary rejection is not a setup.

### NO_TRADE_CONTRACT

This is the safe default and records structured reasons. It covers `UNKNOWN`, conflict, missing levels, insufficient RR, staleness, range/trend conflict, data-quality failure, and disabled draft contracts. It has direction `NONE`, entry type `none`, no targets, and at least one `no_trade_reasons` code.

## Output contract

The formal schema is `ENGINE_TREND_21_SETUP_OUTPUT_SCHEMA.json`. `setup_id` identifies one causal premise and must remain stable through `WAIT_CONFIRMATION -> TRADE_CANDIDATE/INVALIDATED`; a materially new zone or later independent attempt receives a new ID. `source_regime` and `source_hypothesis` are copied, never rewritten. `confidence` is nullable because calibration belongs to later labeled validation and must not simply copy regime confidence.

The contracts and complete examples are in `ENGINE_TREND_21_SETUP_CONTRACTS.json`.

## Conceptual live-case audit

These are conservative conceptual classifications against existing ENGINE-TREND-19/20 evidence. They do not change or reinterpret baseline engine output and do not claim fills or profitability.

| Case | Unchanged baseline | Expected setup-layer status | Reason |
|---|---|---|---|
| BTCUSDT 2026-07-13 16:00 | `UNKNOWN`; ENGINE-TREND-20 counterfactual trend-only pass | `NO_TRADE` | `UNKNOWN` is a hard block, and the trend-only contract is disabled pending 20B. |
| SOLUSDT 2026-07-08 06:00 | `DOWN`, confirmed `DOWN_CONTINUATION` | `NO_TRADE` | Directional context is eligible, but the baseline snapshot does not formalize a post-retest entry with complete invalidation/stop/target provenance and qualifying RR. `DOWN` alone cannot promote it. |
| SOLUSDT 2026-07-08 18:30 | `UNKNOWN`, unresolved confirmed-hypothesis conflict | `NO_TRADE` | Unknown and unresolved conflict are both hard blocks. |
| SOLUSDT 2026-07-08 23:45 | `FLAT`, confirmed `CONFIRMED_RANGE`; audited upper boundary `77.8`, close `77.83` | `WAIT_CONFIRMATION` | A range premise and boundary exist, but no closed inward rejection is established; the small boundary excursion must resolve as rejection versus confirmed breakout. No entry is authorized. |

`INVALIDATED` is not assigned to these snapshots because the audit does not provide prior setup-layer state/ID whose premise was subsequently breached.

## Explicit non-changes

- Runtime code changed: no.
- Market-hypothesis runtime changed: no.
- Trading runtime changed: no.
- Thresholds changed: no.
- Composer changed: no.
- `technical_indicator_context` changed: no.
- Exchange/execution integration added: no.
- Backtest or PnL calculation added: no.

