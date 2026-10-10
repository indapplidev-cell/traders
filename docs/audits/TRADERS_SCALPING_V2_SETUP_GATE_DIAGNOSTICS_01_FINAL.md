# Scalping v2 setup-gate diagnostics and causal stop comparison

Date: 2026-10-10 UTC. Profile: `trade-5m-v2`, PAPER. This task does not change admission thresholds, stop/target geometry, costs, RR/EV, risk, selector, or LIVE state.

## Fresh pre-change evidence

PostgreSQL `online_pipeline_runs` joined to `online_pipeline_results`, common closed boundary 2026-10-10 06:15 UTC, last four hours: 960 symbol-boundary rows. Production setup statuses: 885 `NO_SETUP`, 75 `SETUP_CANDIDATE`. Reproduction of the current ordered micro-gate predicates from persisted causal analysis context classified the 885 `NO_SETUP` rows as 835 without momentum context, 5 without direction after momentum, and 45 without entry evidence after momentum and direction. This classification is diagnostic; it does not assert that any rejected row would have passed downstream trading gates.

Of 75 production candidates, 57 first failed `SCALP_REJECT_CAUSAL_STOP_TOO_WIDE`; 17 had pre-recovery non-authoritative commission, and one had another source rejection. The 57 stop distances averaged 113.47 bps (range 36.01–311.11 bps) versus the unchanged 36 bps envelope. A causal read-only comparison using each candidate's five latest closed 5m candles (five present for every candidate), their directional min-low/max-high, and the existing ATR buffer found only **3/57** stop-rejected rows would fit the envelope before price normalization. This is an envelope-only upper bound, not a full target/cost/RR/EV replay or evidence for a better stop policy. No alternative stop was promoted.

## Change and safeguards

For an analyzed v2 `NO_SETUP` with `NO_STRUCTURAL_SETUP`, setup diagnostics now append the first failed micro predicate: `SCALPING_V2_NO_MOMENTUM_CONTEXT`, `SCALPING_V2_NO_DIRECTIONAL_CONTEXT`, `SCALPING_V2_ENTRY_EVIDENCE_NOT_CONFIRMED`, or `SCALPING_V2_ENTRY_QUALITY_REJECTED`. Analysis precondition failures (`ANALYSIS_NOT_ANALYZED`, `NOT_ENOUGH_DATA`) retain their original diagnostic attribution. Existing status, setup type, reason codes, candidate admission, and all downstream decisions are unchanged. The new detail is persisted in `setup_payload_json.diagnostics.diagnostic_reasons` for subsequent natural cycles; the existing Funnel terminal reason remains authoritative.

## Validation and limits

Focused setup/profile/Funnel tests: 56 passed. Python compile and scoped whitespace check passed. Broader legacy tests are currently incompatible with removed `trade-5m-v1` assumptions, while one i18n route-count assertion expects 28 rather than the actual 29; these failures are outside the changed files and are not treated as a PASS. Natural PAPER plan-to-command-to-position passage is not proven by this diagnostics-only change. The unresolved trading bottlenecks remain setup formation and the causal stop envelope. A different stop-selection policy requires a separate, fully causal shadow outcome comparison including target, costs, RR/EV and risk before any proposal to change admission.

## Deployment and natural PAPER canary

Implementation SHA: `fe93e7f935f8a34d8727f7ddfa5072c68583f1ef`. Only `online-orchestrator-5m` was rebuilt and recreated; its running image is `sha256:7c99e97a8b7e6f3edb1932fc45bef22539114ec7207db181a04be1be6cd63984` and its immutable source label matches that SHA. The readonly API and other services were not recreated.

The first two complete natural post-deployment 5m boundaries, 06:35 and 06:40 UTC, each persisted 20/20 symbol results. At 06:35, 19 `NO_SETUP` rows persisted `SCALPING_V2_NO_MOMENTUM_CONTEXT`, while the one WLDUSDT setup candidate retained the existing stop-envelope rejection (140.15 bps versus 36 bps). At 06:40, all 20 `NO_SETUP` rows persisted the new momentum diagnostic. There was no PAPER plan or position in those two cycles. The orchestrator was running with zero restarts; readonly `/api/v1/health` returned HTTP 200, `OK`, `CURRENT`, `operational=true`, `ready=true`. The commission sidecar was `READY` for 20 symbols with zero refresh failures and a 06:34:33 UTC success. Alembic remained `0037_continuous_two_lifecycle_slots`. The operator control state remained `PAPER`, `allow_live=false`, and runtime health reported `live_allowed=false`. No real Binance order endpoint was called.
