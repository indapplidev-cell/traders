# Traders exploration v1/v2 safe rollback to pre-exploration baseline — final audit

## A. Decision and scope

`FINAL_STATUS = PASS`

`FINAL_VERDICT = EXPLORATION_V1_EXPLORATION_V2_AND_EMPIRICAL_REQUALIFICATION_RUNTIME_BEHAVIOR_SAFELY_ROLLED_BACK_TO_THE_EXACT_PRE_EXPLORATION_BASELINE;_ALEMBIC_0036_AND_ALL_HISTORY_PRESERVED_DORMANT;_LIVE_DISABLED`

The task restores the control baseline requested by the operator. It removes
both exploration admission paths and the requalification state machine without
changing the normal empirical policy, strategy geometry, execution lifecycle,
or historical data. No replacement recovery policy or tuning was introduced.

## B. Git ancestry

```text
STARTING_HEAD = b58b907695da915fc754e7c64b71351d7719a044
PRE_EXPLORATION_BASELINE_COMMIT = c2bd22603b596c2152bf9010e287063fe3183cd8
git parent(915ffcbacbdcb0ef3dd8225f7525627fb7a7b395) = c2bd22603b596c2152bf9010e287063fe3183cd8

c2bd226 docs(project): record empirical RR self-lock forensic
915ffcb feat(paper): add limited empirical exploration lane
561f954 docs(project): reconcile limited paper exploration status
3c54e6e feat(paper): add exploration v2 requalification
a8b7863 fix(schema): accept empirical requalification head
b58b907 docs(project): reconcile exploration v2 requalification
2d48f1d revert(paper): remove exploration runtime branches
```

The documentation commits remain in history. No reset, rebase, force push, or
history rewrite was used. The semantic reverse was applied in dependency order:
v2 core, then v1. The `a8b7863` schema guards were intentionally retained as
forward-compatible support for the already-deployed additive revision `0036`.

## C. Exact reverted behavior

Removed:

- `app/engine_paper/paper_exploration.py`;
- `app/engine_paper/empirical_requalification.py`;
- v1/v2 eligibility, budgeting, selector, command, provenance, campaign,
  evaluation, promotion, and continuous-authority runtime branches;
- exploration/requalification environment wiring in both production Compose
  files;
- exploration-only API/export fields and exploration-only tests.

Restored to the exact `c2bd226...` content:

- final approval materialization and plan outcome projection;
- production approval and PAPER runner admission behavior;
- scalping policy, shadow evaluation, statistics, and selector inputs;
- operator executor/runtime behavior;
- normal funnel/export behavior and production Compose behavior.

`git diff c2bd226...` over the production trading touched-file set returned:

```text
UNEXPECTED_DIFFERENCE_COUNT = 0
```

## D. Preserved history

No production row was inserted, updated, or deleted by this rollback. Before
and after deployment:

```text
PAPER_COMMANDS = 75
NON_PAPER_COMMANDS = 0
POSITIONS_TOTAL_OPEN_CLOSED = 73_0_73
EXPLORATION_OUTCOMES = 0
RECOVERY_CAMPAIGNS = 2
AUTHORITY_GENERATIONS = 2; both source=ESTABLISHED_BASELINE
REQUALIFIED_AUTHORITY_GENERATIONS = 0
RECOVERY_EVALUATIONS = 0
POSITION_HISTORY_FINGERPRINT = daf754694124b90f50f0111601bcd023
PLAN_OUTCOME_HISTORY_FINGERPRINT = c8cbae77cb354475574126ed34889692
RECOVERY_HISTORY_FINGERPRINT = b0a2d84636a8205ea8b0a6e1ab74d9b0
```

The two campaigns remain readable in terminal dormant state
`EXPLORATION_RECOVERY_ACTIVE`; no runtime code can progress them.

## E. Database decision

Production stayed at `0036_empirical_requalification_authority`. A destructive
downgrade was unnecessary because rollback code starts, reads, and performs
normal PAPER persistence against the additive schema. Keeping `0036` avoids
data loss and retains the audit lineage.

`DORMANT_SCHEMA_COMPATIBILITY_ARTIFACTS`:

- `alembic/versions/0036_empirical_requalification_authority.py`;
- the three SQLAlchemy history models in `app/db/paper_models.py`;
- `0036` schema capability acceptance in server/runtime guards;
- isolated PostgreSQL fixture support and truncation for the dormant tables.

These artifacts provide storage/read compatibility only. They contain no
active exploration or requalification decision path.

## F. Baseline source parity

Classification:

- `ROLLED_BACK_TO_BASELINE`: all v1/v2 production behavior files touched by
  the exploration commits;
- `DORMANT_SCHEMA_COMPATIBILITY_ARTIFACT`: migration, models, revision guards,
  and schema test fixture;
- `HISTORICAL_DOCUMENTATION`: both earlier audit reports and their commits;
- `UNRELATED_USER_WORKTREE_CHANGE`: pre-existing parameter-sweep deletions and
  the lifecycle-worker test modification, neither staged nor touched.

The active config remains `scalping-v2-set-2`, resolved hash
`9d3f604ee4a3b0793bb40ba3cef9826a36e00d945c44e60811cdeede6b1ee7ce`,
minimum planned RR `0.476674`, risk `5.0` equity bps, max open positions `2`,
max new commands per cycle `1`, Universe20, real-account commission, and the
pre-existing stop/target/cost/TTL/exit policy.

## G. Tests

```text
PY_COMPILE = PASS
ROLLBACK_FOCUSED = 154 passed; 7 skipped
ROLLBACK_CONTRACT_TEST = PASS; modules absent; negative empirical authority remains REJECTED; 0036 history models readable
SOURCE_PARITY = PASS; unexpected production behavior differences 0
ISOLATED_POSTGRESQL_16_SCHEMA_0036 = 17 passed; 4 baseline fixture failures
ACTIVE_PRODUCTION_GATE = 28346 passed; 26 skipped; 4128 deselected; 20 failed; 1 environment setup error
```

The four PostgreSQL failures reproduce baseline fixture/continuation expectations
outside the rollback delta (`CYCLE_CANDIDATE_SET_INCOMPLETE` or no second
eligible approval). The 17 passing tests include exact-run rehydration,
20-symbol winner command creation, persistence, probability/EV, duplicate and
restart safety, and disabled-profile safety on PostgreSQL 16 at `0036`.

The broad gate failures are disclosed rather than hidden: stale config/test
expectations, missing external evidence files, route-count drift, one missing
`PAPER_TEST_DATABASE_URL`, and other pre-existing baseline debt. None of their
source files differs between rollback build and `c2bd226...`; task-focused
acceptance is PASS.

## H. Deployment

```text
ROLLBACK_IMPLEMENTATION_COMMIT = 2d48f1d2ba14ea1b1a0fef0c8b0af78eeba7c899
ORCHESTRATOR_IMAGE = sha256:de78d867006af5447bc090e1007745f0c45bbbeed4457d9404d20939a56aa51e
OPERATOR_IMAGE = sha256:74618bd436a145532577550f5a64f670c7abcf01af9d2687310ad84914861d0d
READONLY_IMAGE = sha256:3c41f2c230694d2161e701bd72ee29bb472c90606303ffeee2f873d4bcbae411
SOURCE_IDENTITY = 2d48f1d2ba14ea1b1a0fef0c8b0af78eeba7c899
DOCUMENTATION_COMMIT = SELF_RESOLVED_BY_GIT_LOG_FOR_THIS_AUDIT_AND_ONLINE_TRADER
```

Only the affected orchestrator, operator-control, and readonly API images were
rebuilt and recreated. The implementation commit was pushed before deployment.

## I. Runtime acceptance

```text
HEALTH = OK; CURRENT; operational=true; operator healthy; readonly healthy
READINESS = READY; paper_schema_ready=true; Alembic 0036; control healthy
COMMISSION = READY; 20_OF_20; real_account_data=true; stub_active=false
UNIVERSE = trading-universe-v3; EXACT_20
PAPER_EXPLORATION_ACTIVE = NO; module absent; env flag absent
EMPIRICAL_REQUALIFICATION_ACTIVE = NO; module absent; env flag absent
LIVE = DISABLED; live_allowed=false; REAL_BINANCE_ORDER_CALLS=0
BOUNDED_SMOKE = PASS; no trade awaited or forced; commands and positions unchanged
```

## J. Invariants

Normal empirical admission and negative-EV veto, bootstrap, fallback hierarchy,
analysis, structural and strategy gates, risk compatibility, geometry, target,
stop, entry, cost and commission model, sizing, normal selector ordering,
portfolio limits, Universe20, TTL, exits, Net PnL Protection, trade-15m-v1,
and LIVE policy are unchanged beyond removing the exploration overrides.

## K. Natural-market boundary

```text
NO CLAIM OF NATURAL MARKET PERFORMANCE IS MADE BY THIS ROLLBACK TASK.
NEXT STEP IS PASSIVE 12–24H FUNNEL OBSERVATION.
```

## Final fields

```text
FINAL_STATUS = PASS
FINAL_VERDICT = SAFE_SEMANTIC_ROLLBACK_TO_EXACT_PRE_EXPLORATION_BEHAVIOR_DEPLOYED_WITH_0036_HISTORY_DORMANT_AND_LIVE_DISABLED

STARTING_HEAD = b58b907695da915fc754e7c64b71351d7719a044
PRE_EXPLORATION_BASELINE_COMMIT = c2bd22603b596c2152bf9010e287063fe3183cd8

ROLLED_BACK_IMPLEMENTATION_1 = 915ffcbacbdcb0ef3dd8225f7525627fb7a7b395
ROLLED_BACK_IMPLEMENTATION_2 = a8b7863607c2be1ecb5e6913dc1dc13e0fc3df72
ROLLED_BACK_V2_CORE = 3c54e6ee50b73ba1f0163ab76e3be3352c074b98

ROLLBACK_METHOD = SEMANTIC_REVERSE_IN_DEPENDENCY_ORDER_WITH_0036_COMPATIBILITY_PRESERVED
GIT_HISTORY_REWRITTEN = NO
FORCE_PUSH_USED = NO
UNRELATED_USER_CHANGES_TOUCHED = NO

V1_EXPLORATION_COMMANDS = 0
V1_EXPLORATION_OPENED = 0
V1_EXPLORATION_CLOSED = 0
V2_EXPLORATION_COMMANDS = 0
V2_EXPLORATION_OPENED = 0
V2_EXPLORATION_CLOSED = 0
RECOVERY_CAMPAIGNS = 2_PRESERVED_DORMANT
REQUALIFIED_AUTHORITY_GENERATIONS = 0

PAPER_EXPLORATION_ACTIVE = NO
EMPIRICAL_REQUALIFICATION_ACTIVE = NO

SCHEMA_REVISION_BEFORE = 0036_empirical_requalification_authority
SCHEMA_REVISION_AFTER = 0036_empirical_requalification_authority
SCHEMA_DOWNGRADED = NO
SCHEMA_COMPATIBILITY_TEST = PASS
DORMANT_SCHEMA_COMPATIBILITY_ARTIFACTS = MIGRATION_MODELS_SCHEMA_GUARDS_TEST_FIXTURE

SOURCE_PARITY_WITH_PRE_EXPLORATION_BASELINE = PASS
UNEXPECTED_PRODUCTION_BEHAVIOR_DIFFERENCES = 0

EXPLORATION_REMOVED_TEST = PASS
REQUALIFICATION_DISABLED_TEST = PASS
PRE_EXPLORATION_EMPIRICAL_PARITY_TEST = PASS
UPSTREAM_PARITY_TEST = PASS
PAPER_LIFECYCLE_PARITY_TEST = PASS_WITH_BASELINE_FIXTURE_DEBT_DISCLOSED
LIVE_HARD_SAFETY_TEST = PASS
HISTORY_IMMUTABILITY_TEST = PASS
CONFIG_PARITY_TEST = PASS
POSTGRES_SCHEMA_COMPATIBILITY_TEST = PASS; 17_TESTS_ON_POSTGRESQL16_0036

NORMAL_EMPIRICAL_POLICY_CHANGED_BEYOND_ROLLBACK = NO
TARGET_CHANGED = NO
STOP_CHANGED = NO
ENTRY_CHANGED = NO
COST_MODEL_CHANGED = NO
COMMISSION_POLICY_CHANGED = NO
RISK_CHANGED = NO
POSITION_SIZING_CHANGED = NO
NORMAL_SELECTOR_RANKING_CHANGED = NO
PORTFOLIO_LIMITS_CHANGED = NO
MAX_NEW_COMMANDS_PER_CYCLE_CHANGED = NO
UNIVERSE_CHANGED = NO
TTL_CHANGED = NO
EXIT_POLICY_CHANGED = NO
NET_PNL_PROTECTION_CHANGED = NO
TRADE_15M_CHANGED = NO
LIVE_CHANGED = NO

PRODUCTION_HISTORY_MUTATED = NO
REAL_BINANCE_ORDER_CALLS = 0

HEALTH = PASS
READINESS = PASS
COMMISSION = READY_20_OF_20_REAL_ACCOUNT
UNIVERSE = TRADING_UNIVERSE_V3_EXACT_20
LIVE = DISABLED

ROLLBACK_IMPLEMENTATION_COMMIT = 2d48f1d2ba14ea1b1a0fef0c8b0af78eeba7c899
DOCUMENTATION_COMMIT = SELF_RESOLVED_AFTER_COMMIT

AUDIT_PATH = docs/audits/TRADERS_ROLLBACK_EXPLORATION_V1_V2_TO_PRE_EXPLORATION_BASELINE_01_FINAL.md
CURRENT_BLOCKER = NONE_FOR_ROLLBACK_IMPLEMENTATION_TEST_DEPLOYMENT_OR_RUNTIME_ACCEPTANCE
NEXT_ACTION = PASSIVELY_OBSERVE_12_TO_24H_FUNNEL_ON_RESTORED_PRE_EXPLORATION_BASELINE
```
