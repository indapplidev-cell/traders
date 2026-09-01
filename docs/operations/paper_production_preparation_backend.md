# Production PAPER preparation execution layer

`app.engine_paper.production_preparation` remains the canonical action, result,
allowlist, target-guard, mutation-budget, readiness, and executor contract.
`PostgresPaperProductionPreparationBackend` implements that protocol. It may
only ensure the runtime role, reconcile the two exact grant allowlists, bind
and validate the runtime credential, publish disabled runtime configuration,
and narrowly deploy the Readonly API. It has no ARM, START, trade, order,
canary, Binance, or LIVE authority.

Every mutation class is bounded to one attempt by
`PaperProductionPreparationMutationBudget`. Schema migration and immutable
baseline creation are separately explicit orchestration steps. PostgreSQL role
and grant changes use transactions and postcondition checks. Existing broader
role attributes, memberships, ownership, table privileges, grant option, DDL,
DELETE, or baseline write privilege fail closed; dry-run never revokes drift.

## Protected binding boundary

`PaperProductionPreparationTargetBinding` is the production administrator
capability boundary. In canonical production mode it accepts no caller URL,
password, target environment variable, or secret argument. It reads exactly
the Compose-owned `.secrets.production.local/shared-db-password` capability
used by the PostgreSQL container, combines it with the fixed tracked
localhost PostgreSQL contract, constructs the hidden-parameter engine, and
returns only composed dependencies. Missing, malformed, mismatched, or
unreachable targets fail with fixed reason codes.

The deployment migrator accepts every proven linear production revision from
`0008` and `0014` through the current `0020` head. It upgrades forward to
`0020_paper_plan_execution_outcomes`, then reconciles the exact runtime and
Readonly grants. This avoids depending on the redundant administrator copy in
`.env.production.local`, which can become stale after shared-secret rotation.

`ProtectedPaperRuntimeBindingAdapter` remains the runtime credential boundary. Public
executor/backend calls accept and return no password, URI, token, or secret.
The adapter generates a credential with `secrets.token_urlsafe(48)`, stages a
restrictive same-directory pending binding, installs the same staged value in
PostgreSQL, and atomically publishes it. A retry reuses a valid pending value,
so an uncertain result does not cause blind rotation. Results, repr, errors,
and CLI output contain sanitized booleans and role names only.

The production protected binding remains `.env.production.local`; source,
tests, and plan mode do not open it. The concrete task tests use only isolated
paths. Existing file security mode is copied to the replacement; a new
isolated binding is owner-read/write only.

## Non-secret identity configuration

The tracked composition is `ops/production/paper-preparation.json`. It points
to persistent host-local `ops/production/paper-identity.json`, which is ignored
by Git and is safe for operator inspection and audit. That JSON must contain
exactly these non-secret keys, with no duplicates or additional keys:

```json
{
  "PAPER_PRODUCTION_ACCOUNT_ID": "<explicit 3-128 char production identifier>",
  "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "<explicit stable lifecycle identifier>",
  "PAPER_PRODUCTION_CURRENCY": "USDT"
}
```

There is no default identity, test fallback, client override, random value, or
restart rotation. Values use the canonical existing validation contract.

## CLI

The tracked module is `app.engine_paper.production_preparation_cli` and the
installed command is `traders-paper-production-prepare`.

```text
python -m app.engine_paper.production_preparation_cli --production plan
python -m app.engine_paper.production_preparation_cli --production status
python -m app.engine_paper.production_preparation_cli --production execute \
  --ack I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS \
  --actions ENSURE_RUNTIME_ROLE,...
```

All three modes use the same trusted target binding and executor composition.
`status` and `plan` validate the exact target read-only and perform zero
mutation. `execute` has no
default, requires the exact acknowledgement and an exact comma-separated
action set, and accepts no secret argument. Full separately authorized
preparation additionally uses `--orchestrate-schema-and-baseline
--initial-balance-usdt 100.00`; it verifies 0008 first, migrates to 0013,
executes role/grant/binding actions, creates/gets the immutable baseline, then
executes only the disabled-runtime and narrow-Readonly deployment actions.

The privileged database URL is never accepted from or returned to the caller.
The production target ID is the exact tracked `traders-production-primary`;
canonical production mode also fixes the protected source, deployment driver,
host, port, database, and administrator identity. `--config` is reserved for
isolated synthetic PostgreSQL 16 proofs and rejects the canonical production
target. The target must be PostgreSQL 16 at the accepted revision, with
control DISABLED and LIVE false.

Exit codes are deterministic: `0` success, `2` validation blocked, `3` target
mismatch, `4` privilege drift, `5` binding unavailable, `6` identity
unavailable, and `7` execution failure. Output contains only sanitized target,
action, role, readiness, mutation-count, and PASS/BLOCKED fields.

This execution layer being ready does not prepare production. Production stays
at revision 0008 with no PAPER baseline or runtime until the separately
authorized production-preparation task reruns all fresh WAL/PITR and target
gates.
