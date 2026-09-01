# PITR WAL ACK daemon and safe inspector recovery

## Persistent owner startup

Install the canonical owner for the current Windows operator at logon:

```powershell
python scripts/production_wal_archive_remediation.py install-daemon-autostart `
  --root D:\traders_ml_recovery\postgres --interval-seconds 3
```

The installer prefers a LIMITED scheduled task and uses the current-user
Startup folder when Task Scheduler registration is denied to a non-elevated
session. Both paths launch `pythonw` without an interactive window. The daemon
lock replaces a stale PID only after proving that PID is not alive, so an
unclean logout or process termination cannot permanently suppress recovery.
It never replaces a live owner.

Validate the active owner and archive continuity without exposing command
lines or protected bindings:

```powershell
python scripts/safe_wal_ack_inspector.py
python scripts/production_wal_archive_remediation.py diagnose `
  --root D:\traders_ml_recovery\postgres
```

Task: `TRADERS_ML_PITR_WAL_ACK_DAEMON_AND_SAFE_INSPECTOR_RECOVERY_01`

Observed and recovered at: `2026-08-12T12:33:14Z`

## Incident and bounded recovery

- Docker Desktop was stopped and the production containers were unreachable.
- The WAL ACK state file still named PID 15724 as `RUNNING`, but the process was
  proven absent. The exact stale PID lock was removed only after that liveness
  check.
- Docker Desktop was started and the existing containers returned with their
  persistent PostgreSQL volume. No image replacement, container recreation,
  schema migration, PAPER transition, or LIVE transition was performed.
- The WAL ACK daemon was restarted as PID 12828. Its atomic state subsequently
  reported `RUNNING`, `error_class=NONE`, zero pending archive status entries,
  and zero export backlog.
- Recovery waited for the configured natural archive timeout. No
  `pg_switch_wal`, write query, PAPER mutation, or business-data mutation was
  used to accelerate the proof.

## Final production evidence

```text
FINAL_VERDICT = PASS
POSTGRES_CONTAINER = RUNNING_HEALTHY
READONLY_API_HEALTH = HTTP_200
TRACKED_SOURCE_ROUTES = 18_GET_0_WRITE
PRODUCTION_ALEMBIC = 0008_engine_orchestrator_freshness_retry
POSTGRES_MAJOR = 16
POSTGRES_STORAGE = PERSISTENT_EXTERNAL_VOLUME
ARCHIVE_MODE = ON
WAL_LEVEL = REPLICA_OR_HIGHER
WAL_ACK_DAEMON = RUNNING_PID_12828
WAL_ACK_DAEMON_ERROR_CLASS = NONE
ARCHIVED_COUNT_SINCE_POSTGRES_RESTART = 1
HISTORICAL_FAILURE_COUNT_SINCE_POSTGRES_RESTART = 0
ACTIVE_UNRESOLVED_FAILURE_COUNT = 0
PENDING_ARCHIVE_STATUS_COUNT = 0
EXPORT_BACKLOG_COUNT = 0
REQUIRED_WAL_SEGMENTS = 107
ARCHIVE_ARTIFACT_COVERAGE = 107
MISSING_REQUIRED_SEGMENTS = 0
SOURCE_RECOVERABLE_MISSING_SEGMENTS = 0
BASE_BACKUP_CHAIN_CONTIGUOUS = YES
PHYSICAL_WAL_GAP = NO
PHYSICAL_WAL_GAP_UNRECOVERABLE = NO
PITR_WINDOW_SECONDS = 103076
MINIMUM_REQUIRED_PITR_WINDOW_SECONDS = 86400
MINIMUM_24_HOUR_PITR_GATE = PASS
BOUNDED_RETRY_ATTEMPTS = 0
WAL_ARCHIVE_HEALTH = PASS
WAL_ARCHIVE_FINDING = WAL_ARCHIVE_HEALTHY
PAPER_CONTROL = HEALTHY_DISABLED_GENERATION_3
LIVE_ENABLED = NO
```

The safe production inspector was invoked only through its fixed metadata
allowlist. The tracked Compose inspector classified all three protected
references as required references with `policy_result=PASS`. No protected
binding value, container environment, Compose-resolved configuration, or
credential-bearing URI was read or rendered.

## Validation

```text
pytest tests/production_wal_archive_unresolved_failure_remediation
       tests/paper_backup_pitr_infrastructure_remediation/test_safe_inspector.py
       tests/security_retry/test_safe_inspection_and_output_matrix.py
= 1443 passed, 1 skipped

production_wal_archive_remediation.py diagnose = PASS
production_wal_archive_remediation.py retry --timeout-seconds 30 = PASS
safe_production_inspector.py final runtime reread = PASS
safe_tracked_file_inspector.py docker-compose.yml --policy = PASS
paper_production_control status = HEALTHY / DISABLED / generation 3
```

The only skipped test is the existing platform-conditional case in the selected
regression scope. No required test failed.
