# Scalping v2 setup-gate diagnostics and causal stop comparison

Date: 2026-10-10 UTC. Profile: `trade-5m-v2`, PAPER. This task does not change admission thresholds, stop/target geometry, costs, RR/EV, risk, selector, or LIVE state.

## Fresh pre-change evidence

PostgreSQL `online_pipeline_runs` joined to `online_pipeline_results`, common closed boundary 2026-10-10 06:15 UTC, last four hours: 960 symbol-boundary rows. Production setup statuses: 885 `NO_SETUP`, 75 `SETUP_CANDIDATE`. Reproduction of the current ordered micro-gate predicates from persisted causal analysis context classified the 885 `NO_SETUP` rows as 835 without momentum context, 5 without direction after momentum, and 45 without entry evidence after momentum and direction. This classification is diagnostic; it does not assert that any rejected row would have passed downstream trading gates.

Of 75 production candidates, 57 first failed `SCALP_REJECT_CAUSAL_STOP_TOO_WIDE`; 17 had pre-recovery non-authoritative commission, and one had another source rejection. The 57 stop distances averaged 113.47 bps (range 36.01–311.11 bps) versus the unchanged 36 bps envelope. A causal read-only comparison using each candidate's five latest closed 5m candles (five present for every candidate), their directional min-low/max-high, and the existing ATR buffer found only **3/57** stop-rejected rows would fit the envelope before price normalization. This is an envelope-only upper bound, not a full target/cost/RR/EV replay or evidence for a better stop policy. No alternative stop was promoted.

## Change and safeguards

For an analyzed v2 `NO_SETUP` with `NO_STRUCTURAL_SETUP`, setup diagnostics now append the first failed micro predicate: `SCALPING_V2_NO_MOMENTUM_CONTEXT`, `SCALPING_V2_NO_DIRECTIONAL_CONTEXT`, `SCALPING_V2_ENTRY_EVIDENCE_NOT_CONFIRMED`, or `SCALPING_V2_ENTRY_QUALITY_REJECTED`. Analysis precondition failures (`ANALYSIS_NOT_ANALYZED`, `NOT_ENOUGH_DATA`) retain their original diagnostic attribution. Existing status, setup type, reason codes, candidate admission, and all downstream decisions are unchanged. The new detail is persisted in `setup_payload_json.diagnostics.diagnostic_reasons` for subsequent natural cycles; the existing Funnel terminal reason remains authoritative.

## Validation and limits

Focused setup/profile/Funnel tests: 56 passed. Python compile and scoped whitespace check passed. Broader legacy tests are currently incompatible with removed `trade-5m-v1` assumptions, while one i18n route-count assertion expects 28 rather than the actual 29; these failures are outside the changed files and are not treated as a PASS. Natural PAPER plan-to-command-to-position passage is not proven by this diagnostics-only change. The unresolved trading bottlenecks remain setup formation and the causal stop envelope. A different stop-selection policy requires a separate, fully causal shadow outcome comparison including target, costs, RR/EV and risk before any proposal to change admission.
