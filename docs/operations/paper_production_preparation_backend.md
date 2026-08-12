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

`ProtectedPaperRuntimeBindingAdapter` is the only credential boundary. Public
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
python -m app.engine_paper.production_preparation_cli --config <non-secret-json> plan
python -m app.engine_paper.production_preparation_cli --config <non-secret-json> status
python -m app.engine_paper.production_preparation_cli --config <non-secret-json> execute \
  --ack I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS \
  --actions ENSURE_RUNTIME_ROLE,...
```

`plan` is the only mode that does not resolve the privileged environment
binding; it consumes no secret and performs zero mutation. `execute` has no
default, requires the exact acknowledgement and an exact comma-separated
action set, and accepts no secret argument. Full separately authorized
preparation additionally uses `--orchestrate-schema-and-baseline
--initial-balance-usdt 100.00`; it verifies 0008 first, migrates to 0013,
executes role/grant/binding actions, creates/gets the immutable baseline, then
executes only the disabled-runtime and narrow-Readonly deployment actions.

The privileged database URL and the independent safe target ID are resolved
only from `TRADERS_PAPER_PREPARATION_ADMIN_DATABASE_URL` and
`TRADERS_PAPER_PREPARATION_TARGET_ID`. They are never serialized. The target
must be production, PostgreSQL 16, at the caller-declared accepted revision,
with control DISABLED and LIVE false.

Exit codes are deterministic: `0` success, `2` validation blocked, `3` target
mismatch, `4` privilege drift, `5` binding unavailable, `6` identity
unavailable, and `7` execution failure. Output contains only sanitized target,
action, role, readiness, mutation-count, and PASS/BLOCKED fields.

This execution layer being ready does not prepare production. Production stays
at revision 0008 with no PAPER baseline or runtime until the separately
authorized production-preparation task reruns all fresh WAL/PITR and target
gates.
