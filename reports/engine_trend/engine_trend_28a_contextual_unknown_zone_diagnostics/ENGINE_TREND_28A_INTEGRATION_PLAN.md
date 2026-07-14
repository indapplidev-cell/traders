# ENGINE-TREND-28A integration plan

Current status: offline/report-only callable module. No runtime import or route was added.

Future API/UI exposure can use a one-way adapter after the engine result is finalized:

1. Copy immutable `market_regime`, confidence, candle close/day range, Schwager zones/range/breakout context, indicator context, hypotheses and MTF regimes into `ContextualDiagnosticInput`.
2. Call `diagnose_context` in a reporting/read-model boundary after trading/setup evaluation is complete.
3. Expose the returned object under a separate `contextual_diagnostics` field. Do not merge tags into `reason_codes`, regime selection, composer scores or setup eligibility.
4. UI may render zones, waiting reasons and confirmation checklists. It must label them “diagnostic context / no signal”.
5. Add contract tests proving removal of the diagnostic call leaves engine result, setup result and runtime behavior byte-for-byte unchanged.

Required future gates: API schema review, latency check, source-output adapter tests, explicit runtime non-interference test, and UI copy review. None of these gates authorizes paper or live trading.
