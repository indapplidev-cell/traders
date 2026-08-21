# Trading Funnel monotonic stage semantics remediation 01

```text
TASK = TRADERS_FUNNEL_MONOTONIC_STAGE_SEMANTICS_REMEDIATION_01
RESULT = PASS_SOURCE_DEPLOYMENT_AND_DESKTOP_HTTP_ACCEPTANCE
FINAL_VERDICT = PASS_MONOTONIC_HISTORICAL_STAGES_WITH_SEPARATE_CURRENT_ELIGIBILITY
PROJECT_STATE_COMMIT = SELF
PROJECT_STATE_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/TRADERS_FUNNEL_MONOTONIC_STAGE_SEMANTICS_REMEDIATION_01_FINAL.md
RECONCILED_AT_UTC = 2026-08-21T04:24:16Z
SERVER_IMPLEMENTATION_COMMIT = 4ebbf40e29fe417646edec2501ae18521a167f21
CLIENT_IMPLEMENTATION_COMMIT = 84746ff143c5c14a8414d8b58e7e85964e626340
LIVE = DISABLED
```

## Root cause and corrected contract

The projection mixed two time semantics in one ordered funnel. It recomputed
`VALIDITY_APPROVED` against request-time `now_ms`, while `FINAL_APPROVAL`
represented the immutable historical creation event. An expired approval could
therefore render `QUANTITY=1, VALIDITY=0, FINAL=1`.

The corrected contract is:

- `VALIDITY_APPROVED` records that validity was successfully checked when the
  approval chain was created;
- `FINAL_APPROVAL` records immutable approval creation;
- `ELIGIBLE` remains the current, expiry-aware acceptance gate;
- expired natural and SHADOW candidates cannot enter ranking or win, including
  when a stale external candidate mapping is supplied.

The public RU labels are now `Срок проверен`, `Одобрение создано`, and
`Допущен сейчас`. EN labels are `Validity check passed`, `Approval created`,
and `Currently eligible`. API stage keys and projection schema are unchanged.

## Exact production reproduction and acceptance

The production record was `BNBUSDT`, boundary `1787282100000`, with an immutable
`FINAL_APPROVAL_CREATED` and all three approval components valid through
`1787282999999`. At request time it was expired but remained inside the rolling
four-hour window.

```text
BEFORE_ROLLING_4H = PAPER_PLAN1_QUANTITY1_VALIDITY0_FINAL1
AFTER_ROLLING_4H = PAPER_PLAN1_QUANTITY1_VALIDITY1_FINAL1
AFTER_CURRENT_ELIGIBLE = 0
AFTER_CURRENT_WINNER = NONE
CATALOG_VERSION = i18n-c0e92a2ae32c6425
RU_LABELS = Срок проверен | Одобрение создано | Допущен сейчас
REAL_DESKTOP_SERVER_PROVIDER = PROFILE15M_VALIDITY1_FINAL1_WINNER_NONE
```

## Deployment identity and invariance

Only Readonly API was rebuilt and force-recreated through the authoritative
narrow deployment adapter. Its exact postcondition passed.

```text
READONLY_CONTAINER_BEFORE = 3134309a0c3d403fcd82e5261fb9163c4690d2922b690ce2494fdaeebcf5532a
READONLY_IMAGE_BEFORE = sha256:79df542d7b934160a342720de3e3792a0474124b7211b08569864a959716456b
READONLY_CONTAINER_AFTER = 7e01de5abd282413b095999024b04363aef31d6a703aef5a00037f5bf6bb07d0
READONLY_IMAGE_AFTER = sha256:270a6d136409e2d423234241454237a9f9486504eab848ad5b048f2df09d4f21
READONLY_SOURCE_IDENTITY = sha256:c7984d56a47b24c0cbce717acebbecc370da1f2bcdaf883a136bfbd78d9ef978
READONLY_HEALTH = HEALTHY
READONLY_ROUTES = 27_GET_0_WRITE
OTHER_SERVICE_IDENTITIES = UNCHANGED
OTHER_SERVICE_RESTART_COUNTS = ZERO
SCHEMA = 0017_parallel_trade_profiles
PAPER_COMMAND_ORDER_FILL_POSITION = 0_0_0_0
WAL_PITR = TRUE_TRUE
CONTROL = ARMED_GENERATION6_UNCHANGED
LIVE_ALLOWED = FALSE
CURRENT_MUTATION_READY = FALSE
```

## Validation

```text
SERVER_FOCUSED = 27_PASSED
SERVER_EXPANDED = 229_PASSED_11_SKIPPED
SERVER_COMPILEALL = PASS
CLIENT_FOCUSED_NONGUI = 30_PASSED_13_SUBTESTS
CLIENT_FULL = 1449_PASSED_2_SKIPPED_3029_SUBTESTS_1_TCL_ENVIRONMENT_FAILURE
CLIENT_GUI_LIMITATION = SYSTEM_TCL_INIT_UNAVAILABLE
DESKTOP_RESTART = ONE_NEW_INSTANCE_ACTIVE
WINDOWS_VISUAL_CAPTURE = UNAVAILABLE_0X80004002_NO_BLIND_CLICKS
```

The Tcl and Windows capture limitations do not affect the production HTTP
contract or parser acceptance. The generated client bootstrap and deployed
server catalog have the same catalog version and exact labels.

