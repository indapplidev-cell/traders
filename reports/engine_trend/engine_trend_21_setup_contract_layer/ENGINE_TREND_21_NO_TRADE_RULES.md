# ENGINE-TREND-21 — NO_TRADE Rules

`NO_TRADE` is a valid, explicit setup-layer answer. It is not low confidence converted into a direction. Multiple reason codes should be retained when multiple hard gates fail.

## Regime and authorization

- `UNKNOWN_REGIME`: unconditional `NO_TRADE`.
- `REGIME_SETUP_MISMATCH`: requested setup direction/type is incompatible with source regime.
- `REQUIRED_HYPOTHESIS_MISSING`: no confirmed hypothesis required by the contract.
- `CONTRACT_NOT_VALIDATED_ENGINE_TREND_20B`: trend-only continuation draft is disabled.
- `CONTRACT_NOT_RUNTIME_AUTHORIZED`: design contract has not passed validation/approval.

## Causality and structure

- `NO_CAUSAL_STRUCTURE`: no qualifying LL/LH, HH/HL, or confirmed range structure.
- `NO_CAUSAL_SETUP_ZONE`: no prior broken/reclaimed level, retest zone, or confirmed range boundary.
- `INDICATOR_ONLY_EVIDENCE`: indicators are the only directional basis.
- `RETEST_NOT_OBSERVED`: continuation contract lacks a causal retest/reclaim sequence.
- `REJECTION_NOT_CONFIRMED`: no closed inward/bearish/bullish confirmation; use `WAIT_CONFIRMATION` only when levels and a live premise already exist.
- `LOOKAHEAD_EVIDENCE_REQUIRED`: the setup could only be constructed using future candles.
- `EVIDENCE_PROVENANCE_MISSING`: required anchor cannot be traced to as-of evidence.

## Invalidations, stops, and targets

- `INVALIDATION_UNDEFINED`: premise has no objective falsification level.
- `INVALIDATION_ALREADY_BREACHED`: invalidation was breached before candidate activation.
- `STOP_UNDEFINED`: no protective stop can be causally derived.
- `STOP_WRONG_SIDE`: stop is not beyond entry in the risk direction.
- `STOP_NOT_BEYOND_INVALIDATION`: stop fails to protect beyond structural invalidation.
- `TARGET_UNDEFINED`: no causal objective exists.
- `TARGET_WRONG_SIDE`: target does not provide positive directional reward.
- `TARGET_ALREADY_BREACHED`: target was reached before the proposed entry.
- `TARGET_BLOCKED_BY_STRUCTURE`: nearer opposing structure makes the target non-reachable under the contract.

## Reward/risk

- `RR_UNCOMPUTABLE`: missing/non-finite entry, stop, target, risk, or reward.
- `NON_POSITIVE_RISK`: directional risk is zero or negative.
- `NON_POSITIVE_REWARD`: directional reward is zero or negative.
- `RR_BELOW_MINIMUM`: no eligible target has `RR >= min_reward_risk`.
- `NET_RR_NOT_VALIDATED`: future runtime gate when costs/slippage are required but unavailable; not computed in ENGINE-TREND-21.

## Conflicts

- `UNRESOLVED_CONFLICT`: confirmed/pending evidence has no safe unique premise.
- `CONFIRMED_OPPOSING_REVERSAL`: confirmed reversal opposes the proposed continuation.
- `CONFIRMED_RANGE_DOMINATES`: range is stronger than a proposed trend continuation.
- `CONFIRMED_BREAKOUT`: forbids range mean reversion.
- `CONFIRMED_BREAKDOWN`: forbids range mean reversion.
- `CONFIRMED_TRAP_CONFLICT`: confirmed trap contradicts entry direction.
- `RANGE_TREND_CONFLICT`: range and trend contexts are both active without validated precedence.
- `MULTIPLE_SETUP_CONFLICT`: incompatible setup candidates survive selection.

When the conflict may resolve and a complete causal premise/levels already exist, emit `WAIT_CONFIRMATION`. Confirmed opposing evidence or unresolved conflict at expiry emits `NO_TRADE`; if it breaches a tracked prior premise, emit `INVALIDATED`.

## Freshness and data

- `SETUP_STALE`: confirmation window expired.
- `SETUP_ZONE_CHANGED`: structural zone was materially redefined.
- `SOURCE_HYPOTHESIS_STALE`: source hypothesis is no longer current/eligible.
- `DATA_QUALITY_FAILURE`: source quality did not pass mandatory checks.
- `INSUFFICIENT_CANDLES`: context/decision window is incomplete.
- `MISSING_OHLCV`: required candle field is absent.
- `IRREGULAR_CADENCE`: timeframe cadence is invalid.
- `DUPLICATE_CANDLES`: duplicate timestamps exist.
- `NON_FINITE_VALUE`: NaN/infinity is present.
- `TIMESTAMP_OR_TIMEFRAME_MISMATCH`: source evidence cannot be aligned causally.

## Terminal representation

A `NO_TRADE_CONTRACT` output must use `direction: NONE`, `entry.type: none`, empty `targets`, and at least one reason code. Null prices describe the absence of a setup; they must never be interpreted as market orders. A new later evaluation may produce a new setup, but must not mutate the historical `NO_TRADE` snapshot.

