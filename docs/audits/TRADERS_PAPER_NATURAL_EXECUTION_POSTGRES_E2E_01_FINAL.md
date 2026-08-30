# TRADERS PAPER natural execution PostgreSQL E2E 01

```text
TASK = PAPER_NATURAL_EXECUTION_POSTGRES_E2E_01
VERDICT = CLOSED_ISOLATED_POSTGRES_E2E
PRODUCTION_ACCEPTANCE = NOT_STARTED_NOT_DEPLOYED
RECONCILED_AT_UTC = 2026-08-30T11:15:01Z
SOURCE_BASE_BEFORE_TASK = 24f0855585aebf413b9abb309060264f15a31909
BRANCH = feature/engine-platform
LIVE = FALSE
PRODUCTION_MUTATIONS = 0
HISTORICAL_APPROVAL_REPLAY = 0
MIGRATION_DIRECTION = UPGRADE_ONLY
```

## Environment and safety proof

The test ran in the task-owned Docker container
`traders-paper-e2e-postgres`, exposed only as `127.0.0.1:55439`. The database
was `paper_test_natural_execution_runtime`; the runtime role was
`paper_test_natural_runtime`. The permanent fixture rejects non-PostgreSQL
URLs, non-loopback hosts, database or principal names without the
`paper_test_` prefix, PostgreSQL versions other than 16, and roles with any of
SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, or BYPASSRLS. Credentials are
never logged by the fixture.

Alembic upgraded the empty isolated database to the single repository head
`0018_promote_5m_production_search`. There was no downgrade. The production
database, production canary control files, protected services, and the 37
historical defective approvals were not read for execution or mutated.

## Natural execution trace

The final isolated run produced:

```text
snapshot_id = market-data-snapshot:v1:b82529da698f56ee91ee9fc4e02c643e04de4dc21f027e71835c0903cbd66fc2
analysis_id = analysis:BTCUSDT:5m:1800000000000:e9bd5bd131a104dc
paper_plan_id = paper:BTCUSDT:5m:1800000000000:risk:BTCUSDT:5m:1800000000000:strategy:v2:620b93362441269d4c1f40b0d6d011d7150a50933b2d4d3b895d7b1f0658144a:834ae396a3ac6bc4:833aaa476ea40cf8
approval_id = paper:risk-approval:v1:1d830b1a4160c2d5361193bd1b4954cdcece064c4387f20fc869bfadc5b7d8ca
adapter_outcome = ELIGIBLE_APPROVAL
candidate_id = paper:production-approval-candidate:v1:7eaf172349dce72729f765d58297728485368aef681e32ff3a515939deb599b0
winner = paper:production-approval-candidate:v1:7eaf172349dce72729f765d58297728485368aef681e32ff3a515939deb599b0
command_id = paper:ingestion-command:v1:752a982942bdf7e5734c844f625723f1302b3a2903d1a8b90fbbbccab0111b0a
entry_order_id = paper:first-canary:entry-order:5263d047b23af9cc81504e818582febbb06ba50242fe3e3ef5e253bb074e9c51
fill_id = paper:fill-id:v1:6442fea734cb06dabd2f5505b202a39ca33fc70211044f5daea6930fdf32c96d
position_id = paper:first-canary:position:8a9f62da1b35ff48257974cb8b9ed1d86b48b6c3605e910d8856bd25ee0ee115
position_state = OPEN
```

No execution provenance field was supplied by the test. The only replacement
boundary was Binance public market-cost HTTP; a causal, deterministic local
cost fixture supplied the same public cost inputs. Candles, analysis, setup,
strategy, risk, PAPER plan, final approval, adapter, selector, command
ingestion, order execution, fill simulation, repositories, lifecycle worker,
and PostgreSQL persistence were real.

## Transition proof

| Transition | Production-facing function | Result |
|---|---|---|
| market snapshot -> analysis watermark | `PipelineRunner.run`; `OnlineAnalysisRunner` | PASS |
| analysis -> natural final approval | `PipelineResultStore.finish`; default final approval materializer | PASS |
| approval -> candidate | `PaperProductionApprovalSourceAdapter.read` | PASS |
| candidate -> winner | `ProductionEligibleApprovalSelector.select` | PASS, eligible count 1 |
| winner -> command | `PaperFirstCanaryEligibleApprovalContinuationWorker.run_once`; `ProductionPaperFirstCanaryExecutor._ingest_candidate` | PASS |
| command -> ENTRY order | `PaperCommandIngestionService.ingest_and_create_entry_order` | PASS, same unit of work |
| ENTRY order -> fill | `ProductionPaperFirstCanaryLifecycleWorker.run_once`; `PaperControlledLifecycleWorker`; `PaperOrderExecutionService.execute_entry` | PASS |
| fill -> OPEN position | repository `apply_entry_fill_and_open_position` inside lifecycle unit of work | PASS |
| DB -> UI projection | `SqlAlchemyReadAdapter.list_paper_positions`; `PaperReadonlyReportingService.positions` | PASS |

The canary was created through `PaperOperatorControlService.arm_first_canary`
and `start_first_canary`, not by direct row insertion. Its initial state was
`WAITING_FOR_ELIGIBLE_APPROVAL`, command/position counts were zero, both limits
were one, persistent control state was `ARMED`, and the persistent-state enum
contains no LIVE state.

## PostgreSQL database proof

| Table | Rows | Relevant ID/state |
|---|---:|---|
| `paper_execution_commands` | 1 | command above; `PENDING`, PAPER |
| `paper_orders` | 1 | ENTRY order above; `FILLED` |
| `paper_fills` | 1 | ENTRY fill above |
| `paper_positions` | 1 | position above; `OPEN` |
| `paper_exit_decisions` | 0 | OPEN-only mandatory E2E |
| `paper_journal_entries` | 6 | entry/accounting journal persisted |

The fill used the real foundation policy: the first eligible closed 1m candle
opened at `100.70`, adverse slippage was read from policy, producing
`100.720140000000000000`; the persisted entry fee was
`0.100069490000000000`. Foreign-key lineage from command to order, order to
fill, and entry order/fill to position was asserted. Numeric precision,
timezone-aware timestamps, JSON payloads, enum/string values, unique
idempotency keys, row-lock continuation, and transactional units of work were
exercised on PostgreSQL 16.

## Idempotency, restart, expiry, and bounds

After the first continuation and lifecycle poll, a repeated approval poll, a
new continuation-worker instance, a repeated lifecycle poll on the same
candle, and a new lifecycle-worker instance left counts at:

```text
commands = 1 -> 1
entry orders = 1 -> 1
fills = 1 -> 1
positions = 1 -> 1
```

The restarted lifecycle correctly returned `WAITING_FOR_EXIT_CANDLE`. A second
natural run evaluated after `valid_until_ms` left command count at zero. A
consumed canary with `max_new_commands=1` and `max_open_positions=1` was no
longer polled, preserving the one-command/one-position bound. Existing focused
tests additionally cover terminal or consumed bounds and executor recovery.

## UI/read-only proof

```text
active_positions = 1
command_id = paper:ingestion-command:v1:752a982942bdf7e5734c844f625723f1302b3a2903d1a8b90fbbbccab0111b0a
position_id = paper:first-canary:position:8a9f62da1b35ff48257974cb8b9ed1d86b48b6c3605e910d8856bd25ee0ee115
symbol = BTCUSDT
state = OPEN
entry_price = 100.72014
```

`command_id` was added additively to the existing position DTO and SQLAlchemy
read projection. No domain state or write path changed.

## Test evidence

| Suite/test | Result | Count | Notes |
|---|---|---:|---|
| `tests/integration/paper_natural_execution_e2e` | PASS | 2 | Full OPEN E2E plus expired approval; PostgreSQL 16 |
| relevant snapshot/analysis/approval/selector/canary/lifecycle/API matrix | PASS | 1910 | One known stale OpenAPI inventory assertion explicitly deselected |
| `tests/paper_production_approval_source_adapter/test_adapter_contract.py` | PASS | 1438 | Complete consumer contract file |
| `tests/paper_controlled_worker_retry/test_postgres_full_lifecycle.py` | PASS | 1 | Existing OPEN -> exit -> CLOSED, accounting/journal exact-once proof |
| compileall | PASS | n/a | `app` and new integration package |
| `git diff --check` | PASS | n/a | line-ending warnings only |

The existing full lifecycle PostgreSQL test is the bounded evidence for close
order, close fill, CLOSED position, realized PnL, and journal/accounting. This
task deliberately keeps the new natural-path regression focused on the missing
entry-to-OPEN invariant.

## Pre-existing failures

1. `tests/engine_risk/test_scalping_risk_order_and_sizing.py::test_preview_does_not_reserve_but_authoritative_risk_does`
   was last changed in `1f2eca17dbf142d741bbee4377631b35c442b05a` and was
   unchanged from the task base. Its legacy helper now produces
   `RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE`. It is not blocking: the new 5m E2E
   uses the real `RiskRunner` and proves `RISK_PRE_APPROVED_RESEARCH` before
   natural materialization.
2. `tests/paper_controlled_runtime_canary/test_contract_matrix.py::test_contract_exposes_exact_task_and_migration_identity`
   was last changed in `78035f12170ac97612dc9b3945828baa8a6394f4` and was
   unchanged from the task base. It expects legacy head 0014 while that
   historical canary constant resolves to 0015 and repository head is 0018.
   It does not exercise approval, selector, command, fill, position, or current
   PostgreSQL schema migration.

An additional stale read-only inventory assertion expects 27 GET operations
while the pre-task application exposes 28. The task's additive position field
does not add an endpoint; the assertion is unrelated and remains untouched.

## Bounded production-like validation procedure

Production deployment was not authorized and was not performed. After an
explicitly authorized build/deploy from the tested project-state commit:

1. Verify image source label/digest resolves to that exact commit; apply only
   forward migrations and confirm the single head is 0018.
2. Confirm `LIVE=false`, control state and WAL/PITR readiness through read-only
   diagnostics, then canonically arm at most one PAPER command and one open
   position for the approved symbol scope.
3. Record the existing 37 defective approval IDs as an exclusion set. Do not
   backfill, replay, select, or alter them.
4. Wait only for a final approval created by a fresh natural market event after
   deployment. Require a `market-data-snapshot:v1:` watermark and
   `ELIGIBLE_APPROVAL` before selection.
5. Observe winner, command, ENTRY order, ENTRY fill, and OPEN position with
   command and position counts no greater than one. Do not invoke repositories
   or lifecycle mutations manually.
6. Corroborate the same IDs in PostgreSQL read-only queries and the PAPER
   read-only API. Acceptance requires the UI projection to show the OPEN
   position and command ID.
7. On the first broken transition, stop acceptance and record that transition
   as the new blocker. Never substitute a historical approval.

## Deployment provenance

The tested working tree is the tree to be captured by the project-state commit;
its exact SHA is recorded by the subsequent status reconciliation. No image was
built, no tag or digest was created, no push occurred, and no deployment ran.

