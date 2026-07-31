# Production PAPER runtime readiness review

Task: `TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_RUNTIME_READINESS_REVIEW_01`

This document is a review artifact, not an enablement runbook invocation. It
defines the contracts and gates required before a separate production PAPER
task may be authorized. It creates no production target resolver, credential
loader, service, scheduler, API action, or database mutation path.

## Decision

```text
TASK_STATUS = COMPLETED
PRODUCTION_PAPER_RUNTIME_READINESS = NOT_READY_BLOCKERS_IDENTIFIED
PAPER_MODE_ENABLED = NO
LIVE_MODE_ENABLED = NO
```

The current bounded runner remains foreground, one-shot, operator-controlled,
and isolated-only. A successful review describes reality; it does not turn an
unimplemented or unproven production control into a ready control.

## Readiness matrix

| Domain | Status | Evidence | Blocker / enablement gate |
|---|---|---|---|
| R1 schema migration | READY | Exact `0008 -> 0009 -> 0010 -> 0011` PostgreSQL 16 rehearsal; existing synthetic candle preserved; nine PAPER tables; zero observed lock wait; no destructive upgrade DDL | Repeat against frozen enablement commit with an approved backup |
| R2 rollback / forward fix | NOT_READY | `0011 -> 0010` drops cursor table; `0010 -> 0009` restores two constraints as `NOT VALID`; `0009 -> 0008` drops all PAPER tables | `BACKUP_RESTORE_CAPABILITY_UNPROVEN` |
| R3 deployment topology | READY | Dedicated operator-started one-shot job selected | Materialize a disabled, no-auto-restart, resource-bounded artifact later |
| R4 authorization | READY | Two-person, change-ticket, exact target/version/schema/symbol/bounds acknowledgement specified | Bind named operators through owned change control |
| R5 isolation / permissions | READY | Separate migration and runtime principal designs; isolated deny probes show zero unrelated grants | Provision and verify only in enablement preparation |
| R6 market data / approval | NOT_READY | Closed-only, contiguous, fresh, reproducible input and final approval contracts are specified | Production adapters for both authorities are absent |
| R7 bounds / stop controls | NOT_READY | Initial one-symbol, one-position, one-command, one-stage bounds are specified | Authoritative global PAPER kill switch is absent |
| R8 idempotency / concurrency | READY | Repository, child services, single-cycle, bounded sequence, and runner replay/resume/concurrency pass in isolated PostgreSQL | Repeat frozen-commit acceptance |
| R9 observability / alerts | NOT_READY | Required signal matrices are specified | Production destination, rotation, paging, and incident preservation are absent |
| R10 incident / emergency stop | NOT_READY | Eleven required runbook subjects identified | Kill switch and lifecycle-boundary drills are absent |
| R11 retention / cleanup | NOT_READY | All material and audit record classes identified | No approved retention, deletion, or cleanup contract |
| R12 backup / recovery / reconciliation | NOT_READY | Graph reconciliation invariants specified | No restore proof, PITR/WAL proof, or safe reconciliation command |
| R13 performance / capacity | NOT_READY | Required isolated benchmark shapes and SLO dimensions specified | Complete percentile/query/transaction/memory/log-size acceptance is unproven |
| R14 API / client | READY | Current policy remains `9 GET / 0 write`; operator CLI/job only | Any write API/client control is a separate task |
| R15 security | READY | Immutable remediation evidence accepted; tracked policy and no-echo inspectors retained | Repeat safe checks against frozen enablement commit |
| R16 release / rollback | READY | Explicit 14-step release and 7-step disable/forward-fix sequences | Attach named owners and evidence to a change ticket |
| R17 post-enable validation | READY | One-symbol, one-ENTRY-maximum canary and 60-minute observation specified | Requires separate authorization; not a 72-hour soak |
| R18 LIVE separation | READY | LIVE denied; PAPER runner has no exchange order adapter, network fetch, or mode coercion | Preserve static dependency and denial tests |

`UNPROVEN` is never treated as ready. Any critical or high blocker forces the
overall `NOT_READY_BLOCKERS_IDENTIFIED` decision.

## Migration gap 0008 to 0011

### 0009 PAPER persistence foundation

- Creates eight normalized PAPER tables, ten indexes, primary/unique/foreign
  key/check constraints, and no existing-table mutation.
- PostgreSQL executes the revision transactionally. Object creation takes
  catalog and `ACCESS EXCLUSIVE` locks on the new objects; foreign keys take
  referenced-object locks. No existing rows are rewritten and no backfill is
  required.
- The command status has a `PENDING` server default; remaining required values
  are supplied by writers. Existing market-data, orchestrator, and readonly API
  code does not reference these new objects.
- Classification: `REQUIRES_PRE_BACKUP`. Downgrade is destructive because it
  drops all eight tables and their data.

### 0010 event vocabulary

- Replaces two check constraints to add validated/opened order events.
- Constraint validation scans the existing event and journal rows while
  replacement takes an `ACCESS EXCLUSIVE` table lock. PAPER writes must be
  quiesced.
- No backfill or nullability/default change occurs. Downgrade restores the old
  vocabulary using `NOT VALID`, preserving already-recorded 0010 events while
  limiting subsequent writes.
- Classification: `REQUIRES_WRITE_QUIESCE`; downgrade is
  `SCHEMA_DOWNGRADE_ONLY`, not an application rollback guarantee.

### 0011 exit evaluation cursor

- Creates one cursor table, its index, a position foreign key, and strict
  progression constraints. It does not backfill positions.
- It is fast while empty, but creation still uses catalog and referenced-table
  locks. Current ENTRY/runtime semantics require exact revision 0011.
- Classification: `REQUIRES_PRE_BACKUP`. Downgrade removes cursor history and
  is destructive.

The production-safe classification is a maintenance change with PAPER writes
quiesced, an approved pre-backup, a dedicated migration principal, exact lock
timeouts, and immediate existing-service validation. It is not universally
`ONLINE_SAFE` merely because the isolated database was fast.

## Rollback and recovery

```text
DOWNGRADE_CLASSIFICATION = DOWNGRADE_DESTRUCTIVE
ROLLBACK_STRATEGY = APPLICATION_DISABLE_PLUS_FORWARD_FIX
```

On failure: activate the PAPER kill switch, deny new commands, allow the active
child transaction to finish atomically, disable the PAPER artifact, capture a
safe state manifest, and reconcile. Keep schema 0011 when possible. Restore an
older application only if it is schema-compatible; otherwise deploy a reviewed
forward fix. Do not downgrade through 0009 unless explicit PAPER data loss has
been accepted and a verified recoverable backup exists.

Before enablement, an owned backup policy must define database-level and
schema-only coverage, PITR/WAL status, encryption, storage access, integrity
verification, maximum age, retention, and restore owner. A restore rehearsal
must reconstruct the database in isolation and pass the same schema and graph
reconciliation. None of those production capabilities was inferred by this
review.

## Deployment topology

| Option | Decision |
|---|---|
| Foreground host runner | Rejected as the primary topology: weaker resource/process/deployment identity |
| Dedicated one-shot container | Recommended: explicit start, immutable image, no restart, narrow identity and resources |
| Controlled job container | Acceptable only if it preserves explicit single-use start and does not become a scheduler |
| Existing application integration | Rejected initially: creates lifecycle and accidental-continuity coupling |

The recommended job must have one invocation, no automatic retry or restart,
no daemon, bounded CPU/memory/PIDs/time/output, immutable configuration/request
manifests, preflight gates, cooperative cancellation, and verified cleanup.

## Principals and privileges

The migration principal receives temporary `CONNECT`, schema `USAGE/CREATE`,
and only the DDL needed for reviewed revisions 0009-0011 during the maintenance
window. It is never used by the runtime.

The runtime principal receives `CONNECT`, schema `USAGE`, and
`SELECT/INSERT/UPDATE` (plus narrowly justified delete only for an approved
cleanup command) on the nine PAPER tables. Sequence access is granted only to
PAPER-owned sequences if any exist. It receives no schema ownership, DDL,
role/database creation, grant option, unrelated-table access, or membership
that enables privilege escalation.

Rotation creates and verifies a replacement principal, atomically changes only
the disabled job binding, exercises deny/allow probes, then revokes login,
membership, and object grants from the old principal. Production roles are not
created by this review.

## Target, arming, and acknowledgement

`ProductionPaperRuntimeTargetIdentity` carries opaque environment and database
identities (never a URI), exact schema head, deployment commit/image, and change
ticket. `ProductionPaperRuntimeEnablementArming` binds that identity to a symbol
allowlist, exact hard limits, activation/expiry, single-use state, and a clear
kill switch. `ProductionPaperRuntimeOperatorAcknowledgement` binds an operator
and independent approver to the same immutable values.

Missing, expired, reused, mismatched, broadened, or kill-switched arming fails
before target resolution or mutation. Two people and an approved change ticket
are mandatory.

Initial canary bounds are one symbol, one simultaneous position, one new
command, one worker stage, 300 seconds, at most two candle inputs, at most 40
rows touched, at most 20 event/journal rows, zero retries, and zero resume
attempts. Expansion is not implicit.

## Input and approval authority

The future market-data adapter must select only closed candles from the
authoritative persisted source, prove contiguous boundaries, reject open/future
data, enforce symbol/timeframe and freshness, retain the source timestamp, and
make the selection reproducible. It may not fetch Binance directly.

The approval adapter must carry immutable strategy/risk approval identity and
version, finality, controlled quantity, PAPER mode, symbol, freshness/expiry,
and idempotency identity. Rejected/deferred/non-final/stale approval never
creates a command. Current test fixtures prove domain behavior but are not
production adapters.

## Observability and incident controls

Required structured, bounded, no-echo, correlation-ID signals include runner
invocations; requested/completed stages; entity/state counts; exit decisions;
replay/idempotency/uncertain-commit outcomes; mutation-budget/postflight
failures; cursor lag; input freshness; fees/PnL; duration; and cleanup.

Alerts cover unexpected mutation, stuck CLOSING, an OPEN order beyond its
boundary, cursor lag, semantic duplicates, exhausted uncertain commit, schema
mismatch, unauthorized invocation, and security violations. The enablement task
must name destination, rotation, retention, access owner, pager owner, and
incident-preservation action.

The authoritative kill switch denies new commands at every lifecycle boundary.
An already-open child transaction may complete atomically; no new stage starts.
After ENTRY or while OPEN/CLOSING, position safety action requires its own
approved policy and cannot fall back to LIVE. Required runbooks cover migration
failure, startup denial, partial durable prefix, stuck OPEN/CLOSING, uncertain
commit, duplicates, input gaps, observer outage, credential incident, host
crash, and cleanup failure.

## Retention and reconciliation

An approved contract must assign minimum retention and deletion eligibility for
commands, orders, fills, positions, decisions, cursors, events, journal,
summaries, and logs. Audit/causal records cannot be removed while a dependent
row or incident/legal hold exists. Cleanup must be separately authorized,
bounded, observable, retry-safe, and never share a transaction with runtime
execution.

A safe reconciliation command must be read-only, bounded, rollback-only, and
check order/fill/position accounting; cursor existence for OPEN positions;
decision and close order for CLOSING; close fill for CLOSED; exact fees/PnL and
journal; event ordering/counts; orphans; monotonic versions; and semantic
duplicates. No such command exists yet.

## Release, canary, and observation

Future release order is: freeze commit; verify evidence/security; capture safe
baseline; verify backup/restore; migrate with the migration principal; validate
schema and existing services; provision the runtime principal; deploy disabled
artifacts; validate configuration; run read-only readiness; arm one invocation;
run the minimal canary; observe for 60 minutes; and expand only under a new
authorization.

The smallest canary uses one approved symbol and one explicit final approval,
permits at most the command/ENTRY path, and enforces one-position/notional/time
budgets. Any mismatch, unexpected mutation, stale input/approval, lock wait,
observer outage, cleanup failure, or alert is a stop. Success requires exact
mutation/audit budgets, healthy existing services, safe logs, and no expansion.

The observation samples service health, `9 GET / 0 write`, schema revision,
database locks/sessions, PAPER states and cursor progress, mutation budgets,
idempotency, alerts/logs, and CPU/memory/output at an approved cadence. It is not
a 72-hour soak and does not authorize one.

PAPER and LIVE remain separate. LIVE is out of scope and not implemented; the
PAPER runner has no Binance order adapter and no default or coercion may select
LIVE.
