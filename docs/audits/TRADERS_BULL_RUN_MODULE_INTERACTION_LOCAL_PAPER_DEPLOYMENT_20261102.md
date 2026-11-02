# Traders bull-run native-module interaction: local PAPER deployment

## Verdict

`PASS_LOCAL_PAPER_DEPLOYMENT_WITH_LIVE_DISABLED`

The production-like local Traders contour was rebuilt from project-state commit
`5f4320378759fd6173eb99430a599d58eb080dea`.  The change corrects the interaction
between Altunina, Schwager and Nison: a LONG candidate now requires an explicitly
bullish independent verdict and a causal native-module consensus.  A neutral
verdict can no longer enter through the calibrated path.

This is an interaction correction, not a claim that each native theory engine was
individually directionally inverted.  The corrected replay found no selected event
with a wrong native direction; the proven defect was conservative/empty projection
and admission of a neutral aggregate verdict in the prior calibration path.

## Deployed runtime

- Orchestrator container: `traders-ml-online-orchestrator-5m-1`
- Orchestrator source revision: `5f4320378759fd6173eb99430a599d58eb080dea`
- Orchestrator runtime image ID:
  `sha256:0785d572ee72c6024cb2010a2a0d66e319497e7f08a2d81d8662d1fceabbee23`
- Orchestrator started at: `2026-11-02T18:50:11.628415866Z`
- Orchestrator restart count at verification: `0`
- Read-only API container: `traders-readonly-api-readonly-api-1`
- Read-only API source revision: `5f4320378759fd6173eb99430a599d58eb080dea`
- Read-only API runtime image ID:
  `sha256:444ffebbe64ecc3a81b9bca0d64e46e501f06d4d3ac672638b78a543d46ee04d`
- Read-only API health at verification: `healthy`
- Make Impress containers were not rebuilt, restarted or modified.

## Active parameters

- Trade-parameter file SHA-256:
  `d3ba540df4b64bf4385882a36387fe16262369a040bf7e6b71d688d7203438a0`
- Active config hash:
  `794c3ae991dfe82e2c27f1d011f6f6178399db40ce0036e6820abfb2f4b5ba8a`
- Resolved config hash:
  `810ee1d85255d5f7fb2adaf2974e1b32628ec06427620d4a6fe6ed9878635c17`
- Entry weights: `25 / 4 / 12 / 15 / 21 / 8 / 15`
- Entry threshold: `45`
- Exit weights: `40 / 10 / 16 / 34`
- Exit thresholds: `40 / 75 / 90`
- Analytical profit-lock buffer: `8 bps`
- Active parameter set: `scalping-v2-set-2`

The server-owned YAML is intentionally ignored by Git.  It was mounted into both
the orchestrator and read-only API and both resolved the same active configuration.

## Runtime safety evidence

- Runtime mode: `PAPER`
- Runtime enabled: `true`
- `live_allowed`: `false`
- Operator state: `CONTINUOUS_ARMED`
- Operator health: `HEALTHY`
- Commands used on the verification UTC day: `0`
- First post-deployment natural boundary: `2026-11-02T18:55:00Z`
- Boundary completion: `20 / 20` symbols, `CURRENT`, cycle complete
- Boundary result: `0` selected, `0` PAPER commands, `0` positions opened
- Production database schema/Alembic state: unchanged
- No LIVE activation or real Binance order call was performed by this task.

## Corrected historical evidence

The verifier was rerun after requiring native-module agreement:

- labelled October bull-run events: `140`
- module-confirmed entry candidates: `122`
- successful causal trades with net result at least `+8 bps`: `85`
- event-conditioned coverage: `60.7142857%`
- median successful net result: `+20.3551464 bps`
- mean captured excursion: `66.15%`

The earlier `100 / 140` figure is superseded.  Eighteen previously successful
replays had a neutral expert direction and are now correctly excluded.  The
`85 / 140` figure passes the requested 60% event-conditioned research gate, but it
is not a whole-market win rate and does not qualify LIVE trading.

Verifier outputs were byte-identical between the primary and repeat run.  The full
method and hashes are recorded in
`TRADERS_BULL_RUN_NATIVE_MODULE_INTERACTION_REMEDIATION_20261102.md`.

## Verification

- Focused module/calibration/exit/research suite: `16 passed`
- Earlier expanded focused suite for this change: `29 passed`
- Python compilation: `PASS`
- One broader legacy setup test still references removed profile `trade-5m-v1`;
  this is pre-existing test debt and is unrelated to the deployed interaction.

## Remaining qualification

The local desktop client reads the rebuilt read-only API and therefore sees the
new active parameters and all new pipeline results generated after deployment.
Historical rows are not rewritten.  Whole-market false-entry qualification over
the 2,240 outside-event observations and the immutable November holdout remain
mandatory before any separate LIVE-readiness decision.
