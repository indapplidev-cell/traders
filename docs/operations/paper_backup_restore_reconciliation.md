# PAPER backup, restore, PITR, and reconciliation readiness

This runbook is a production-enablement prerequisite, not authority to enable
PAPER. Normal Alembic downgrade from 0011 to 0008 is destructive and is
forbidden as a recovery method.

## Proposed recovery objectives

The proposed, not yet formally approved policy is RPO 15 minutes, RTO 2 hours,
maximum logical-backup age 24 hours, 35-day retention, monthly logical restore
rehearsal, and quarterly PITR rehearsal. PostgreSQL 16 logical backup and
physical/WAL recovery are both required. Backup encryption, access control,
integrity verification, pre-migration backup, persistent storage, and an
assigned database-operations owner are mandatory. Isolated proof is not
production proof.

## Universal recovery boundary

For every incident: disable PAPER, deny new work, wait for any current child
transaction boundary, preserve the database, and capture only approved no-echo
metadata. Never downgrade 0011 to 0008 as normal recovery. Select either a
tested forward fix or an approved backup/restore path. Validate the schema,
run bounded read-only reconciliation, and resume only after explicit operator
authorization. Preserve timestamps, safe IDs, schema versions, tool versions,
checksums, decisions, and reconciliation reports as evidence; never preserve
credentials, connection strings, raw WAL, or protected-binding derivatives.

## Incident matrix

| Incident | Detection and immediate stop | Allowed inspection | Forbidden action | Recovery decision and validation |
|---|---|---|---|---|
| Migration failure before PAPER data | migration error; keep PAPER disabled | schema/version, locks, migration logs with secrets removed | downgrade or new PAPER work | tested forward fix preferred; restore only if structural damage; validate 0011 and reconcile empty/approved scope |
| Partial migration failure | unexpected revision/object inventory; deny work | transactional status and safe catalog metadata | manual production DDL | preserve DB, forward fix or approved restore; exact schema plus reconciliation |
| Runtime deployment failure | health/startup gate failure; stop runtime | image/version, GET health, safe logs | schema rollback, runner retry loop | roll application back while preserving DB or forward fix; schema and read smoke |
| PAPER corruption suspicion | invariant/alert finding; global PAPER stop | bounded read-only reconciliation and safe IDs | repair through reconciliation or ad-hoc SQL | choose known-good backup/PITR boundary or reviewed forward data fix; reconcile before resume |
| Runner crash after durable prefix | typed runner failure; no automatic retry | durable graph and bounded audit rows | replay an ambiguous prefix | reconcile and infer exact durable prefix; separate explicit resume authorization |
| Database loss | connection/storage loss; stop all consumers | infrastructure status and approved backup catalog | create empty production DB and resume | restore latest approved artifact or PITR target; verify schema, exact graph, repository/runtime read smoke |
| Container or host loss | infrastructure failure; keep PAPER disabled | persistent-volume and image identity metadata | assume container filesystem is durable backup | recreate on approved infrastructure and restore/PITR; full validation |
| Backup corruption | checksum/tool integrity rejection | safe manifest and artifact checksum | restore corrupted or mismatched artifact | select earlier verified artifact or PITR; record lost RPO and reconcile |
| PITR failure | recovery target/replay/startup mismatch | bounded recovery logs and safe metadata | expose WAL or retry against production source | retain failed target, select verified logical restore or earlier target; validate on fresh instance |
| Reconciliation failure after restore | typed inconsistent/safe-failure result | bounded findings and safe IDs | let reconciliation repair, return HEALTHY on incomplete scan | keep restored target isolated, select another backup/target or reviewed fixture/data repair; rerun from start |

## Backup selection and authorization

Select only an artifact whose safe manifest has PostgreSQL major 16, expected
schema head, byte length, verified SHA-256, successful tool integrity check,
retention class, and rehearsal identity. A missing, truncated, modified,
wrong-checksum, wrong-engine, wrong-schema, or unverified artifact fails closed.
Production restore/PITR needs a separate approved change, recovery owner, and
resume approver.

## Read-only reconciliation

Invoke only through an explicit safe target manifest:

```text
python -m app.engine_paper.reconciliation --target <explicit-safe-target-manifest> --read-only-reconcile
```

The manifest contains only target class, opaque target identity, and expected
schema head. A permanent approved resolver must supply the connection outside
the manifest. The service first starts a PostgreSQL read-only transaction and
reads `alembic_version`. Any revision other than 0011 returns
`PAPER_SCHEMA_NOT_DEPLOYED` with zero PAPER-table queries. Reads are bounded;
limit overflow, cancellation, read faults, invariant faults, and rendering
faults can never return `HEALTHY`. The command never repairs data.

Exit codes are stable: 0 healthy, 10 inconsistent, 11 schema not deployed,
12 target rejected, 13 read-only violation, 14 bounded limit exceeded,
15 cancelled, and 16 safe failure.
