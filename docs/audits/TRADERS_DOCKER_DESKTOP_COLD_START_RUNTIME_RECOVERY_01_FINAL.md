# Docker Desktop cold-start runtime recovery 01

## Final verdict

```text
TASK = TRADERS_DOCKER_DESKTOP_COLD_START_RUNTIME_RECOVERY_01
FINAL_VERDICT = PASS
INCIDENT = DOCKER_DESKTOP_STOPPED_SERVER_UNREACHABLE_CLIENT_STALE_CONNECTION
PRIMARY_ROOT_CAUSE = COM_DOCKER_SERVICE_STOPPED_LINUX_ENGINE_PIPE_ABSENT
SECONDARY_ROOT_CAUSE = PRE_0026_5M_IMAGE_REJECTED_PRODUCTION_SCHEMA_0026_ON_COLD_START
SOURCE_DEFECT = ALREADY_FIXED_IN_COMMIT_cbf13a10a57a2d4cfa5c6500d9729902bfae0382
SOURCE_CHANGE_BY_TASK = NONE
RUNTIME_REMEDIATION = START_DOCKER_DESKTOP_REBUILD_AND_RECREATE_5M_ONLY_RESTART_ACK_OWNER_RESTART_DESKTOP_CLIENT
FIVE_MIN_IMAGE_BEFORE = sha256:24c208acc4698fb9737472bbfafce7074976b8ba357f9088dcfcf3ec4a02d10a
FIVE_MIN_SOURCE_BEFORE = 1c4c27208ddc78ad0ac3b3f4394917a4361ad7ef
FIVE_MIN_FAILURE_BEFORE = online_runtime_requires_schema_0020_through_0025
FIVE_MIN_IMAGE_AFTER = sha256:02b834e2b73b34a37968684bc8ca5288995a16520205992dfc0980f844055f9e
FIVE_MIN_SOURCE_AFTER = cbf13a10a57a2d4cfa5c6500d9729902bfae0382
FIVE_MIN_RUNTIME_AFTER = RUNNING_RESTART0_OWNER_ACQUIRED_LAST_BOUNDARY_1788649500000_OVERALL_OK
FIFTEEN_MIN_CONTAINER_RECREATED = NO
FIFTEEN_MIN_IMAGE = sha256:5632f5c5a6c1c31552d9c1f75271d05f15b2e4440986e4835a11997892376934
READONLY_IMAGE = sha256:511472fc30845c325565ca20fead806f6e58eaabe8233fa30e671683eaa7b408
OPERATOR_IMAGE = sha256:8411db7d88ecb88d857f1552c6df0b9b78e1b04cbbe0f33c0947fab08cb655a3
POSTGRES = RUNNING_HEALTHY_RESTART0_PERSISTENT_VOLUME_RETAINED
ALEMBIC = 0026_scalping_1m_entry_refinement
READONLY = HTTP200_STATUS_READY_SCHEMA_READY_MARKET_READY_APPROVAL_READY
PAPER_CONTROL = CONTINUOUS_ARMED_GENERATION12_HEALTHY
WAL_PITR = TRUE_TRUE_LINEAGE_VALID_PHYSICAL_GAP_FALSE
ACK_OWNER = RUNNING_PID14932_HEARTBEAT_HEALTHY_IDENTITY_MATCH_BACKLOG0_PENDING0
ACK_OWNER_AUTOSTART = CURRENT_USER_LOGON_INSTALLED
CLIENT_BEFORE = PID14344_SERVER_UNAVAILABLE
CLIENT_AFTER = PID9424_RESPONDING_PRODUCTION_READONLY_HTTP_CONNECTION_OK_API_V1
FUNNEL_HTTP = trade-5m-v2_HTTP200_AND_trade-15m-v1_HTTP200
GUI_FUNNEL_RU_EN = PASS
GUI_PROFILE_AWARE = PASS_EXACT10_F5_AUTOREFRESH_LEGACY15M
FOCUSED_REGRESSION = 49_PASSED_5_SKIPPED
POSITIONS = 41_TOTAL_0_OPEN_41_CLOSED
TRADES = 41
LIVE = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
```

## Diagnosis and recovery

The Docker client initially had no Linux Engine pipe, the Docker Desktop
service was stopped, ports 8765 and 8766 had no listeners, and both Readonly
health requests were refused. Starting the existing Docker Desktop installation
restored the engine and the persisted Compose projects without replacing the
PostgreSQL volume.

The cold start then exposed a deployment skew hidden while the prior process
remained alive: the active 5m image was built from `1c4c272...` and rejected
Alembic revision 0026. The repository had already extended the startup gate to
0026 in `cbf13a10...`; rebuilding that single service from the proven source
removed the restart loop. No source or strategy parameter was changed by this
incident task, and the 15m container was not recreated.

The host WAL ACK owner was absent after Docker stopped. One canonical owner was
started through the existing safe remediation entrypoint, its identity and
heartbeat passed, and current-user logon autostart was installed idempotently.
Readonly subsequently projected WAL and PITR ready with valid contiguous
lineage and no physical gap.

## Acceptance

The production API returned HTTP 200 for health, readiness, the 5m Funnel and
the 15m Funnel. The rebuilt 5m owner acquired its PostgreSQL advisory lock and
completed the natural 23:05 UTC boundary for all ten symbols with `last_error`
null. The restarted source-tree desktop rendered `Соединение: В норме — API
v1`, current market rows, and a fresh update timestamp. Dedicated RU and EN
Funnel acceptance and profile-aware Market/Analysis/Scenarios acceptance,
including F5 and auto-refresh, passed.

The warning for an untranslated new reason code used the existing generic
localized fallback and did not block data loading; it is not the incident root
cause. PAPER remained continuous and healthy, no position was open at final
acceptance, LIVE remained disabled, and no real exchange order was sent.
