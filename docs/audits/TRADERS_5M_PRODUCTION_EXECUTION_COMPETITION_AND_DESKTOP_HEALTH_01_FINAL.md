# TRADERS 5m production execution competition and desktop health — final

```text
TASK = TRADERS_5M_PRODUCTION_EXECUTION_COMPETITION_AND_DESKTOP_HEALTH_01
FINAL_VERDICT = PASS_CONTROLLED_DEPLOYMENT_AND_NATURAL_5M_PRODUCTION_CYCLE
LIVE = DISABLED
PAPER_ACCOUNT = 100_USDT
IMPLEMENTATION_COMMIT_1 = 538d59255c9c478bb43f825a87987acb8d61fcc2
IMPLEMENTATION_COMMIT_2 = 9fe3a4f1dba41c054cd5003e589ac72ba21394f5
CLIENT_IMPLEMENTATION_COMMIT = 6aeeab660013cf100303d7ff1a907a46d15c39db
CLIENT_STATUS_COMMIT = c247de361b6fd2f0a6728f866aa90f46b66e6d37
OBSERVED_AT_UTC = 2026-08-21T06:38:00Z
```

## Result

The 5m profile is no longer a shadow-only projection. It now runs as
`PRODUCTION_SEARCH`, can materialize executable PAPER approvals, and competes
with 15m approvals under the existing deterministic
`eligible-approval-ranking-v1` selector. The selector reads both timeframes at
one database clock boundary and fails closed if either source read is unhealthy.

The first deployment attempt exposed a production-only schema defect. Schema
0017 constrained `trade-5m-v1` rows to `SHADOW_SEARCH`. `reserve()` also caught
every `IntegrityError` as if it were a duplicate window, hiding that constraint
violation. Schema 0018 now preserves historical 5m shadow provenance while
allowing new 5m production rows, and only the named profile-window uniqueness
violation is classified as a duplicate.

The desktop `Unknown` connection state had a separate cause: the global health
request was issued only on Dashboard refresh. Every non-Dashboard page refresh
now schedules the same bounded health request; success updates the global
banner and failure clears it to `Unknown`.

## Production evidence

```text
ALEMBIC = 0018_promote_5m_production_search
5M_CONTAINER = 6b87b0cf9985
5M_IMAGE = sha256:b8f289f7bd22f17f2dbc56f1339420112bc558dbbafeabab508b233c162ad1f0
5M_RESTART_COUNT = 0
5M_NATURAL_PRODUCTION_ROWS = 60
5M_LATEST_BOUNDARY_MS = 1787294100000
5M_HISTORICAL_SHADOW_ROWS_PRESERVED = 1663
5M_CURRENT_CYCLE = 10_OF_10_COMPLETE_CURRENT
5M_COMMAND_CREATION = TRUE
5M_POSITION_OPENING = TRUE
15M_CURRENT_CYCLE = 10_OF_10_COMPLETE_CURRENT
15M_COMMAND_CREATION = TRUE
15M_POSITION_OPENING = TRUE
SELECTOR_POLICY = eligible-approval-ranking-v1
READONLY_CONTAINER = 55c68f3d445c
READONLY_IMAGE = sha256:537145e33cf6228476b6a659e0a3b815d6d8b95861d56d20e08eec55b4e47ffb
READONLY_SOURCE_IDENTITY = sha256:84b001a573660ba5baed4c67e5dc08d21bc3972bc2fc9a3e783bbf659ca0ad6a
READONLY_HEALTH = HEALTHY_RESTART_0
CONTROL_CONTAINER = db6015863510
CONTROL_IMAGE = sha256:a4664ff5c34844c59f89224369cda859b72d30c27663b7b2ff1a128626590f39
CONTROL_SOURCE_IDENTITY = 9fe3a4f1dba41c054cd5003e589ac72ba21394f5
CONTROL = ARMED_GENERATION_6_HEALTHY_AUDIT_PASS
CONTROL_SAFE_PROBE = 3_GET_5_POST_VALID_READ_AND_REJECTED_UNAUTHENTICATED_MUTATIONS
LIVE_ALLOWED = FALSE
CANARY_ID = 6f9858cd-f6b1-4c7f-810c-fccc1065bb9d
CANARY_STATE = NO_ELIGIBLE_APPROVAL
CANARY_COMMANDS = 0
CANARY_POSITIONS = 0
PAPER_COMMANDS_ORDERS_FILLS_POSITIONS_JOURNAL = 0_0_0_0_0
ACCOUNT_BALANCE_FEES_NET_PNL = 100_0_0
```

The latest natural 5m cycle reached analysis for all ten symbols. None reached
a PAPER plan in the observed boundary, so the lack of a command is currently a
market/strategy outcome, not a 5m authorization blocker. The armed first-canary
budget remains unused and bounded to one command and one open position.

## Validation

```text
SERVER_AFFECTED_MATRIX = 1730_PASSED_11_SKIPPED
SERVER_SCHEMA_AND_DUAL_PROFILE_MATRIX = 1855_PASSED_12_SKIPPED
SERVER_SELECTOR_AND_5M_FOCUSED = 44_PASSED
SERVER_COMPILE = PASS
SERVER_DIFF_CHECK = PASS
FULL_SERVER_SUITE = PREEXISTING_UNRELATED_0014_EXPECTATION_FAILURE_AFTER_2631_PASSED_16_SKIPPED
CLIENT_FOCUSED = 42_PASSED_13_SUBTESTS
CLIENT_FULL = 1451_PASSED_2_SKIPPED_3029_SUBTESTS
CLIENT_GUI_ENVIRONMENT = SYSTEM_TCL_INIT_FAILURE_ONLY
CLIENT_COMPILE = PASS
CLIENT_REAL_HTTP = HEALTH_OK_AND_5M_PRODUCTION_10_OF_10_PASS
```

The known full-suite server failure is an unrelated stale contract assertion
that expects schema 0014 while the pre-task code already declared 0015. It was
not altered as part of this deployment.

## Next gate

Observe the first naturally eligible approval from either 15m or 5m. The shared
selector must choose one winner, after which the already armed bounded canary
must prove command, simulated order, fill, position, exit, fees, and final net
PnL. Continuous PAPER execution is not accepted until that canary completes.
