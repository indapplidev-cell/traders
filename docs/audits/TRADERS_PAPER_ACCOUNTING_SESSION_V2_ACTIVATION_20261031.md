# PAPER accounting session v2 activation

Recorded at: `2026-10-31T17:14:00Z`

Environment: production PAPER

Result: `PASS`

## Outcome

- Activated `TRADERS_PAPER_SESSION_02` with immutable baseline `baseline:production-paper-v2` and initial balance `1000 USDT`.
- Preserved the historical `TRADERS_PAPER_SESSION_01` baseline (`100 USDT`) and all 193 historical positions without rewriting their economics.
- Added an explicit `accounting_session_id` boundary to the 11 session-owned PAPER economic tables.
- Migrated production schema from `0037_continuous_two_lifecycle_slots` through `0038_plan_outcome_pre_selector_terminal` to `0039_paper_accounting_session_v2`.
- Reactivated continuous PAPER as `CONTINUOUS_ARMED`, generation 18. LIVE remains disabled.

## Runtime evidence

| Check | Proven state |
|---|---|
| Readiness | `READY` |
| Control | `CONTINUOUS_ARMED`, generation 18 |
| LIVE | `false` / blocked |
| Active session | `TRADERS_PAPER_SESSION_02` |
| Initial/current balance | `1000 / 1000 USDT` |
| New-session closed/open trades | `0 / 0` |
| Accounting reconciliation | `HEALTHY` |
| Mutation readiness after restart | `true`, no denial reasons |
| Production schema | `0039_paper_accounting_session_v2` |
| Operator image revision | `2559a4c36adeb64cfcb44d55dfe633fef6116445` |
| Orchestrator/readonly session implementation revision | `6281051629baed5ae1fe0e8731f5f6df4ff2fdd9` |

The historical tables contain only `TRADERS_PAPER_SESSION_01` rows. The one
new `paper_continuous_control_events` row belongs to
`TRADERS_PAPER_SESSION_02`; no new-session order, fill, position, exit, or
journal rows existed at validation time.

## Safety and recovery

- Confirmed zero open positions and zero active non-expired commands before migration.
- Disabled the continuous worker before migration and stopped writer services while applying it.
- Created scoped recovery dump `/var/lib/postgresql/recovery/pre_session_v2_paper_20261031_170443.dump` before schema mutation; existing WAL/PITR protection was retained.
- Expired historical pending commands were terminally marked failed; no active command crossed the accounting boundary.
- No production order, fill, or position was created by the transition.
- No LIVE setting was enabled and no real Binance order call was made.
- Existing user-owned artifact deletions, forensic reports, and prior `online_trader.md` edits were not included in implementation commits.

## Runtime remediation discovered during activation

The first restarted operator cycle exposed a least-privilege mismatch: terminal
plan reconciliation selected `online_pipeline_runs` using `FOR UPDATE`, while
the PAPER runtime role intentionally has read-only access to pipeline source
tables. The query now uses the existing transaction-scoped PostgreSQL advisory
lock for per-run serialization and does not request a row lock on the read-only
source. The runtime role received the already-declared contract grants
(`SELECT` on `online_pipeline_runs` and `online_pipeline_results`). After the
operator was rebuilt at revision `2559a4c`, multiple worker intervals completed
without the former permission error and mutation readiness returned to `true`.

## Verification

- Focused contract and outcome tests: `16 passed`.
- Earlier implementation validation: `1877 passed, 2 skipped, 1 deselected`.
- Isolated PostgreSQL migration validation proved both 100 and 1000 USDT baselines and the session-v2 defaults.
- Operator, readonly API, and orchestrator containers were rebuilt/recreated only where required; no production deploy outside these PAPER services occurred.
- The first Docker rebuild attempt failed on a transient malformed package-index response. The retry completed successfully; the running operator image reports the expected revision.

## Commits

- `6281051629baed5ae1fe0e8731f5f6df4ff2fdd9` — session split, baseline rotation, schema/API/runtime implementation.
- `2559a4c36adeb64cfcb44d55dfe633fef6116445` — read-only source locking correction.
