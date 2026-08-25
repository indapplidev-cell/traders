# Final decision — arbitrary-range Funnel export timeout remediation

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_DESKTOP_FUNNEL_ARBITRARY_RANGE_EXPORT_TIMEOUT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
SERVER_SOURCE_COMMIT = 4d32db3c9c3f4b2b2de225468615e2903159a26a
DESKTOP_SOURCE_COMMIT = 9983d8f039e5bb3bdd0db1d252dd9837fb4fa20c
MOBILE_COMMIT = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
READONLY_CONTAINER = 7c9c376af2650eaa3332ebe237a739cd3dbe0ac6b9a8d1e08b2f8bd2732202be
READONLY_IMAGE = sha256:4426ad3c4dd8cddbcfeec5eeca3fa6e99e42cf8645226a28fb0ac94fab721947
READONLY_SOURCE = 4d32db3c9c3f4b2b2de225468615e2903159a26a
ALEMBIC_VERSION = 0018_promote_5m_production_search
READONLY_GET_WRITE = 28_0
OBSERVER_PID = 23308_UNCHANGED
OBSERVATION_AFTER = 132_OF144_BOUNDARIES_1320_OF1440_EVALUATIONS_EXACT10
WAL_PITR = PASS_PASS_LINEAGE_VALID_NO_PHYSICAL_GAP_BACKLOG_PENDING_UNRESOLVED_ZERO
CONTROL = ARMED_GENERATION6_UNCHANGED
LIVE = DISABLED_UNCHANGED
PUSHED = NO
NEXT_ACTION = CONTINUE_TRADERS_5M_SCALPING_PRODUCTION_OBSERVATION_AND_CALIBRATION_BASELINE_01_UNTIL_144_HOMOGENEOUS_BOUNDARIES
```

The original desktop-provider 24-hour `trade-5m-v1` JSONL request reproduced
as a 10.027-second read timeout with zero response bytes. The cause was the
one-shot wide-row load/build/aggregate/serialize path, not N+1. The accepted
path is now arbitrary-range, stable-snapshot keyset pagination with bounded
200-row default pages (2000 maximum), no OFFSET, page-level retry, crash-safe
resume, incremental JSONL/CSV, streaming presentation summary, `.part` fsync
and atomic final replacement.

Real production seven-day desktop loops completed 13,040 5m rows and 6,520
15m rows across 99 pages with no server timeout, duplicate, gap or ordering
drift. Production EXPLAIN measured 57.709 ms first-page and 22.809 ms keyset
SQL, 185 KiB sort memory. Application peak allocation without page retention
was 7.63 MiB. The measured wide-record page acceptance envelope is P95 <= 3s
and max <= 6s; the unchanged per-page read timeout remains 10s.

Only Readonly was replaced. The 5m/15m orchestrators, PostgreSQL, Market Data,
Control and observer were not restarted. Full evidence is in
`docs/audits/TRADERS_DESKTOP_FUNNEL_ARBITRARY_RANGE_EXPORT_TIMEOUT_REMEDIATION_01_FINAL.md`
and the external evidence inbox copy. The external evidence SHA256 is resolved
after the project-state audit commit and recorded in the final handoff.

```text
FILES_CHANGED = app/i18n/catalog.py, app/server_api/funnel_export.py, app/server_api/repositories/protocols.py, app/server_api/routes/v1.py, app/server_api/services/query_service.py, app/server_api/trading_funnel.py, tests/server_api/test_funnel_export.py, FINAL_DECISION.md, docs/audits/TRADERS_DESKTOP_FUNNEL_ARBITRARY_RANGE_EXPORT_TIMEOUT_REMEDIATION_01_FINAL.md, ../traders-client/src/traders_client/api_contract/protocol.py, ../traders-client/src/traders_client/application/app_controller.py, ../traders-client/src/traders_client/funnel_export.py, ../traders-client/src/traders_client/i18n/generated_bootstrap.json, ../traders-client/src/traders_client/providers/mock_provider.py, ../traders-client/src/traders_client/providers/server_provider.py, ../traders-client/src/traders_client/ui/funnel_export_dialog.py, ../traders-client/src/traders_client/ui/main_window.py, ../traders-client/src/traders_client/ui/trading_funnel_view.py, ../traders-client/tests/test_funnel_export.py, ../traders-client/client_status.md, online_trader.md
```
