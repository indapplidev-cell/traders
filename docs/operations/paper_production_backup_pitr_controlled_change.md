# PAPER production backup/PITR controlled operations

This runbook covers the first production PAPER milestone. It never enables
PAPER or LIVE, migrates production, changes a database role, or reads a
protected binding. The technical policy is project-local:

```text
TARGET_RPO_TECHNICAL = 15 minutes
TARGET_RTO_TECHNICAL = 2 hours
MAX_LOGICAL_BACKUP_AGE = 24 hours
MIN_VALID_LOGICAL_BACKUPS = 2
MIN_PITR_WINDOW = 24 hours
RESTORE_REHEARSAL_TARGET_CADENCE = 30 days
PITR_REHEARSAL_TARGET_CADENCE = 90 days
PROJECT_OPERATOR_ROLE = TRADERS_LOCAL_OPERATOR
RECOVERY_APPROVAL_ROLE = TRADERS_LOCAL_OPERATOR
TWO_PERSON_APPROVAL_REQUIRED_FOR_PAPER = NO
```

The approved local root is `D:\traders_ml_recovery\postgres`. It is outside
the Git repositories, evidence inbox, temporary directories and PGDATA. The
root and all children use protected Windows ACL inheritance with no broad
write grant. It remains on the same host failure domain; this is not an
off-host disaster-recovery copy.

## Bounded commands

Run with the protected project virtual environment. The CLI accepts no
password, connection URI, env file or arbitrary container/root identity.

```text
python scripts/production_backup.py preflight
python scripts/production_backup.py create-logical
python scripts/production_backup.py restore-logical
python scripts/production_backup.py verify
python scripts/production_backup.py catalog
python scripts/production_backup.py retention-dry-run
python scripts/production_backup.py create-base
python scripts/production_backup.py sync-wal
python scripts/production_backup.py rehearse-pitr --recovery-target-name traders_ml_backup_pitr_controlled_01
python scripts/production_backup.py refresh-monitoring
python scripts/production_backup.py health
```

Logical artifacts move from `IN_PROGRESS` through tool completion,
`pg_restore -l`, size and repeated SHA-256 verification, manifest validation
and atomic publication. Base backups use `pg_basebackup -Fp -X stream` and
`pg_verifybackup`, then receive a deterministic tree checksum and catalog
entry. Only `PUBLISHED` manifests are selectable.

WAL archiving is fail-closed. PostgreSQL stages an immutable segment, compares
an existing staging file byte-for-byte, and waits at most 300 seconds for the
host operator command. `sync-wal` copies to an `.in_progress` host artifact,
verifies SHA-256, atomically renames it, then creates the in-container ACK.
PostgreSQL reports archive success only after that ACK. A conflicting existing
host artifact fails nonzero and is never overwritten. Confirmed staging files
are boundedly removed; the persistent host archive is retained.

## Retention and health

Retention always begins with a dry run, deletes at most eight governed entries
per invocation, preserves the newest two logical backups, preserves the newest
base recovery anchor, never touches unmanifested/pre-existing artifacts and
updates the catalog atomically. A catalog mismatch, missing artifact,
corruption, orphan manifest or unmanifested artifact fails health.

The health report covers logical backup age/count/checksum, catalog integrity,
destination free space, base-backup validity, WAL progress/unresolved failure,
actual accumulated PITR window and restore/PITR rehearsal timestamps. Future
PAPER preparation fails closed unless the complete health result and read-only
reconciliation availability both pass. During initial bootstrap exactly one
fresh verified logical backup is accepted because the second-backup mechanism
and 24-hour age gate are implemented. No equivalent exception is made for an
actual PITR window shorter than 24 hours.

## Recovery rehearsal

Never restore or replay into production during rehearsal. Restore a logical
backup to a fresh PostgreSQL 16 target with `--no-owner --no-acl`, verify
Alembic `0008`, structural compatibility and the read-only reconciliation
schema gate. For PITR, copy a verified base backup to a task-owned volume,
mount the persistent WAL archive read-only, create `recovery.signal`, select an
approved timestamp/LSN/named restore point and require recovery pause at that
target. Verify schema `0008`, zero PAPER tables and then remove only the
task-owned container/volume.

At schema `0008`, `PAPER_SCHEMA_NOT_DEPLOYED` with zero PAPER-table queries is
the expected reconciliation result and is not a restore failure.
