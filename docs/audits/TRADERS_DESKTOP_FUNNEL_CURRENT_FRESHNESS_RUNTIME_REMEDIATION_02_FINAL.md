# Desktop funnel CURRENT freshness runtime remediation 02

Captured at `2026-08-20T17:48:10Z`.

## Decision

```text
TASK = TRADERS_DESKTOP_FUNNEL_CURRENT_FRESHNESS_RUNTIME_REMEDIATION_02
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS
BLOCKER_CODE = NONE
ROOT_CAUSE = PRODUCTION_READONLY_CATALOG_AND_DESKTOP_LKG_REMAINED_AT_PRE_FIX_IDENTITY
SOURCE_FIX_WAS_NOT_DEPLOYED = YES
```

The source/client implementation was correct, but the running desktop started
with cached catalog `i18n-c987e45a65572881`. The production Readonly API also
advertised that same old identity and did not expose `market.data.CURRENT`, so
startup synchronization correctly retained the old LKG and replaced the newer
generated-bootstrap view. This was a deployment-state mismatch, not a second
translation lookup defect.

## Narrow deployment

```text
SERVER_SOURCE_IMPLEMENTATION_COMMIT = 8958482a8533d9141dd0b731fc1f5f75eecbd747
CLIENT_SOURCE_IMPLEMENTATION_COMMIT = 2a4aec04bb3555948c95a175f8262ec645676de9
READONLY_IMAGE_ID = sha256:03b698440c14a871ba3b230e364add2db36ee8cd0005f0b2beb160e348f02e28
READONLY_IMAGE_SOURCE_IDENTITY = 8958482a8533d9141dd0b731fc1f5f75eecbd747
READONLY_CONTAINER_BEFORE = 268357eb12ac685e2ea022ddc214e284b36c100db0a9c5d0e637e9e9ee55a3eb
READONLY_CONTAINER_AFTER = bc331c9a96a6010693240256858038a15459d3a3d6336581ca06b34bf0edc884
READONLY_HEALTH_AFTER = HEALTHY
READONLY_RESTART_COUNT_AFTER = 0
DEPLOYMENT_SCOPE = READONLY_API_ONLY_NO_DEPS_FORCE_RECREATE
WHOLE_STACK_DOWN = NO
```

The image was rebuilt from the accepted source identity and only
`readonly-api` was force-recreated. PostgreSQL, market-data, 15m orchestrator,
5m orchestrator and Operator Control retained their exact container IDs and
restart count zero.

## Runtime and desktop acceptance

```text
RUNTIME_CATALOG_BEFORE = i18n-c987e45a65572881
RUNTIME_CATALOG_AFTER = i18n-2467d88a8f9049d6
RUNTIME_CONTENT_HASH_AFTER = 2467d88a8f9049d69aaf4036c6485263e936050087e31950eef129fab2fbc8ec
RUNTIME_RU_KEY_COUNT = 801
RUNTIME_EN_KEY_COUNT = 801
RUNTIME_RU_CURRENT = ДАННЫЕ_АКТУАЛЬНЫ
RUNTIME_EN_CURRENT = DATA_CURRENT
FUNNEL_15M = CURRENT_EXACT10
FUNNEL_5M = CURRENT_EXACT10
DESKTOP_LKG_AFTER = i18n-2467d88a8f9049d6
DESKTOP_PROCESS_AFTER = PYTHONW_PID15980_NEW_PROCESS
DESKTOP_15M_VISIBLE = 15m_PIPE_ДАННЫЕ_АКТУАЛЬНЫ_PASS
DESKTOP_5M_VISIBLE = 5m_PIPE_ДАННЫЕ_АКТУАЛЬНЫ_PASS
DESKTOP_UNKNOWN_FALLBACK_FOR_CURRENT = ZERO
PROVIDER = PRODUCTION_READONLY_HTTP_CONNECTED_READONLY
```

The desktop was restarted after deployment. Its cache atomically advanced to
the new server identity. Direct visual acceptance on the running application
proved both profile selections and preserved the separate 5m shadow/PAPER-off
notice.

## Safety and limitations

```text
POSTGRES_CONTAINER_ID_UNCHANGED = YES
MARKET_DATA_CONTAINER_ID_UNCHANGED = YES
ORCHESTRATOR_15M_CONTAINER_ID_UNCHANGED = YES
ORCHESTRATOR_5M_CONTAINER_ID_UNCHANGED = YES
CONTROL_CONTAINER_ID_UNCHANGED = YES
DATABASE_SCHEMA_OR_DATA_MUTATIONS = ZERO
CONTROL_OR_TRADING_MUTATIONS = ZERO
LIVE = DISABLED_UNCHANGED
SECRET_VALUE_OUTPUT = ZERO
ACL_MANUAL_CORROBORATION = PROTECTED_CURRENT_USER_SYSTEM_ADMINISTRATORS_ONLY
LEGACY_ACL_INSPECTOR = SAFE_INSPECTION_FAILED_TOOLING_DEFECT_NO_SECRET_OUTPUT
PRODUCTION_PUSH = NOT_PERFORMED
```

The legacy binding verifier failed inside its Windows ACL subprocess even
though a direct metadata-only ACL inspection proved the required restricted
principal set and the existing healthy service already consumed the binding.
No protected value was printed or copied. The unrelated legacy GUI smoke
script also remains incompatible with the current `SettingsStore.path`
contract; live GUI acceptance was performed directly instead.

