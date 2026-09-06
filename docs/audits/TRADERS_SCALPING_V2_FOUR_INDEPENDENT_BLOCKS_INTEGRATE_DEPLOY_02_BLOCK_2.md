# Block 2 — Real Binance account commission authority

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS
BLOCK_2_IMPLEMENTED = YES
BLOCK_2_INTEGRATED = YES
BLOCK_2_DEPLOYED = YES
BLOCK_2_RUNTIME_ACTIVE = YES
BLOCK_2_REAL_ACCOUNT_DATA = TRUE
BLOCK_2_STUB_ACTIVE = NO
CREDENTIAL_SOURCE_PARSE = PASS
BINANCE_ACCOUNT_COMMISSION_AUTH = PASS
ACTIVE_SYMBOLS_QUERIED = 10
ACTIVE_SYMBOLS_READY = 10
COMMISSION_SOURCE = BINANCE_ACCOUNT_COMMISSION
RUNTIME_EFFECTIVE_COMMISSION_PROVENANCE = VISIBLE
SECRET_OUTPUT = 0
SECRET_COMMITTED = NO
SECRET_IN_IMAGE = NO
REAL_BINANCE_ORDER_CALLS = 0
LIVE = DISABLED
BLOCK_2_COMMIT = b3efe3859086b440f1cf729557075d5027c4b9a6
BLOCK_2_PUSH = SYNCHRONIZED_0_AHEAD_0_BEHIND
WORKER_IMAGE = sha256:27c9de66c9274d2c6181dff1ec55035b549b0dc722293d568384a6f1db499df6
READONLY_IMAGE = sha256:b85f53b8b35b4d58761b823eab51e5559069c12d49ed037b2cd08d08d1ae0609
OPERATOR_IMAGE = sha256:e613dcdcbab89645fb0aa1395188d549e064e12a5ecfe5974b40cad41101ed99
DEPLOYED_SOURCE = b3efe3859086b440f1cf729557075d5027c4b9a6
TRADE_PARAMETER_CONFIG_HASH = 1c7f19fa12c9fbd0d2a720571f19f27e5542f8eb921123b9e91ee968c3e195ec
ALEMBIC = 0028_scalping_profitability_grants
WORKER_HEALTH = OK
READONLY_HEALTH = HEALTHY
OPERATOR_HEALTH = HEALTHY
LEGACY_15M = EXITED_NOT_RECREATED
FOCUSED_TESTS = 15_PASSED
FUNNEL_AND_PROVIDER_TESTS = 38_PASSED
COMPILE = PASS
COMPOSE_VALIDATION = PASS
RECONCILED_AT_UTC = 2026-09-06T20:10:09Z
```

The implementation follows the official Binance Spot signed USER_DATA account
commission contract at `GET /api/v3/account/commission`. The protected runtime
binding reads the user credential file as a Docker secret, synchronizes against
the public Binance server clock, and writes only a non-secret atomic snapshot
outside the repository and image build context.

The active `trade-5m-v2` symbol universe is taken from runtime configuration.
Every one of its ten symbols has standard, special, tax, discount, liquidity
role, effective entry/exit fee, round-trip fee, fetch time, age, and provider
version provenance. Startup, reconnect, universe-change, hourly refresh, retry,
and TTL behavior are fail-closed. A valid cache is accepted only inside TTL;
otherwise the real cost path reports `FEE_SOURCE_NOT_READY`. Zero-fee,
configured-fee, and legacy authorized-stub fallbacks cannot become authoritative.

Production proof traced the provider through protected snapshot, freshness
policy, cost snapshot, Scalping v2 effective total cost, and dynamic Required Net
RR/EV admission. Readonly reports `READY`, `real_account_data=true`, 10/10 ready,
`stub_active=false`, and visible effective provenance without exposing credentials.

The first pre-acceptance startup exposed two safe integration defects: the local
credential file used label-plus-value lines without `=`/`:`, and the host clock
required Binance server-time synchronization. Both attempts remained fail-closed.
Subsequent diagnostics were restricted to signed read-only BTCUSDT commission
reads. The final production validation performed one successful bounded refresh
over exactly the ten active symbols. No order, account mutation, or withdrawal
endpoint was called. Paper command/order/position counts remained unchanged at
54/106/53 across deployment.

Official contract references:

- https://developers.binance.com/en/docs/products/spot/rest-api
- https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/ws-api/account

