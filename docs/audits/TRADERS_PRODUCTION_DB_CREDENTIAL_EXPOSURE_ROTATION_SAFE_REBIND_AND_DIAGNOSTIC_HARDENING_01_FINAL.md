# Production DB credential exposure rotation and diagnostic hardening 01

## Verdict

`TRADERS_PRODUCTION_DB_CREDENTIAL_EXPOSURE_ROTATION_SAFE_REBIND_AND_DIAGNOSTIC_HARDENING_01`
completed with PASS. The exposed active principals were
`traders_readonly_api` and `traders_paper_runtime`; the affected consumers were
Readonly and Operator Control. The old credentials were denied on fresh
connections, the new credentials authenticated, and only those two containers
were replaced. PostgreSQL, Market Data, 15m, and 5m were not restarted or
replaced.

## Incident scope and secret safety

Scope was established by internal authentication of protected binding
candidates. Only principal names and boolean outcomes were emitted. The stale
`traders_ml` values present in container environment metadata were already
invalid, while the active shared-file credential was not present in the
offending environment output; it was therefore not rotated for convenience.

The new extended Docker inspector returns only allowlisted container/image
identity, restart count, state, health, environment key names, protected
binding identity, validated DB principal names, executable basenames, and
source revision. Recursive structured redaction and URI userinfo redaction are
covered by fake-secret sentinel tests. The rotation controllers no longer use
raw Docker inspection. Operational documentation forbids raw inspect, rendered
Compose config, and environment dumps.

Active-secret scans after rotation found zero matches in tracked files,
evidence, and task-window logs. Protected bindings are Git-ignored,
Docker-excluded, ACL-restricted, and untracked. No credential value,
secret-derived fingerprint, or tracked secret was created.

## Privilege matrix

The complete ordered catalog snapshots before and after rotation were exactly
equal, including role attributes, memberships, table grants, routine grants,
and Alembic revision.

| principal | superuser | createdb | createrole | replication | bypass RLS | table privileges |
|---|---:|---:|---:|---:|---:|---|
| traders_ml | YES | YES | YES | YES | YES | owner/admin baseline unchanged |
| traders_paper_runtime | NO | NO | NO | NO | NO | SELECT 23, INSERT 11, UPDATE 6; no DELETE |
| traders_readonly_api | NO | NO | NO | NO | NO | SELECT 22 only |

Role memberships before and after were empty. No GRANT, REVOKE, role creation,
membership change, schema mutation, or privilege expansion occurred.

## Production acceptance

- Alembic remained `0018_promote_5m_production_search`; PostgreSQL is healthy.
- WAL/PITR/lineage are `true/true/true`, physical gap is false, and
  backlog/pending/unresolved are `0/0/0`.
- ACK owner PID 4912 is alive, identity-matched, state-matched, and has a healthy
  heartbeat. The existing lineage and base backup were preserved.
- Fresh 15m and 5m natural boundaries were each exact 10/10 with zero error or
  safety rows. The 5m owner count is one.
- The 5m parameter set remains
  `trade-5m-v1-runtime-v1-87b8a882d06b3539`, risk threshold remains `65.0`,
  and minimum RR remains `1.5`.
- Control remained ARMED generation 6; the Control verification used GET only.
  LIVE remained disabled.
- Readonly returned HTTP 200 with 28 GET routes and zero write routes.
- PAPER commands/orders/fills/positions remained `0/0/0/0`; Binance order API
  calls were zero.

## Validation

```text
SAFE_INSPECTOR_AND_SECURITY_TESTS = 632 passed
IMPACTED_SERVER_CONTROL_READONLY_TESTS = 896 passed, 17 skipped
TRADING_INVARIANT_TESTS = 115 passed, 5 skipped
COMPILE = PASS
ACTIVE_SECRET_SCAN = TRACKED0_EVIDENCE0_LOG0
CHANGED_PATH_REGRESSION_FAILURES = 0
SECURITY_FINDINGS = 0
PROJECT_STATE_COMMIT = d877d729e44859da1aaf8e31aa71b491d466f3f5
PUSHED = NO
```

The Windows test runner emitted one non-functional temporary-directory cleanup
warning; no test failed. The interrupted Scalping refactor is not marked
complete. Its pending Readonly i18n deployment and remaining runtime acceptance
remain parent-task work.

```text
SECURITY_REMEDIATION = COMPLETED
INTERRUPTED_SCALPING_REFACTOR = READY_TO_RESUME
NEXT_ACTION = RESUME_TRADERS_5M_SCALPING_MODE_FULL_MODULAR_REFACTOR_01_FROM_SECURITY_PREFLIGHT
```
