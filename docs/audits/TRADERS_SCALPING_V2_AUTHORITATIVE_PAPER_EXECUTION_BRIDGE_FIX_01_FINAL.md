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

ROOT_CAUSE = STALE_READINESS_HTTP_TIMEOUT_AND_DISPATCH_CADENCE; MISSING_PRODUCTION_V2_SIMULATION_POLICY; V2_SCORE_CONTRACT_MISMATCH; OPENED_LIFECYCLE_OVERWRITTEN_BY_LATER_APPROVAL_EXPIRY_IN_FUNNEL
ROOT_CAUSE_FIXED = YES

READINESS_STATE = READY_CONTROL_ARMED_GENERATION6_MUTATION_READY_LIVE_FALSE
READINESS_REASONS = NONE

NATURAL_WINNER_SYMBOL = DOGEUSDT
NATURAL_WINNER_RANK = 1
NATURAL_WINNER_PROFILE_VERSION = trade-5m-v2
NATURAL_WINNER_CANDIDATE_ID = paper:production-approval-candidate:v1:51004bd0ddb5beb4a94df7a24fbba02113034e55ac10ca791b0dd11bc76b6f12
NATURAL_WINNER_APPROVAL_ID = paper:risk-approval:v1:e6fb8c95a718cb46b30fe4f292e6533b57acca6d0d941ae4d64cb72733eb2f3e
NATURAL_WINNER_PLAN_ID = paper:DOGEUSDT:5m:1788404100000:risk:DOGEUSDT:5m:1788404100000:strategy:v2:0c44e84678bdb07e08380450dffd1efd7bcb11ed82cc70fa52043e724700bdda:4c77670eb6a3f5c0:e9ede056794bd107

COMMAND_ID = paper:ingestion-command:v1:6dad532db0c37c2cfbf84bb7adc71ade1c2c4e396c81cf7323a766b4ab4d9fc8
COMMAND_STATUS = CREATED_PERSISTED_QUEUE_STATE_PENDING_ENTRY_ORDER_FILLED

POSITION_ID = paper:first-canary:position:4a4ed46f2cc0552377d16479f77c633d6d0a47a3bca5a1d9079cc2e41f36e1d0
POSITION_STATUS = OPEN

EXPIRY_RACE_FIXED = PASS
READINESS_REGRESSION_FIXED = PASS
GENERIC_UNAVAILABLE_VALUES_AFTER = 0_FOR_REQUIRED_REACHED_WINNER_FIELDS
FUNNEL_PAPER_PARITY = PASS
POSTGRES_E2E = PASS_6
NATURAL_V2_POSITION_OPEN = PASS

DEPLOYED_COMMIT = b760cd7a319d4814854dc62aa02edbae35ec5f5d
ALEMBIC_HEAD = 0022_scalping_v2_paper_simulation_policy
DESKTOP_HEAD = 78f124aa9dce0131b759939ef02962edb8d2bb16
MOBILE_HEAD = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db

LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0

REMAINING_BLOCKERS = NONE
NEXT_ACTION = OBSERVE_NORMAL_PAPER_CANARY_LIFECYCLE_AND_CLOSE_WITHOUT_ENABLING_LIVE
```

## Natural production acceptance

The first post-policy-fix natural winner was the `DOGEUSDT` Scalping v2 cycle
at boundary `1788404100000` (2026-09-03 02:55:00 UTC), pipeline run
`orchestrator:f58e95f5f1ab43edadc422561f0582a8`. Its natural plan and immutable final
approval were selected at rank 1. The executor created exactly one PAPER
command on the first attempt, the next eligible closed 1m candle produced a
filled entry order at 2026-09-03 02:56:00 UTC, and the durable position became
`OPEN` before approval expiry at `1788404399999`.

The command uses `simulation:scalping-v2:foundation:v1`; the fill preserves the
same policy. The command joins to the v2 pipeline run, and the entry order/fill
join to the OPEN position. There was no replay of historical expired approvals.

The production readonly runtime reports the same run, profile, boundary,
candidate, approval, plan, rank, command and position. The v2 funnel now reports
`PAPER_POSITION_OPENED` instead of allowing later approval expiry to overwrite
the completed execution result. The PAPER position list reports the identical
command and position IDs, `DOGEUSDT`, `LONG`, and `OPEN`.

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
- Scalping v2 decisions now use the computed final score as their contract score;
  a post-deploy 10-symbol boundary completed with zero module errors.
- Funnel lifecycle precedence is corrected: a persisted command/position result
  is authoritative over approval TTL observed later.

## Verification evidence

- Isolated PostgreSQL 16 E2E: `6 passed`. It covers multiple v2 candidates,
  canonical ranking, command creation, fill, OPEN position, v1 negative path,
  expiry, identity mismatch, readiness recovery, readonly reconstruction and
  frozen 15m regression.
- Focused authority, selector, UI, score-contract, profile and geometry suite:
  `104 passed` after the final changes.
- Final funnel/strategy/authority regression: `37 passed, 6 skipped` (the six
  skips were the same E2E tests before the isolated URL was supplied); the
  isolated run was then executed explicitly and passed all six.
- Compileall and `git diff --check`: PASS.
- Production schema: single Alembic head
  `0022_scalping_v2_paper_simulation_policy`; active v2 simulation-policy rows:
  one.
- Production v1 5m runs/outcomes after the authoritative cutover boundary:
  zero/zero.
- Required reached winner fields checked in the readonly funnel: setup, entry,
  stop and target policy/provenance; geometry, cost and RR decisions; selector,
  command and position states. Generic `Недоступно`, `UNKNOWN`, or `N/A`: zero.
- Current readiness: READY, control ARMED generation 6, market-data/approval/
  WAL/PITR true, mutation ready, denial reasons empty, LIVE false.
- All four mutable Scalping/PAPER services run images labeled with source commit
  `b760cd7a319d4814854dc62aa02edbae35ec5f5d`. The frozen 15m container was not
  rebuilt or restarted.

## Safety

Only PAPER persistence and isolated test-database mutations were performed.
LIVE remained disabled. No real Binance order endpoint was called. Production
credentials were neither printed nor changed. A temporary isolated-test role
credential was rotated after a failed local test invocation and was not reused;
it has no production authority.
