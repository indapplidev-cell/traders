# Readonly API parity runtime redeployment acceptance 02

```text
TASK_ID = TRADERS_MOBILE_READONLY_API_PARITY_RUNTIME_REDEPLOYMENT_ACCEPTANCE_02
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_MOBILE_READONLY_API_PARITY_RUNTIME_REDEPLOYMENT_ACCEPTANCE_02_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
```

The clean authoritative server tree at
`82fada2b642787c0dc79085855657a320347a01b` contains the accepted bounded
`SqlAlchemyReadAdapter.list_latest_analyses` implementation: one database
request composed from at most ten `UNION ALL` latest lookups, one
`session.execute`, and no full-history window or `ROW_NUMBER`. Source remained
25 GET and zero write routes. Focused verification passed with 14 Analysis
repository/semantic/bound tests, 113 server API tests, and 1,849 PAPER/reporting
and route tests with two environment-dependent skips.

Before deployment, Readonly image
`sha256:7aad14db4371e52339d58f7d44128e05e38378711d3d44cc42fca0084fce74a2`
was healthy and exposed 25 GET / 0 write, but `/api/v1/analysis` returned HTTP
500 in 30,047.728 ms and `/api/v1/markets` returned HTTP 500 in 30,309.112 ms.
PAPER orders, fills and journal remained HTTP 200.

Only the production Readonly target was built and recreated. The exact action
was the independent production compose equivalent of `build readonly-api`
followed by `up -d --no-deps --force-recreate readonly-api`. The resulting
image is
`sha256:83c42ba8f95ee0b12aeb7e33f75c3109d442d321e89e9fbf1cbc9875ece00e7d`,
labelled with source
`82fada2b642787c0dc79085855657a320347a01b@533802200b7dbb5072fa74d561015e64e5b7d028`.
Readonly container identity changed from `298e1c88fbbd` to `2b14f3c9d1a3` and
became healthy without an extra restart.

Postdeploy acceptance:

```text
READONLY_HEALTH = HTTP_200_HEALTHY
READONLY_ROUTES = 25_GET_0_WRITE
ANALYSIS = HTTP_200_10_ITEMS_BOUNDED
ANALYSIS_7_SAMPLES_MS = 618.596,905.864,499.974,256.643,254.882,240.825,270.522
ANALYSIS_MEDIAN_MAX_MS = 270.522_905.864
MARKETS = HTTP_200_10_ITEMS_BOUNDED
MARKETS_7_SAMPLES_MS = 692.651,649.395,398.522,402.442,401.992,501.404,403.387
MARKETS_MEDIAN_MAX_MS = 403.387_692.651
AGGREGATE_DETAIL_SPOTCHECK = 10_OF_10_IDENTITY_AND_CLOSED_UNTIL_MATCH
PAPER_ORDERS_FILLS_JOURNAL = HTTP_200_200_200_BOUNDED_EMPTY
GET_MATRIX = 25_ROUTES_23_2XX_2_EXPECTED_DETAIL404_0_UNEXPECTED4XX_0_UNEXPECTED5XX
DESKTOP_PROVIDER = PASS_10_MARKETS_NO_TIMEOUT
DESKTOP_TESTS = 19_PASSED_21_SUBTESTS
```

PostgreSQL, market-data, orchestrator and Control container identities were
unchanged and all restart deltas were zero. PostgreSQL remained healthy at
Alembic `0015_trading_universe_activation`; no DDL, DML, migration, index,
grant, role or timeout mutation was performed. Market data remained current at
60/60 and the orchestrator remained running with the Funnel route HTTP 200.
Control remained loopback-only, ARMED generation 6. Canary
`6f9858cd-f6b1-4c7f-810c-fccc1065bb9d` remained
`WAITING_FOR_ELIGIBLE_APPROVAL` with zero commands and positions. LIVE and
Binance order authority remained disabled.

No source, mobile, desktop, server-network or firewall change occurred. Port
18765 has no listener, portproxy or task firewall rule. No Control POST,
trading, canary or database mutation was made and no secret value was output.

```text
MOBILE_07_RETRY_02_AUTHORIZED = YES
MOBILE_08_AUTHORIZED = NO
NEXT_ACTION = TRADERS_MOBILE_07_CONTROLLED_MOBILE_NETWORK_ACCESS_ACCEPTANCE_01_RETRY_02
```
