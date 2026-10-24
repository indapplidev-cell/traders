# Scalping v2 setup-family gate trace 01

Date: 2026-10-10 UTC. Scope: `trade-5m-v2`, PAPER, diagnostics only. Implementation commit: `9fb4eef88b8b8b622ee0671fb8af3e44d3f5dbba`.

## Pre-change read-only evidence

For the common closed-candle endpoint 2026-10-10 07:00 UTC, the preceding 24 hours contained 5760 persisted symbol-boundary analyses (20 symbols × 288 boundaries). There were 5060 `NO_SETUP` results and 700 setup candidates: 682 `SCALP_MOMENTUM_CONTINUATION` and 18 `SCALP_BREAKOUT`. Reproduction of the existing ordered v2 micro predicates from persisted causal context attributes those 5060 `NO_SETUP` results to first failed *micro-route* conditions: 4909 no momentum, 23 no direction after momentum, and 128 no entry evidence after momentum and direction. This is not a first-terminal-rejection census for the whole pipeline and does not establish that rejected observations were tradeable.

The existing Schwager producer emitted `SCHWAGER_BREAKOUT_RETEST_HELD` in three analyses. Two remained `NO_SETUP` with `LOW_CONFIDENCE`; one became `SCALP_MOMENTUM_CONTINUATION`. The setup retest rule recognizes `BREAKOUT_RETEST_HELD` and other unprefixed forms but not this prefixed code. No `SCALP_BREAKOUT_RETEST` candidate appeared in this 24-hour window. Recognizing the source code alone would not establish a further executable trade. `market_structure_diagnostics.py` is research-only and is not a live setup evidence source.

## Change and invariant

`SetupDiagnostics` now contains `family_first_unmet_condition` for all seven v2 setup families and `producer_consumer_mismatches` for the observed retest-code mismatch. The trace uses the existing rule predicates and exact v2 micro predicates; `CONDITIONS_MET_NOT_SELECTION` explicitly means that these local conditions were met, not that the family won precedence or passed later gates. Failed analysis preconditions are labeled `ANALYSIS_PRECONDITION_FAILED`. The trace is attached after the existing setup rule, micro route, and family mapping have already decided the result. No producer code is aliased into admission, no threshold or selector changed, and no PAPER/LIVE command is created by the trace.

Tests compare `status`, `setup_type`, and `reason_codes` against the existing decision path, cover the prefixed retest mismatch and serialized trace, and retain the existing v2 micro regression. Scoped setup/profile tests: 42 passed with one pre-existing `trade-5m-v1` test deselected. Broader scoped tests: nine passed and five pre-existing v1 tests failed because the removed `trade-5m-v1` profile cannot resolve. Python compile and `git diff --check` passed. The incompatible v1 tests were not edited.

## Deployment and natural canary

Only `online-orchestrator-5m` was rebuilt and recreated with immutable source label `9fb4eef88b8b8b622ee0671fb8af3e44d3f5dbba`; the running image is `sha256:9d6f35a8ce7304d130d7536fd16acd971ecb08db848b1eacfe95437d0c073178`. The first two natural post-deployment 5m boundaries, 2026-10-10 07:40 and 07:45 UTC, each completed 20/20 symbols, persisted a momentum-family trace in all 40 results, and had zero pipeline errors, order approvals, or opened positions. Both cycles remained 20/20 `NO_SETUP`. Mean run durations were 2971.3 and 2084.7 ms, respectively, versus 2619.1 ms at the immediately preceding 07:35 boundary; this does not establish a causal latency change. The readonly health endpoint reported HTTP 200, `OK`, `CURRENT`, `operational=true`, `ready=true` during the original post-deployment observation. Alembic remained `0037_continuous_two_lifecycle_slots`; the continuous PAPER control row remained `CONTINUOUS_ARMED` generation 16. LIVE and real Binance order execution were not enabled.

On 2026-10-24, Docker Desktop was explicitly restarted at the user's request after a host-side stoppage. The unchanged orchestrator image and source label resumed with zero container restarts. At initial recheck, the last complete pipeline boundary was 2026-10-21 11:10 UTC and market-data backfill was still progressing across the 20 symbols; this historical two-cycle canary is not misrepresented as a fresh October 24 canary. Current freshness must be evaluated separately after full market-data recovery.

## Verdict and next scope

PASS for diagnostic implementation and the two natural October 10 canary cycles; current October 24 market-data freshness remains a separate recovery check. This task improves attribution, not trade conversion. Family absence during one window is not proof of unreachable code, and `NO_SETUP` does not independently establish a missed profitable movement. The next distinct task is causal, read-only comparison of observed family evidence against local gate failures and downstream geometry/economics before requesting any behavioral admission change.
