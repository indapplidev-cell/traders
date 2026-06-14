# Stage ML38 Candle TA Context Feature Layer

## Goal

Implement `fv3_candle_ta_context` and keep research safety: no traders-core, no live, no orders, no auto activation.

## Source Ideas

- Nison ideas formalized: candle morphology, doji/hammer/shooting star, engulfing, harami, star families, window gaps.
- Altunina ideas formalized: technical context, trend structure, support/resistance, indicator confirmation, volatility context.

## Feature Groups

- candle morphology
- candle patterns
- technical context
- regime features

## Safety

- lookahead: protected by backward-only rolling windows and explicit ML38 no leakage tests.
- NaN/inf: protected by safe division, bounded ratios, and ML38 NaN/inf tests.
- no traders-core
- no live
- no orders
- no auto activation

## Execution

- files changed: pending final refresh after full ML38 run
- tests added: ML38 feature, leakage, summary, and report coverage
- pytest results: pending final run
- CLI results: pending final run

## Fresh Grid

- BTCUSDT: pending
- ETHUSDT: pending
- SOLUSDT: pending

## Next Stage

- ML39: not started in ML38 report
