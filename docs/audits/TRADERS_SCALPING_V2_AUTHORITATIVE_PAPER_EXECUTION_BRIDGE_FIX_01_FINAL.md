# TRADERS_SCALPING_V2_AUTHORITATIVE_PAPER_EXECUTION_BRIDGE_FIX_01

## Final operational verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_NATURAL_SCALPING_V2_PAPER_POSITION_OPEN

SCALPING_V2_PROFILE_ID = trade-5m-v2
SCALPING_V2_VERSION = trade-5m-v2
SCALPING_V2_AUTHORITATIVE = PASS

SCALPING_V1_ACTIVE_NEW_CANDIDATES = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_APPROVALS = FORBIDDEN
SCALPING_V1_SELECTOR_PARTICIPATION = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_COMMANDS = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_POSITIONS = FORBIDDEN

TRADE_15M_VERSION = trade-15m-v1
TRADE_15M_CONFIG_CHANGED = NO
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS

SELECTOR_ID = eligible-approval-ranking-v1
MAX_NEW_COMMANDS_PER_CYCLE = 1
MAX_OPEN_POSITIONS = 1
MULTI_APPROVAL_POLICY = DETERMINISTIC_RANKING_ONE_WINNER_NON_WINNERS_EXPLICIT_NOT_SELECTED
RANKING_FIELDS = risk_score_desc,planned_risk_reward_desc,strategy_score_desc,closed_until_ms_desc,source_run_id_asc,final_approval_id_asc,candidate_id_asc,symbol_asc
TIE_BREAK = candidate_id_asc_then_symbol_asc

ROOT_CAUSE = STALE_READINESS_HTTP_TIMEOUT_AND_DISPATCH_CADENCE; MISSING_PRODUCTION_V2_SIMULATION_POLICY; V2_SCORE_CONTRACT_MISMATCH; OPENED_LIFECYCLE_OVERWRITTEN_BY_LATER_APPROVAL_EXPIRY_IN_FUNNEL; V2_POSITION_JOURNAL_CAUSATION_OVERWRITTEN_BY_REQUEST_CAUSATION
ROOT_CAUSE_FIXED = YES

READINESS_STATE = READY_CONTROL_ARMED_GENERATION10_WAITING_FOR_ELIGIBLE_APPROVAL_MUTATION_READY_ACCOUNTING_HEALTHY_LIVE_FALSE
READINESS_REASONS = NONE

NATURAL_WINNER_SYMBOL = LINKUSDT
NATURAL_WINNER_RANK = 1
NATURAL_WINNER_PROFILE_VERSION = trade-5m-v2
NATURAL_WINNER_CANDIDATE_ID = paper:production-approval-candidate:v1:deea1cbc4107c252ca024a160e8ddbbde8d9f1997c6b7c32a49daad714cb412e
NATURAL_WINNER_APPROVAL_ID = paper:risk-approval:v1:cfc87745a46d026b1db01b58d735c7f98fa5eea9f9cfca5aead3337f1eb3590e
NATURAL_WINNER_PLAN_ID = paper:LINKUSDT:5m:1788405900000:risk:LINKUSDT:5m:1788405900000:strategy:v2:ff66ef75603226e3c9b4298673a5ca8f6eb3dbf8fae427c15a8a4890bfee1f2b:de06e5a74954ab3b:c02fcda8bf9fcfca

COMMAND_ID = paper:ingestion-command:v1:f0b7ecb26a44b532c494a541af5e0af47e40de349e564afc11457e65929692a7
COMMAND_STATUS = CREATED_PERSISTED_QUEUE_STATE_PENDING_ENTRY_ORDER_FILLED

POSITION_ID = paper:first-canary:position:da114d344a74676d896fd2908daed69cf3c67caa6fb1fc69bf63e530ee807cdc
POSITION_STATUS = OPEN_AT_ACCEPTANCE_NATURALLY_CLOSED_AFTER_ACCEPTANCE

EXPIRY_RACE_FIXED = PASS
READINESS_REGRESSION_FIXED = PASS
GENERIC_UNAVAILABLE_VALUES_AFTER = 0_FOR_REQUIRED_REACHED_WINNER_FIELDS
FUNNEL_PAPER_PARITY = PASS
POSTGRES_E2E = PASS_6
NATURAL_V2_POSITION_OPEN = PASS

DEPLOYED_COMMIT = 6be591a6231f6250b99efeb5ee9f20e2998010fe
ALEMBIC_HEAD = 0023_scalping_v2_journal_causality
DESKTOP_HEAD = 78f124aa9dce0131b759939ef02962edb8d2bb16
MOBILE_HEAD = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db

LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0

REMAINING_BLOCKERS = NONE
NEXT_ACTION = CONTINUE_NORMAL_SCALPING_V2_PAPER_CANARY_OPERATION_WITHOUT_ENABLING_LIVE
```

## Natural production acceptance

The final acceptance winner under deployed source commit
`6be591a6231f6250b99efeb5ee9f20e2998010fe` and schema revision
`0023_scalping_v2_journal_causality` was the `LINKUSDT` Scalping v2 cycle at
boundary `1788405900000` (2026-09-03 03:25:00 UTC), pipeline run
`orchestrator:2a31abadec8d4cfc81ac759a17032d8c`. Its natural plan and immutable final
approval were selected at rank 1. The executor created exactly one PAPER
command on the first attempt, the entry order filled, and position
`paper:first-canary:position:da114d344a74676d896fd2908daed69cf3c67caa6fb1fc69bf63e530ee807cdc`
became `OPEN` at 03:26 UTC.

The command uses `simulation:scalping-v2:foundation:v1`; the fill preserves the
same policy. The command joins to the v2 pipeline run, and the entry order/fill
join to the OPEN position. There was no replay of historical expired approvals.

The production readonly runtime reports the same run, profile, boundary,
candidate, approval, plan, rank, command and position. The v2 funnel now reports
`PAPER_POSITION_OPENED` instead of allowing later approval expiry to overwrite
the completed execution result. The PAPER position list reports the identical
command and position IDs, `LINKUSDT`, and `OPEN`.

An earlier natural `DOGEUSDT` v2 winner at boundary `1788404100000` also opened
successfully and later closed naturally by stop loss. That full lifecycle
exposed a journal-causality reconciliation defect: position events retained the
request causation instead of the execution fill causation. Forward migration
`0023_scalping_v2_journal_causality` repaired only v2 PAPER journal rows, and
the execution service now persists fill causation for all future v2 position
events. Post-migration accounting and PAPER reconciliation are `HEALTHY`.
The LINK position later closed naturally with positive realized PAPER PnL. A
fresh bounded PAPER-only canary is ARMED at generation 10 and is waiting for the
next eligible v2 approval with command/open-position budgets `0/1`; LIVE is
still disabled.

## Fixes shipped

- Scalping v2 is the only new 5m runtime identity. Scalping v1 remains available
  only for historical reads/reconstruction and is rejected by approval,
  selector and execution guards.
- All readiness consumers use the current authoritative readonly snapshot with
  generation, evaluation time and provenance. The consumer timeout is ten
  seconds and continuation cadence is five seconds.
- Forward migration `0022_scalping_v2_paper_simulation_policy` installs the
  active v2-only PAPER simulation policy. The legacy foundation policy path is
  retained for frozen non-v2 compatibility, so 15m semantics do not change.
- The lifecycle worker carries the command's simulation-policy identity through
  entry, exit and close processing.
- Forward migration `0023_scalping_v2_journal_causality` repairs existing v2
  position-event causality and the execution service preserves fill causation
  for future v2 OPEN/CLOSE events without rewriting historical v1 data.
- Scalping v2 decisions now use the computed final score as their contract score;
  a post-deploy 10-symbol boundary completed with zero module errors.
- Funnel lifecycle precedence is corrected: a persisted command/position result
  is authoritative over approval TTL observed later.

## Verification evidence

- Isolated PostgreSQL 16 E2E: `6 passed`. It covers multiple v2 candidates,
  canonical ranking, command creation, fill, OPEN position, v1 negative path,
  expiry, identity mismatch, readiness recovery, readonly reconstruction and
  frozen 15m regression.
- Focused authority, selector, UI, score-contract, profile, geometry,
  accounting and order-execution suite: `197 passed` after the final changes.
- Final funnel/strategy/authority regression: `37 passed, 6 skipped` (the six
  skips were the same E2E tests before the isolated URL was supplied); the
  isolated run was then executed explicitly and passed all six.
- Compileall and `git diff --check`: PASS.
- Production schema: single Alembic head
  `0023_scalping_v2_journal_causality`; active v2 simulation-policy rows: one.
- Production v1 5m runs/outcomes after the authoritative cutover boundary:
  zero/zero.
- Required reached winner fields checked in the readonly funnel: setup, entry,
  stop and target policy/provenance; geometry, cost and RR decisions; selector,
  command and position states. Generic `Недоступно`, `UNKNOWN`, or `N/A`: zero.
- Current readiness: READY, control ARMED generation 10 and waiting for an
  eligible approval, market-data/approval/
  WAL/PITR true, mutation ready, accounting/PAPER reconciliation healthy,
  denial reasons empty, runtime worker running, LIVE false.
- All four mutable Scalping/PAPER services run images labeled with source commit
  `6be591a6231f6250b99efeb5ee9f20e2998010fe`. The frozen 15m container was not
  rebuilt or restarted.

## Safety

Only PAPER persistence and isolated test-database mutations were performed.
LIVE remained disabled. No real Binance order endpoint was called. Production
credentials were neither printed nor changed. A temporary isolated-test role
credential was rotated after a failed local test invocation and was not reused;
it has no production authority.

## 2026-09-03 operational continuation: WAL/PITR readiness recovery

A fresh post-task reread found a new operational readiness flap after the
original acceptance: the canonical host WAL ACK owner state still named PID
`15516`, but the process was absent and its heartbeat was stale. PostgreSQL had
one recoverable export backlog item and nine pending archive-status entries.
The archive itself remained continuous: all 2,132 required segments were
available, the base-backup chain was contiguous, and there was no physical or
unrecoverable WAL gap.

The existing project-native single-owner daemon was restarted through
`production_wal_archive_remediation.py daemon`. Its stale-lock path removed the
lock only after proving the recorded PID dead. The recovered owner PID `1860`
drained the backlog through the checksum/ACK protocol and published a current
atomic state. No schema, business-data, PAPER lifecycle, Control, container, or
LIVE transition was used to force readiness.

Fresh post-recovery evidence:

```text
ACK_OWNER = RUNNING_IDENTITY_MATCHED_PID_1860
ACK_HEARTBEAT = HEALTHY
ACK_ERROR_CLASS = NONE
PENDING_ARCHIVE_STATUS_COUNT = 0
EXPORT_BACKLOG_COUNT = 0
ACTIVE_UNRESOLVED_FAILURE_COUNT = 0
ARCHIVE_ARTIFACT_COVERAGE = 2141
REQUIRED_WAL_SEGMENTS = 2141
MISSING_REQUIRED_SEGMENTS = 0
SOURCE_RECOVERABLE_MISSING_SEGMENTS = 0
BASE_BACKUP_CHAIN_CONTIGUOUS = YES
PHYSICAL_WAL_GAP = NO
PITR_CONTIGUOUS_WINDOW_SECONDS = 2030969
WAL_ARCHIVE_HEALTH = PASS
READONLY_WAL_READY = true
READONLY_PITR_READY = true
READONLY_CURRENT_MUTATION_READY = true
READONLY_MUTATION_DENIAL_REASONS = []
CONTROL = ARMED_GENERATION_10_WAITING_FOR_ELIGIBLE_APPROVAL
ALEMBIC_HEAD = 0023_scalping_v2_journal_causality
LIVE_STATE = DISABLED
BINANCE_ORDER_API_CALLS_BY_CONTINUATION = 0
SECRET_OUTPUT = 0
```

The historical WAL regression suite contained one assertion coupled to a
repository-wide diff from commit `ba8d19d...`. Later legitimate PAPER work made
that assertion fail even though the WAL remediator remained isolated. The test
now directly verifies that the remediator has no dependency on PAPER
foundation, market-data adapter, or foundation migrations. This changes no
runtime code or strategy semantics.

Validation after the correction:

```text
WAL_SECURITY_REGRESSION = 1451 passed, 1 platform skip
SCALPING_V2_BRIDGE_FUNNEL_EXECUTION_REGRESSION = 173 passed, 6 PostgreSQL opt-in skips
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
TRADE_15M_CONFIG_CHANGED = NO
TRADE_15M_BEHAVIOR_CHANGED = NO
NATURAL_V2_POSITION_OPEN = PASS_PRESERVED
```
