# PAPER candidate execution and client latency audit 01

## Verdict

```text
FINAL_VERDICT = PASS_DIAGNOSIS_CLIENT_FIX_DEPLOYED_CONTINUOUS_PAPER_BLOCKED_BY_FIRST_CANARY_AUTHORITY
TASK = TRADERS_PAPER_CANDIDATE_EXECUTION_AND_CLIENT_LATENCY_AUDIT_01
SERVER_I18N_IMPLEMENTATION_COMMIT = 043968e14f3585cbb1530c0cac7f67059e1c908e
CLIENT_IMPLEMENTATION_COMMIT = b3e80a47a3887edd002496b5dc15eaf2271bd4af
CLIENT_AUDIT_COMMIT = 3e3112669aba77e8f5f2206ddbc2f5e174f16c65
RECONCILED_AT_UTC = 2026-09-04T04:40:27Z
```

## Why 23 plans did not open trades

The rolling Funnel counters shown by the client are stage-passage counts. The
`Final approval` and `PAPER plan` values do not mean selector winners. At the
fresh audit boundary `1788496500000`, the moving four-hour window contained 21
final approvals and 21 plans (the screenshot previously contained 23), but all
21 persisted plan outcomes had:

```text
SELECTED_WINNERS = 0
ELIGIBLE_NOW = 0
SELECTOR_STATE = LEGACY_NOT_OBSERVED
COMMAND_STATUS = NOT_REACHED
POSITION_STATUS = NOT_REACHED
TERMINAL_REASON = EXPIRED_BEFORE_EXECUTION
```

The count changed from 23 to 21 because the four-hour window moved, not because
records were deleted. These are natural production-pipeline plans, not unit-test
records. Tests use isolated fixtures/databases and the previous deployment
acceptance forced no signal, command, order, fill, or position.

The production executor is still explicitly a bounded first-canary mechanism.
`ProductionPaperFirstCanaryLifecycleWorker` is hard-bound to one command and one
position. After the selected position closes, `_finalize()` transitions Control
from `ARMED` to `DISABLED`. The most recent natural DOGEUSDT canary was selected
at 00:20 UTC, entered SHORT at 00:21 UTC, closed at 00:34 UTC, and automatically
left Control disabled at generation 11. Plans created after that point could not
reach selector/command execution.

The three production PAPER trades are natural first-canary runs:

```text
2026-09-03T02:56Z..03:13Z DOGEUSDT LONG  net_pnl=-0.59975546
2026-09-03T03:26Z..04:54Z LINKUSDT LONG  net_pnl=+0.347627558
2026-09-04T00:21Z..00:34Z DOGEUSDT SHORT net_pnl=-0.36467214
```

The latest DOGE trade occurred naturally after the v2 research-quota correction
while the already authorized generation-10 first canary was armed. It was not
created by a test or by a forced signal.

## Client latency and presentation remediation

The server response was not the freeze source: seven live Funnel provider calls
had a 0.318 second median and 0.431 second maximum. The Tk client repainted every
page on every global state notification, and a PAPER refresh emits multiple
notifications. It also repeatedly logged the missing translation for each
expired historical row.

Client commit `b3e80a4` limits repainting to the active page, skips unchanged
immutable Funnel snapshots, labels the historical selector field correctly,
and consumes the regenerated server-owned bilingual catalog. Server commit
`043968e` supplies an operator-readable `EXPIRED_BEFORE_EXECUTION` reason.

```text
FULL_FUNNEL_RENDER_BEFORE_MEDIAN = 203.667 ms
FULL_FUNNEL_RENDER_AFTER_MEDIAN = 84.998 ms
UNCHANGED_FUNNEL_NOTIFICATION_AFTER_MEDIAN = 0.623 ms
CLIENT_FULL = 1486 passed, 2 skipped, 3029 subtests
CLIENT_FOCUSED = 41 passed
SERVER_CRITICAL = 64 passed
SERVER_I18N = 11 passed
PROFILE_AWARE_GUI = PASS_RU_EN_F5_AUTOREFRESH_15M
```

## Deployment and safety

```text
READONLY_IMAGE_BEFORE = sha256:205e405fb0966cc9605369931c26a7cf18d2ad2d38e5cbefac40e37512fb1928
READONLY_IMAGE_AFTER = sha256:ed16b941003cd88b0afce7d4ccf726da1caad5d3abe5c096de8ebdb870e2c6f5
READONLY_SOURCE = 043968e14f3585cbb1530c0cac7f67059e1c908e
READONLY_HEALTH = healthy_restart0
CATALOG_VERSION = i18n-c4cfcc8ce67cb96f
DESKTOP = source_tree_pid18488
PAPER_CONTROL = DISABLED_GENERATION11_UNCHANGED_BY_TASK
PAPER_CONTROL_ACTIONS = 0
BINANCE_ORDER_API_CALLS = 0
LIVE = DISABLED
```

Continuous PAPER execution is not implemented by the existing first-canary
authority. Re-enabling the same control would only authorize one more bounded
canary; it would not repair the architectural mismatch. The next task is a
separate continuous-PAPER authority design with durable budgets, restart-safe
state, reconciliation, and unchanged LIVE prohibition.
