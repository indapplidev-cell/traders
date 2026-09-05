# TRADERS_SCALPING_V2_CONTINUOUS_PAPER_BUDGET_POLICY_AUDIT_AND_FIX_01

Reconciliation time: 2026-09-05T01:39:42Z

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_PAPER_DAILY_LIMITS_DISABLED_STATISTICS_AND_SAFETY_CAPACITY_RETAINED
IMPLEMENTATION_COMMIT = 1c4c27208ddc78ad0ac3b3f4394917a4361ad7ef
DESKTOP_COMMIT = 69775d9129037d3f98173c829f2619cc1924be6d
SCALPING_V2_PROFILE_ID = trade-5m-v2
SCALPING_V2_AUTHORITATIVE = PASS
PAPER_AUTHORITY_MODE = CONTINUOUS
EFFECTIVE_CONTROL_STATE = CONTINUOUS_ARMED
RISK_PAUSE_REASON = NONE
LIVE_STATE_AFTER = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
ALEMBIC_HEAD = 0025_paper_budget_policy
TRADE_15M_CONFIG_CHANGED = NO
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS
```

## Root cause and policy decision

The old daily values were unrelated module constants in
`app/engine_paper/continuous_authority.py`:

- `10` was a count of unique continuous PAPER commands per UTC day.
- `50` was equity basis points accumulated as 10 bps per unique v2 command.
- `0.5` was USDT accumulated as the absolute value of every negative closed
  PAPER trade's net PnL.
- loss streak had no configured limit (`NULL` / `NOT_CONFIGURED`).

Those numbers were persisted by migration 0024 and copied into the singleton
continuous-control row, but they were not part of the versioned Scalping v2
runtime parameter set.  They were therefore arbitrary legacy control defaults,
not an authoritative Scalping v2 risk policy.  The old comparison itself was
arithmetically consistent, but the authority/source was wrong for the user's
virtual-money statistics phase.

The user explicitly superseded the source prompt's instruction to keep daily
budget enforcement: until a real Binance account and real money are connected,
daily command/risk/loss/loss-streak limits are disabled.  Usage accounting and
the deterministic UTC day reset remain active for statistics.  A separate
persisted `REAL_MONEY_LIMITED` enforcement mode remains available for a future
explicit real-account policy.  The one-new-command-per-cycle and one-open-
position execution-capacity invariants remain enforced independently.

## Complete parameter manifest

| Field | Old value | Unit | Formula / ledger | Old source | New PAPER limit | New policy source |
|---|---:|---|---|---|---|---|
| daily command | 10 | `trade_count` | one per unique `command_id` event | unversioned module constant | disabled / API `null` | `USER_AUTHORIZED_VIRTUAL_PAPER_STATISTICS_POLICY` |
| daily risk | 50 | `equity_basis_points` | sum canonical v2 risk-per-trade bps per unique command | unversioned module constant | disabled / API `null` | same |
| daily realized loss | 0.5 | `USDT` | `SUM(ABS(net_pnl))` for negative closed trades, unique by `position_id` | unversioned module constant | disabled / API `null` | same |
| loss streak | not configured | `closed_trade_count` | consecutive negative closed-trade net PnL; win resets to zero | no configured limit | disabled / API `null` | same |
| budget day | UTC date | date | current UTC calendar day | persisted control row | retained | policy v2 |
| reset | 00:00 UTC | timestamp | next UTC midnight; once per changed persisted day | reconcile transaction/event | retained | policy v2 |
| cooldown | not configured | N/A | no continuous budget cooldown implementation exists | N/A | not configured | explicit N/A |
| risk pause | legacy four budget reasons | enum | compare usage at/above enabled limit | continuous authority | disabled for PAPER daily budgets | enforcement mode |

```text
BUDGET_PARAMETER_MANIFEST = COMPLETE
BUDGET_POLICY_VERSION = scalping-v2-continuous-paper-statistics-v2
BUDGET_ENFORCEMENT_MODE = PAPER_STATISTICS_ONLY
DAILY_COMMAND_BUDGET_UNIT = trade_count
DAILY_RISK_BUDGET_UNIT = equity_basis_points
DAILY_LOSS_BUDGET_UNIT = USDT
DAILY_LOSS_FORMULA = SUM_ABSOLUTE_NEGATIVE_CLOSED_TRADE_NET_PNL_UNIQUE_POSITION
DAILY_RISK_FORMULA = SUM_CANONICAL_RISK_PER_TRADE_BPS_UNIQUE_COMMAND
UNIT_UNAVAILABLE_VALUES_AFTER = 0
SOURCE_UNAVAILABLE_VALUES_AFTER = 0
GENERIC_UNKNOWN_VALUES_AFTER = 0_FOR_CONFIGURED_BUDGET_FIELDS
MAGIC_UNEXPLAINED_BUDGET_VALUES = 0_ACTIVE_LIMITS
```

Net PnL is the canonical PAPER trade-report result after entry/exit fees and
simulated execution prices, so fees and modeled slippage reach the loss ledger
exactly once through net PnL.  Wins do not increase `realized_loss`; under this
gross-loss usage policy they also do not offset it.  Idempotent event IDs for
`POSITION_CLOSED` and `COMMAND_RECORDED` prevent replay/reconciliation double
counting.

## Canonical v2 risk consistency

The `1%` value visible in older funnel diagnostics is stop-distance geometry,
not account risk allocation.  The authoritative v2 runtime parameter is
`risk_per_trade_bps=10`, i.e. 0.1% of equity, sourced from
`SCALPING_V2_RUNTIME_PARAMETERS/risk_per_trade_bps`.  At the original 100 USDT
baseline the maximum planned single-trade risk is 0.1 USDT.  Consequently the
legacy 0.5 USDT loss value and 50 bps risk value were not lower than one
canonical single-trade risk; the defect was their unversioned authority and
their unwanted enforcement during the virtual-money statistics phase.

```text
RISK_PER_TRADE_VALUE = 10
RISK_PER_TRADE_UNIT = equity_basis_points
RISK_PER_TRADE_SOURCE = SCALPING_V2_RUNTIME_PARAMETERS/risk_per_trade_bps
MAX_SINGLE_TRADE_RISK_AT_100_USDT = 0.1_USDT
IS_DAILY_LOSS_BUDGET_LOWER_THAN_SINGLE_TRADE_RISK = NO
IS_DAILY_RISK_BUDGET_LOWER_THAN_SINGLE_TRADE_RISK = NO
SCALPING_V2_RISK_POLICY_INTERNAL_CONSISTENCY = PASS
```

## Migration, readonly, Desktop, and funnel

Forward-only migration `0025_paper_budget_policy` persists policy version,
source, enforcement mode, metric units, and next reset timestamp.  It preserves
all usage counters, clears only legacy daily-budget pause reasons, and restores
continuous authority automatically.  No expired approval is replayed.

The server now owns explicit value/limit/unit/source fields, formulas, policy
metadata, reset boundary, effective state, and pause reason.  Disabled limits
are `null`, never an invented large number.  Desktop renders `DISABLED` and the
server values without calculating units or formulas.  Funnel rows distinguish
`plan_state`, `selector_state`, `command_state`, `position_state`,
`execution_block_reason`, and `budget_state`.

The Desktop process was restarted on source commit `69775d9`.  Native-app
Computer Use returned an empty app inventory on this host, so a screenshot was
not technically available.  UI parity is instead corroborated by the exact
server contract, provider/model tests, source inspection, and the complete
Desktop suite.

## Tests

```text
SERVER_READONLY_FOCUSED = 1831 passed
CONTINUOUS_OPERATOR_FUNNEL_15M_FOCUSED = 77 passed
TRADE_15M_EXPLICIT = 4 passed
DESKTOP_FULL = 1489 passed, 2 skipped, 3029 subtests passed
POSTGRES16_NATURAL_E2E = 8 passed
POSTGRES16_LEGACY_0024_TO_0025_RECONCILIATION = PASS
COMPILEALL = PASS
DIFF_CHECK = PASS
BUDGET_ACCOUNTING_RESTART_SAFE = PASS
BUDGET_RESET_IDEMPOTENT = PASS
PAPER_BUDGET_UI_PARITY = PASS_BY_CONTRACT_AND_FULL_CLIENT_SUITE
FUNNEL_PLAN_VS_EXECUTION_REASON_PARITY = PASS
```

The PostgreSQL E2E uses an isolated loopback PostgreSQL 16 database and a
non-superuser `paper_test_*` principal.  It proves natural eligible headroom,
winner/command/position flow, restart-before-close, restart-after-close,
double-close idempotency, UTC reset, and 15m preservation.  A separate database
was upgraded to 0024, seeded with the exact legacy
`DAILY_LOSS_BUDGET_EXHAUSTED` row, upgraded to 0025, and verified as
`CONTINUOUS_ARMED` with counters preserved and the new policy persisted.

## Production deployment and natural validation

Migration 0025 was applied before service recreation.  Only 5m v2, readonly,
and operator-control were recreated from implementation commit `1c4c272`.
All have restart count zero; readonly and operator health checks are healthy.
The 15m container `1e05edea...` was not recreated and retains its
2026-09-01T07:05:16Z creation time and restart count zero.  Post-deploy ERROR,
CRITICAL, and Traceback matches are zero for all three changed services.

At reconciliation, production reports:

```text
CONTROL_STATE = CONTINUOUS_ARMED
EFFECTIVE_STATE = CONTINUOUS_ARMED
BUDGET_DAY = 2026-09-05
BUDGET_RESET_AT = 2026-09-06T00:00:00Z
COMMANDS_USED = 1
COMMAND_LIMIT = DISABLED
RISK_USED = 10_equity_basis_points
RISK_LIMIT = DISABLED
REALIZED_LOSS_USED = 0.330723550_USDT
REALIZED_LOSS_LIMIT = DISABLED
RISK_PAUSE = FALSE
CURRENT_MUTATION_READY = TRUE
LIVE_ALLOWED = FALSE
PAPER_EQUITY = 98.488621928_USDT
```

Four new natural `trade-5m-v2` commands and positions occurred after the
deployment boundary without manual re-arm: DOGEUSDT, LINKUSDT, ADAUSDT, and
ADAUSDT.  All four positions closed naturally.  The midnight transition reset
the statistical day exactly once; the fourth trade is correctly the first
command of 2026-09-05.  Production SQL found zero post-deploy plan outcomes
with any daily-budget terminal reason.

```text
POSTGRES_E2E = PASS
DEPLOYED = YES
NATURAL_PRODUCTION_VALIDATION = PASS_4_COMMANDS_4_POSITIONS_0_BUDGET_BLOCKS
FALSE_DAILY_LOSS_BUDGET_EXHAUSTED = 0_AFTER
TRADE_15M_BEHAVIOR_CHANGED = NO
LIVE_STATE_AFTER = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
```

Real-money Binance trading remains disabled.  Enabling
`REAL_MONEY_LIMITED` requires a separate explicit task that defines and tests
real-account limits before any LIVE rollout.
