# Scalping v2 post-fix plan selector continuation remediation 01

Date: 2026-09-25

Scope: `trade-5m-v2`, `trading-universe-v3` (20 symbols), PAPER only. LIVE remained disabled. No real Binance order placement call was made.

## Verdict

`PASS` for implementation, deterministic PostgreSQL E2E, deployment, source-revision parity, and production health. The bounded natural observation window contained no new PAPER plan, so natural behavior is recorded as `NATURAL_PLAN_NOT_AVAILABLE_IN_BOUNDED_WINDOW`, not as a natural PASS.

The production defect was a continuation identity loss after a winner had already been persisted. `ProductionPaperFirstCanaryExecutor.execute_continuous_once()` reserved a continuous canary from the selected candidate, but a later poll tried to reproduce that candidate from the newest approval-source snapshot. Once a newer run replaced the selected run in that snapshot, or the current snapshot no longer contained an eligible candidate, the active canary could not be matched. It eventually failed with `CONTINUOUS_RESERVED_APPROVAL_EXPIRED`; the durable selected plan later became `EXPIRED_BEFORE_EXECUTION` without a command.

## Before: fixed 12-hour forensic window

Canonical PostgreSQL was queried for `2026-09-23T16:44:00Z <= first_observed_at < 2026-09-24T04:44:00Z`. The prompt's named `funnel_2409_034223_968.jsonl` was not present in Downloads or the repository, so the database is the authoritative source.

| Measure | Canonical result |
|---|---:|
| PAPER plans | 30 |
| cycles containing a PAPER plan | 25 |
| selected winners | 25 |
| `EXPIRED_BEFORE_EXECUTION` | 24 |
| `ENTRY_FILL_WINDOW_MISSED` | 1 |
| loser plans / `LOWER_SELECTOR_RANK` | 5 / 5 |
| NULL terminal outcome | 0 |
| commands | 0 |
| positions | 0 |

The prompt's approximate `35` plans and `5` NULL losers were not reproduced. The fixed database window contains exactly three groups: 24 selected/expired winners, five terminalized rank losers, and one selected late winner with `ENTRY_FILL_WINDOW_MISSED`.

All 144 `trade-5m-v2` boundaries in this window contain exactly 20 distinct symbols and 20 completed pipeline runs. There are zero incomplete cycles. Each of the 25 cycles containing plans has exactly one selected winner; the five multi-plan cycles each have one `LOWER_SELECTOR_RANK` loser. This disproves the proposed partial-cycle/late-loser race for the audited window. No new cycle barrier or selector policy was introduced.

The 24 valid-timing winners map to forensic category `D. WINNER_PERSISTED_BUT_CONTINUATION_NOT_CLAIMED`. Their outcome rows had `selector_state=SELECTED`, `selected_winner=true`, rank 1, no command, and later expiry. The paired continuous canaries had no approval/command/position and terminated as `CONTINUOUS_RESERVED_APPROVAL_EXPIRED`. The one true late winner maps to category `I. LEGITIMATE_ENTRY_FILL_WINDOW_MISSED` and remains unchanged.

## Root causes

`ROOT_CAUSE_1 = app.operator_control.production_executor.ProductionPaperFirstCanaryExecutor.execute_continuous_once` re-read the latest per-symbol approval snapshot for an already reserved continuous cycle and attempted to rediscover its candidate through `continuous_cycle_id`. The canary stored only the non-invertible derived cycle id, so a newer/latest source row could make the original selected candidate undiscoverable.

`ROOT_CAUSE_2 = app.engine_paper.production_approval.PaperProductionApprovalSourceAdapter.read` intentionally returns the latest completed run per symbol. That behavior is correct for new selection but was incorrectly reused for continuation of a previously selected run.

`ROOT_CAUSE_3 = app.engine_paper.plan_execution_outcome.PaperPlanExecutionOutcomeStore` already held the canonical selected `pipeline_run_id`, but exposed no lookup/claim operation for restart-safe continuation. The expiry sweep therefore had no durable marker that execution was in flight.

`ROOT_CAUSE_NULL_LOSERS = NOT_REPRODUCED_IN_CANONICAL_DB`. Every participating plan in the audited completed cycles has a durable selector state and terminal semantics. The missing export file prevents reconciling the prompt's five alleged NULL rows against a separate projection revision.

## Fix

- `PaperPlanExecutionOutcomeStore.pending_selected_run_id()` resolves the oldest unconsumed selected winner for the current control generation.
- `SqlAlchemyPaperProductionApprovalReader.read_run()` and `PaperProductionApprovalSourceAdapter.read_by_run_id()` reconstruct the exact persisted run under the existing repeatable-read/read-only transaction contract. Continuation no longer re-ranks a durable winner against a newer snapshot.
- `claim_continuation()` persists claim timestamp, attempt, generation, selection-to-claim latency, and remaining causal window under a row lock. Existing cluster-wide PostgreSQL advisory locking still serializes workers by control generation.
- A capacity-blocked candidate can be atomically reclaimed only for the four existing typed capacity reasons. Other terminal outcomes remain terminal.
- The expiry sweep does not overwrite a claimed in-flight row. If the exact selected run is no longer claimable, the outcome is terminalized with `SELECTED_PLAN_NOT_CLAIMABLE` instead of remaining a silent orphan.
- Refinement now merges its details with continuation telemetry instead of replacing it. Funnel/export already projects `refinement_details`, so it exposes `selector_selected_at`, `continuation_status`, `continuation_claimed_at`, `continuation_attempt`, `command_created_at`, and the derived timing fields without a schema migration.
- Entry-window, TTL, strategy, setup, geometry, target, stop, RR, cost, commission, bootstrap, empirical, risk, portfolio, maximum-command, maximum-open, universe, 15m, and LIVE policies were not changed.

## Validation

- `tests/paper_plan_execution_outcomes/test_outcome_store.py`: 8 passed. Covers durable claim/reclaim, claim observability, terminal reject, restart-safe refinement, replay, and claim-versus-expiry behavior.
- Continuation worker concurrency and restart cases: 2 passed (`test_two_concurrent_workers_obtain_one_database_claim`, `test_restart_and_crash_before_command_rediscover_same_waiting_row`).
- Focused continuation/ranking run: 21 passed; one pre-existing stale assertion still expects Alembic predecessor `0019_first_class_15m_domain` while the current contract is `0026_scalping_1m_entry_refinement`.
- The broader legacy continuation file also retains three pre-existing profile-v1/15m fixture failures because runtime authority now exposes only `EXECUTION_TIMEFRAMES=('5m',)`. These failures are outside this change and were not hidden.
- Isolated PostgreSQL 16 E2E on `paper_test_v2`: the two-position continuous scenario passed. It proves two natural fixture plans without re-arm, one winner at a time, durable loser/capacity semantics, command/fill/open-position persistence, restart/replay safety, and zero duplicates.
- Exact-run PostgreSQL rehydration passed and proved that candidate id, lineage, and watermark are identical when reconstructed from the durable selected `run_id`.
- `python -m compileall` passed for changed application and test modules.

## Production deployment

Implementation revision: `8e2771b83793c097e1dc9453e2f10a474ebb9068`.

- Operator Control rebuilt/recreated at `8e2771b83793c097e1dc9453e2f10a474ebb9068`.
- Readonly API rebuilt/recreated at the same revision for projection parity.
- Orchestrator was not affected and remains at `3a5b5b6a0a7787a48eb6eea09b0c67eeb39c393c`.
- Production Alembic remains `0035_scalping_v2_ingestion_policy_contract`; no migration was needed.
- Operator, readonly, orchestrator, market-data, calibration, and PostgreSQL containers are running; operator and readonly are healthy.
- `/api/v1/health`, `/api/v1/paper/readiness`, `/api/v1/trading/funnel?trade_profile=trade-5m-v2`, `/api/v1/analysis`, `/api/v1/trading-universe`, and `/api/v1/paper/positions` all returned HTTP 200 after the final deploy.
- Readiness is `READY`, control is `CONTINUOUS_ARMED`, mutation is PAPER-only, selector/approval/execution workers are active, and `live_allowed=false`.
- Operator logs after deploy contain no traceback, error, or exception.

No production lifecycle row was modified or backfilled. No command or position was created manually. Historical expired rows remain immutable evidence.

## Natural post-deploy observation

The bounded window `2026-09-25T04:56:50Z` through `2026-09-25T05:11:43Z` contained zero new PAPER plans, zero winners, and zero commands. Result: `NATURAL_PLAN_NOT_AVAILABLE_IN_BOUNDED_WINDOW`. Per the task contract this is not a blocker because deterministic PostgreSQL E2E and production health passed, and it is not reported as a natural production PASS.

## Final invariants

```text
FINAL_STATUS = PASS
FINAL_VERDICT = DURABLE_SELECTED_PLAN_CONTINUATION_REPAIRED_AND_DEPLOYED
CYCLE_COMPLETENESS_CONTRACT = EXISTING_20_OF_20_CONTRACT_PROVED; NO_CHANGE_REQUIRED
SELECTOR_DURABLE_STATE = EXISTING_AND_COMPLETE; NULL_SELECTOR_STATE=0
CONTINUATION_DURABLE_CLAIM = IMPLEMENTED
ENTRY_WINDOW_CONTRACT_CHANGED = NO
TTL_CHANGED = NO
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
CURRENT_BLOCKER = NONE_FOR_IMPLEMENTATION_DEPLOYMENT_OR_HEALTH; NATURAL_PLAN_NOT_AVAILABLE_IN_BOUNDED_WINDOW
NEXT_ACTION = OBSERVE_THE_NEXT_NATURAL_PLAN_AND_REQUIRE_CLAIM_PLUS_COMMAND_OR_TYPED_REJECT
```
