# Readonly API parity runtime deployment

```text
TASK_ID = TRADERS_MOBILE_READONLY_API_PARITY_RUNTIME_DEPLOYMENT_01
TASK_STATUS = BLOCKED
FINAL_VERDICT = BLOCKED_TRADERS_MOBILE_READONLY_API_PARITY_RUNTIME_DEPLOYMENT_01
BLOCKER_CODE = READONLY_RUNTIME_TARGET_ROUTE_5XX_AFTER_DEPLOYMENT
SECONDARY_BLOCKER = READONLY_RUNTIME_AGGREGATE_ANALYSIS_PRODUCTION_SELECT_STATEMENT_TIMEOUT
STOP_CONDITION = SOURCE_REMEDIATION_REQUIRES_SEPARATE_TASK
```

The current `feature/engine-platform` source contains all four additive GET-only
routes and the focused isolated contract regression passed with 1845 tests.
Before deployment the healthy localhost runtime exposed 21 GET and zero write
routes; all four targets returned HTTP 404.

The production compose topology proved that Readonly is a one-service project
separate from Control. The task built image
`sha256:7aad14db4371e52339d58f7d44128e05e38378711d3d44cc42fca0084fce74a2`
from source commit `2166055d2ba1bfbb96b5785bea7f86872dfd0c62`, then ran only
`docker compose ... up -d --no-deps --force-recreate readonly-api`. The
Readonly container changed from `c5b2661bb38c` to `298e1c88fbbd`; PostgreSQL,
market-data, orchestrator and Control container identities and restart counts
did not change.

Post-deploy Readonly health passed and the runtime exposes 25 GET and zero
write routes. The three new PAPER list routes return HTTP 200 with bounded empty
lists. Aggregate Analysis is registered but returns HTTP 500 after the
production read-only SELECT is canceled by the configured statement timeout at
approximately 30 seconds. The existing aggregate Markets route encounters the
same timeout. The bounded 25-route matrix therefore produced 21 HTTP 2xx, two
expected detail HTTP 404 responses for empty PAPER collections, zero unexpected
4xx, and two unexpected 5xx. A desktop memory-settings smoke failed on Market
with `ProviderTimeoutError`, confirming the runtime regression without changing
desktop source or settings.

Readonly remained healthy, so the deployed additive runtime was preserved as
required. No rollback, whole-stack restart, source rewrite, migration, grant,
database write, Control POST, canary action, trading mutation or Binance order
call was performed.

## Proven invariants

```text
READONLY_ENDPOINT = 127.0.0.1:8765
READONLY_HEALTH_BEFORE_AFTER = PASS_PASS
READONLY_ROUTES_BEFORE_AFTER = 21_GET_0_WRITE_TO_25_GET_0_WRITE
ANALYSIS_HTTP_BEFORE_AFTER = 404_500
PAPER_ORDERS_HTTP_BEFORE_AFTER = 404_200
PAPER_FILLS_HTTP_BEFORE_AFTER = 404_200
PAPER_JOURNAL_HTTP_BEFORE_AFTER = 404_200
CONTROL = 127.0.0.1:8766_LOOPBACK_ONLY_ARMED_GENERATION_6_UNCHANGED
CANARY = 6f9858cd-f6b1-4c7f-810c-fccc1065bb9d_WAITING_FOR_ELIGIBLE_APPROVAL_UNCHANGED
LIVE_ALLOWED = FALSE_UNCHANGED
POSTGRESQL = HEALTHY_ID_AND_RESTART_COUNT_UNCHANGED
MARKET_DATA = RUNNING_ID_AND_RESTART_COUNT_UNCHANGED_ADAPTER_READY
ORCHESTRATOR = RUNNING_ID_AND_RESTART_COUNT_UNCHANGED_FUNNEL_HTTP200
WAL_PITR = TRUE_TRUE_UNCHANGED
MOBILE_LISTENER_18765 = ABSENT
MOBILE_FIREWALL_RULE = ABSENT
MOBILE_ANDROID_URL_CHANGE = NONE
PRODUCTION_DATABASE_MUTATIONS_BY_TASK = 0
PRODUCTION_CONTROL_MUTATIONS_BY_TASK = 0
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
EXISTING_CANARY_CONTROL_MUTATIONS_BY_TASK = 0
```

MOBILE-07 retry 02 is not ready and MOBILE-08 remains unauthorized. The next
action is a separately authorized source-remediation task for the production
aggregate Analysis/Markets SELECT statement timeout, followed by a narrow
Readonly redeployment and acceptance rerun.
