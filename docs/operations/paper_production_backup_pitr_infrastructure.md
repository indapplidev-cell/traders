# PAPER production backup and PITR infrastructure remediation

This is a fail-closed production-applicability review. It does not authorize a
production backup, restore, PITR, migration, PAPER graph read, runner, restart,
role change, protected-binding access, PAPER enablement, or LIVE operation.

## Safe production inventory

The permanent allowlisted inspector proves PostgreSQL major 16, `pg_dump`
tooling present, and PostgreSQL data on a persistent external Docker volume.
It reports no configured approved backup destination and no last-backup
metadata. PostgreSQL archive settings are `UNPROVEN`: the approved no-echo
settings probe cannot authenticate without crossing the protected binding.
No alternate credential or environment inspection is permitted. Therefore
production backup capability is `NOT_READY` and PITR capability is `UNPROVEN`.

The database volume proves primary database persistence only. It is neither a
backup nor an acceptable backup/WAL failure domain. An approved destination
must be outside the PostgreSQL data directory, ephemeral container layer, Git
repository, and project temporary storage; persistent, retention-bounded,
encrypted at rest, access-controlled, capacity-proven, and approved for both
backup and restore processes.

## Domain decision record

| Domain | Status | Evidence/blocker | Required remediation and closure proof |
|---|---|---|---|
| B1 production backup mechanism | NOT_READY | `pg_dump` exists, but no approved scheduled production mechanism or last-backup metadata | approve no-echo source/destination mechanism; produce verified successful catalog metadata |
| B2 persistent backup storage | NOT_READY | production data volume is persistent; separate backup destination absent | provision approved separate persistent encrypted destination and prove failure-domain separation |
| B3 backup artifact integrity | READY | checksum, manifest, tool check, fail-closed and atomic publication contracts/tests | apply the contract to the approved mechanism |
| B4 backup retention/lifecycle | NOT_READY | bounded retention is proposed, not approved or deployed | approve policy; implement dry-run bounded cleanup with safety floors |
| B5 production restore procedure | READY | isolated-first procedure and pre/postflight contracts complete | keep production restore separately authorized |
| B6 production-applicable restore rehearsal | READY | PostgreSQL 16 production-shape logical dump/restore to fresh isolated target passes | repeat on cadence after approved destination exists |
| B7 WAL/PITR configuration | UNPROVEN | safe archive settings unavailable without prohibited binding access | controlled change must prove or enable archive mode and compatible WAL level |
| B8 PITR archive persistence | NOT_READY | no approved separate persistent WAL archive is configured | provision persistent failure-domain-separated WAL archive |
| B9 PITR restore procedure | READY | isolated recovery target, timeline, validation and reconciliation procedure exists | exercise exact approved production design after infrastructure change |
| B10 RPO/RTO policy | NOT_READY | 15-minute RPO, 2-hour RTO and cadences remain proposed | approval authority records approval evidence |
| B11 operator ownership/change control | NOT_READY | six role classes and two-person recovery gate are proposed | approve ownership, ticket and evidence responsibilities |
| B12 backup monitoring/alerting | NOT_READY | complete contract exists; production monitoring unchanged | implement or formally accept all metrics and alerts |
| B13 backup access control | NOT_READY | least-privilege class specified but destination absent/unapproved | approve roles and enforce source/destination grants |
| B14 backup failure runbook | READY | tool, integrity, capacity, publish, PITR and no-valid-backup branches documented | validate during controlled infrastructure task |
| B15 infrastructure cleanup/retention | READY | task cleanup and safe retention algorithm specified | production cleanup remains disabled until policy approval |

## Atomic publication and backup command boundary

An approved backup executes without password or connection URI in argv,
without environment dumps, and with bounded no-echo logs. The lifecycle is:

```text
IN_PROGRESS -> TOOL_COMPLETED -> CHECKSUM_VERIFIED
            -> MANIFEST_VERIFIED -> PUBLISHED
```

Publication is an atomic rename/promotion only after tool success, checksum,
manifest, schema/engine metadata and capacity checks. Tool failure, truncation,
checksum mismatch, manifest mismatch, capacity failure, or atomic promotion
failure leaves `PUBLISHED = NO`; partial output is quarantined or removed and
is never selectable.

## Retention and capacity

The proposed policy retains at least two full known-good backups, never deletes
the last known-good backup, and never deletes a base backup required by
retained WAL. Cleanup requires a dry run, a bounded deletion batch, and a
minimum recovery safety floor. No production cleanup is authorized here.

Capacity uses this exact floor:

```text
required free space >= max(
  2 * expected full backup size,
  expected full backup size + PITR retention reserve
)
```

Production database size, expected backup size, WAL generation and destination
free space are not safely proven, so capacity readiness remains `UNPROVEN`.

## Restore and PITR procedure

Select an approved artifact, verify checksum/manifest, verify PostgreSQL major
and schema metadata, and restore to a fresh isolated target first. Verify exact
Alembic head, run `PaperReadOnlyReconciliationService`, run a bounded repository
read smoke, and require explicit authorization before any approved production
recovery or runtime resume. A production target is rejected by this task's
preflight. Alembic downgrade is not normal recovery.

If production PITR is absent or unproven, the controlled infrastructure change
must establish `archive_mode = on`, an appropriate WAL level, persistent
failure-domain-separated archive storage, a safe archive mechanism, base backup
cadence, WAL retention covering the recovery window, archive-health monitoring,
a no-echo restore-command contract, timestamp/LSN/named targets, explicit
timeline handling, and a fresh isolated test restore environment. This requires
external storage and may require PostgreSQL restart and container recreation;
none is applied by this review.

## Recovery decision tree

```text
failure
  +-- database intact and usable
  |     +-- disable PAPER -> forward fix -> reconcile -> authorize resume
  +-- data corrupted or lost
        +-- valid backup
        |     +-- isolated validation -> approved restore -> reconcile
        +-- PITR available
              +-- approved target -> isolated PITR -> reconcile
              +-- otherwise hard incident -> no resume
```

Backup failure stops publication and alerts the backup operator. PITR archive
failure stops recovery-window claims and alerts the PITR operator and incident
commander. With no valid backup and no valid PITR chain, the only decision is a
hard incident with no PAPER resume.

## Ownership and monitoring proposal

Roles are backup operator, restore operator, PITR operator, incident commander,
PAPER runtime operator, and approval authority. Each action requires a change
ticket and evidence. Restore/PITR and resume use a two-person gate. Role names
are classes, not people, and remain proposed rather than approved.

Required metrics are last successful backup age, size, duration, verification,
destination free space, failed backup count, WAL archive lag/failures, oldest
recovery point, base backup age, restore rehearsal age, and PITR rehearsal age.
Alerts cover old/invalid/missing backup, low capacity, stalled/gapped WAL, and
overdue restore/PITR rehearsals. Production monitoring is not mutated here.

## Closure decision

`BACKUP_PITR_BLOCKER_CLOSED = NO`. Closure requires proven production DB
persistence, an approved backup mechanism and separate destination, atomic
integrity publication, production-applicable rehearsal, proven PITR (or an
explicit approved no-PITR policy), approved RPO/RTO and ownership, sufficient
capacity, accepted monitoring, complete runbooks, and reconciliation. The next
task is `TRADERS_ML_PAPER_TRADING_PRODUCTION_BACKUP_PITR_CONTROLLED_INFRASTRUCTURE_CHANGE_01`.
