# TRADERS 5m SHADOW full-funnel controlled deployment acceptance 01

```text
TASK = TRADERS_5M_SHADOW_FULL_FUNNEL_CONTROLLED_DEPLOYMENT_ACCEPTANCE_01
RESULT = PASS_DEPLOYED_WITH_NATURAL_NO_ACTION_OBSERVATION
FINAL_VERDICT = PASS_5M_FULL_SHADOW_ROUTE_DEPLOYED_DESKTOP_HTTP_ACCEPTED
PROJECT_STATE_COMMIT = SELF
PROJECT_STATE_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/TRADERS_5M_SHADOW_FULL_FUNNEL_CONTROLLED_DEPLOYMENT_ACCEPTANCE_01_FINAL.md
RECONCILED_AT_UTC = 2026-08-20T19:37:32Z
SOURCE_FULL_FUNNEL_COMMIT = 3302a142d1d7117b24897c872a7eea4a5e70319c
LIVE = DISABLED
```

## Authorization and scope

The user explicitly authorized controlled production deployment and natural
SHADOW observation. The deployment replaced only:

- `online-orchestrator-5m` so new 5m results contain the complete shadow plan
  and post-risk approval projection;
- `readonly-api` so the desktop Trading Funnel consumes the new projection.

PostgreSQL, market-data, 15m orchestrator and Operator Control retained their
container/image identities and restart count zero.

## Deployment postcondition remediation

The first new Readonly image was healthy and exposed the authoritative 27 GET
and zero write routes, but the existing deployment adapter still required the
historical 18-route catalog. It correctly stopped before publishing acceptance.
The postcondition was updated to the exact current 27-route inventory while
retaining the explicit nine legacy-route and thirteen PAPER-route sets. The
remediated adapter then rebuilt/recreated Readonly, verified exact source
identity, health, routes, safe HTTP probes and published the marker.

```text
READONLY_SOURCE_IDENTITY = sha256:2d55f0589cbee34db59af898027aa7b1a1d2db3030c23184b51b2998d1ea1482
READONLY_RUNTIME_IDENTITY_MATCH = PASS
READONLY_GET_ROUTES = 27
READONLY_WRITE_ROUTES = 0
READONLY_READY_MARKER = TRUE
```

## Runtime identities

```text
5M_CONTAINER_BEFORE = 729b2303fc0ace9e0f8ffab14d7924cf0426cc537c840c74c7a2ffbcac4eb526
5M_IMAGE_BEFORE = sha256:4b007e28037722618853f53eeedd78958854861bccc55bd2a56f6ff76208818d
5M_CONTAINER_AFTER = a9e609d45b2f84e7ba09a742663519dc42a4558b2c27f9643fd802cb8b595404
5M_IMAGE_AFTER = sha256:c1ec9f08e82c5f85e1805c42f32c740fec4128af237eb3e072842e3587e480ab
READONLY_CONTAINER_BEFORE = 7215d62f9afd74ddae23c04e90e95be061ec1d96fe9e5a90c31760e324627145
READONLY_IMAGE_BEFORE = sha256:06f42a84f71750f26db0b5493561fddce65b110708491aed1e95247ec40475c8
READONLY_CONTAINER_AFTER = 3134309a0c3d403fcd82e5261fb9163c4690d2922b690ce2494fdaeebcf5532a
READONLY_IMAGE_AFTER = sha256:79df542d7b934160a342720de3e3792a0474124b7211b08569864a959716456b
RESTART_COUNTS_AFTER = ALL_ZERO
```

## Natural 5m observation

Five consecutive natural closed 5m boundaries from `1787253300000` through
`1787254500000` were observed after deployment.

```text
BOUNDARIES = 5
RUNS = 50
RESULTS = 50
EXACT_SYMBOLS_PER_BOUNDARY = 10_OF_10
SHADOW_PLAN_PAYLOADS = 50_OF_50
SHADOW_FINAL_APPROVAL_GENERATION_PAYLOADS = 50_OF_50
STRUCTURAL_SETUPS = 0
RISK_PREAPPROVALS = 0
SHADOW_ELIGIBLE = 0
SELECTOR_WINNERS = 0
```

This is a truthful natural `NO_ACTION` observation. The runtime executed and
persisted the new shadow planning/materialization boundary for every result,
but current market inputs did not pass structural setup. A winner was therefore
not manufactured. Existing RR, commission, spread, slippage and liquidity
gates remain unchanged.

The deployed 5m health report showed owner `ACQUIRED`, `overall_status=OK`,
`last_error=null`, exact cursor alignment and all execution/trading/order/
position safety counters at zero.

## Desktop and API acceptance

The production endpoint returned profile `trade-5m-v1`, decision timeframe
`5m`, mode `SHADOW_SEARCH`, a complete 10/10 current cycle, the full ten-stage
projection and the new `execution_eligible` field. Command and position
creation flags remained false.

The real desktop `ServerProvider` parsed this production response successfully.
The accepted desktop environment completed `1450 passed`, `2 skipped` and
`3029` subtests; the Python process later returned nonzero from a known Tcl
cross-thread teardown after pytest had reported all tests passed. The isolated
GUI file independently passed `9/9`. Windows capture located the single
`Клиент Traders` window, but Tk graphics capture remained unavailable with
`0x80004002`; no blind UI clicks were used.

## Validation and invariants

```text
PREDEPLOY_AFFECTED_REGRESSION = 258_PASSED_11_SKIPPED
POSTCONDITION_FOCUSED = 150_PASSED_6_SKIPPED
EXPANDED_SERVER_DEPLOYMENT_REGRESSION = 490_PASSED_11_SKIPPED
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS_LINE_ENDING_WARNINGS_ONLY
PRODUCTION_ALEMBIC = 0017_parallel_trade_profiles
15M_LATEST_BOUNDARY = 1787254200000_EXACT10
WAL_READY = TRUE
PITR_READY = TRUE
CONTROL = ARMED_GENERATION6_UNCHANGED
PAPER_COMMANDS_ORDERS_FILLS_POSITIONS = 0_0_0_0
5M_PAPER_COMMAND_CREATION_ENABLED = FALSE
5M_POSITION_OPENING_ENABLED = FALSE
LIVE_ALLOWED = FALSE
SCHEMA_MUTATIONS = 0
CONTROL_MUTATIONS = 0
```

## Decision

The 5m mode is now production-deployed and fully connected from Analysis to
the SHADOW winner projection. “Fully connected” means every qualified natural
candidate can traverse all stages; it does not mean every five-minute cycle
must produce a winner. The current bounded production sample stopped honestly
at structural setup.

```text
NEXT_ACTION = CONTINUE_PASSIVE_NATURAL_5M_SHADOW_OBSERVATION_UNTIL_FIRST_ELIGIBLE_WINNER_WITHOUT_THRESHOLD_TUNING
```
