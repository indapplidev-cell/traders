# ENGINE-TREND-28A Contextual UNKNOWN / Zone Diagnostics

## Decision

Final status: `ENGINE_TREND_28A_COMPLETED_CONTEXTUAL_DIAGNOSTICS`.

The source engine result remains authoritative and unchanged. The new module is an offline explainability read-model: it consumes an already finalized regime plus candle/zone/hypothesis/indicator/MTF context and returns `NO_ACTION`. It is not imported by the engine facade, composer, setup contracts or trading runtime.

No runtime, trading runtime, production threshold, composer rule, market hypothesis rule, technical indicator rule, setup contract, profitability label or source regime was changed. No diagnostic creates a trade signal or setup.

## Implemented diagnostic vocabulary

- Range/location: `LOCAL_RANGE_UNCONFIRMED`, `CONFIRMED_RANGE_CONTEXT`, `INSIDE_RANGE`, `NEAR_RESISTANCE`, `NEAR_SUPPORT`, `NEAR_UPPER_RANGE_BOUNDARY`, `NEAR_LOWER_RANGE_BOUNDARY`.
- Missing confirmation: `BREAKOUT_NOT_CONFIRMED`, `BREAKDOWN_NOT_CONFIRMED`, `WAIT_FOR_CONFIRMATION`, `NO_CAUSAL_HYPOTHESIS`.
- Context/risk: `INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER`, `LOW_TREND_STRENGTH`, `MTF_CONFLICT`, `HIGHER_TF_BEARISH_RISK`, `HIGHER_TF_BULLISH_RISK`.
- Known audit gaps/conflicts: `BEARISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS`, `BULLISH_STRUCTURE_WITHOUT_CONFIRMED_HYPOTHESIS`, `UNRESOLVED_HYPOTHESIS_CONFLICT`, `RANGE_TREND_CONFLICT`.
- Terminal diagnostic state: `NO_ACTION`.

The constants `DIAGNOSTIC_NEAR_ZONE_PCT=0.50` and `DIAGNOSTIC_NEAR_ZONE_ATR=1.00` are display/proximity settings used only to decide whether a zone should be mentioned. They are not production thresholds and cannot affect regimes, setup eligibility or trading.

## Output contract

The JSON Schema locks `action` to `NO_ACTION`. Its safety object locks `source_regime_preserved=true`, `setup_created=false`, `trade_signal_created=false`, and `diagnostics_only=true`. Zone payloads contain boundaries, percent/ATR distance, source and touch count when available. `confirmation_needed` is explanatory copy, not an executable condition.

## ETHUSDT 2026-07-14 live/screenshot case

The source remains `UNKNOWN` at confidence `0.25`; action remains `NO_ACTION`. Diagnostics identify local unconfirmed consolidation, nearby pivot support/resistance, missing breakout/breakdown confirmation, weak-to-moderate bullish indicator pressure without a causal hypothesis, low ADX, and a 4h bearish risk conflicting with neutral 15m/1h states.

Human explanation: “Локальная консолидация под сопротивлением 1793–1794 при bearish-risk на 4h. Long запрещён до закрытого пробоя/ретеста. Short запрещён до rejection и breakdown ниже локальной поддержки.”

## Known-case validation

- BTCUSDT 2026-07-13 16:00 remains `UNKNOWN / NO_ACTION`: bearish structure and indicator pressure exist, but the DOWN continuation causal hypothesis is missing.
- SOLUSDT 2026-07-08 18:30 remains `UNKNOWN / NO_ACTION`: `DOWN_CONTINUATION` conflicts with `CONFIRMED_RANGE`, producing `UNRESOLVED_HYPOTHESIS_CONFLICT` and `RANGE_TREND_CONFLICT`.
- SOLUSDT 2026-07-08 23:45 remains `FLAT`; diagnostics add `CONFIRMED_RANGE_CONTEXT` and `INSIDE_RANGE` without creating a setup.

## Historical diagnostic coverage

Available ENGINE-TREND-18B metadata contains 18 `UNKNOWN` rows: 8 are eligible for `LOCAL_RANGE_UNCONFIRMED`, 10 expose confirmed range context, 9 expose range/directional-hypothesis conflict, and all 18 lack a selected causal hypothesis. ENGINE-TREND-20 contains 18 `UNKNOWN` rows; 3 carry `WEAK_ADX` and therefore support `LOW_TREND_STRENGTH`.

Historical zone distances, indicator vote direction and MTF snapshots are absent from those artifacts. Their counts are explicitly marked `not_observable`; zero means “not reconstructible from available fields”, not “condition absent”. Source regimes were not recomputed or changed.

## Verification

- Focused test: `9 passed`.
- Required suite: `365 passed in 105.57s` using all `tests/test_engine_trend_*.py` files.
- `git diff --check`: exit code 0. Git reported LF→CRLF conversion warnings for pre-existing modified tracked files; no whitespace error was reported. New 28A files use LF only.

## Acceptance result

All acceptance criteria are satisfied: meaningful diagnostics are available, nearest zones are represented when supplied, ETH/BTC/SOL cases are explained, source decisions stay immutable, and no trading signal exists. API/UI integration remains a future read-model-only stage.
