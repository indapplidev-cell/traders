# TRADERS Readonly funnel connection recovery 01 — final evidence

```text
TASK = TRADERS_READONLY_FUNNEL_CONNECTION_RECOVERY_01
FINAL_VERDICT = PASS
INCIDENT_REPORTED = DESKTOP_MARKET_AND_TRADING_FUNNEL_SHOWED_SERVER_ERROR
ROOT_CAUSE = FUNNEL_LOAD_ONLY_OMITTED_RESULT_TRADE_PROFILE_ID_AND_PRIMARY_TIMEFRAME
FAILURE = SQLALCHEMY_DETACHED_INSTANCE_ERROR_AFTER_READ_SESSION_CLOSE
IMPLEMENTATION_COMMIT = 4ebd0a6e9c314e684334e1110559948fff11f965
DEPLOYED_SOURCE = 4ebd0a6e9c314e684334e1110559948fff11f965
RECONCILED_AT_UTC = 2026-08-31T09:05:57Z
```

## Diagnosis

The desktop transport was connected, but both profile-aware requests returned
HTTP 500:

- `GET /api/v1/trading/funnel?trade_profile=trade-5m-v1`;
- `GET /api/v1/trading/funnel?trade_profile=trade-15m-v1`.

The server traceback proved that `TradingFunnelReadRepository` cached ORM rows
after closing its read session, while its bounded `load_only` selection omitted
`OnlinePipelineResultRow.trade_profile_id` and
`OnlinePipelineResultRow.primary_timeframe`. The production-approval classifier
then attempted a deferred load from the detached result row.

## Remediation

The existing bounded query now eagerly loads the two classifier identity
columns. No route, schema, write privilege, mutation path, threshold, PAPER
control or LIVE behavior changed. A SQLite regression exercises the real
session-close boundary and proves that cached rows remain classifiable.

## Verification

```text
FOCUSED_FUNNEL_TESTS = 21_PASSED
READONLY_AND_APPROVAL_REGRESSION = 1589_PASSED_7_SKIPPED
COMPILEALL = PASS
REAL_CLIENT_PROVIDER = PASS_MARKETS10_5M_ITEMS10_15M_ITEMS10
POSTDEPLOY_5M_REPEAT = 10_OF_10_HTTP_200_MIN113MS_MAX4851MS
POSTDEPLOY_15M_REPEAT = 10_OF_10_HTTP_200_MIN33MS_MAX118MS
POSTDEPLOY_HTTP_500 = 0
POSTDEPLOY_DETACHED_INSTANCE_ERROR = 0
```

The legacy Tk smoke helper did not start because its test-only
`MemorySettingsStore` lacks the `path` attribute now required by the current
client. This helper incompatibility is outside the server incident and did not
invalidate the direct current-client verification: the actual
`UrllibJsonTransport` plus `ServerProvider` parsed Market, 5m funnel and 15m
funnel responses successfully.

## Fresh runtime state

```text
READONLY_CONTAINER = e86f39d256ca6008fd076e17711c923c84b89b77135ceab6b843fa69291634ad
READONLY_IMAGE = sha256:d87e380e60e1e2822011228c6d7a97d2ab438c1328453c0f009747de03f2e309
READONLY_SOURCE = 4ebd0a6e9c314e684334e1110559948fff11f965
READONLY_STARTED_AT_UTC = 2026-08-31T05:02:33.514275457Z
READONLY_HEALTH = HEALTHY
READONLY_RESTART_COUNT = 0
READONLY_API_HEALTH = STATUS_OK_OPERATIONAL_TRUE_READY_TRUE
ALEMBIC = 0018_promote_5m_production_search
OPERATOR_CONTROL = UNCHANGED_HEALTHY_RESTART0_SOURCE16F75C98D1191BE6A49132FC9AD5003BA8157810
ORCHESTRATORS = UNCHANGED_RUNNING_15M_AND_5M
LIVE = UNCHANGED_DISABLED
```

The Readonly API alone was rebuilt and recreated. PostgreSQL, both
orchestrators, Operator Control and the PAPER/LIVE safety state were not
restarted or mutated by this task.

## Git transport snapshot

```text
LOCAL_HEAD_AT_EVIDENCE = 4ebd0a6e9c314e684334e1110559948fff11f965
REMOTE_HEAD_AT_EVIDENCE = 69f697f267e02a7ab9b805203ef24095f1f409ce
LOCAL_AHEAD_AT_EVIDENCE = 1
LOCAL_BEHIND_AT_EVIDENCE = 0
PUSH_STATE_AT_EVIDENCE = NOT_PUSHED
WORKTREE_STATUS_AT_EVIDENCE = CLEAN
```

Production deployment here is the proven host-local immutable Docker artifact;
it must not be interpreted as a remote Git push.
