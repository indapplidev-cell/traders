# Production PAPER source contracts

## Frozen revision 0013

`0013_paper_first_canary_correlation` was introduced and accepted by commit
`a60386f08ec11d4149ace1f8f9e968246d358eb9`. Its Git blob and semantic schema
are authoritative. The accepted LF SHA256 is
`08f9f65acfef946e89dd41297ba14a1dbeb113b62a91a22331a64b5adf620f54`.
The apparent `6d46a437e8f44562e1c6d0bd9a746827d404b8bd530c363d045ff4abf2f8d5f1`
value was the same content after Windows `core.autocrlf` materialized CRLF.
The registry is unchanged. `.gitattributes` now fixes revision 0013 only to LF,
and the verifier canonicalizes only the already-accepted 0013 checkout while
also comparing the accepted Git blob. Any semantic or byte change after LF
canonicalization still fails deterministically.

## Production account identity

`PaperProductionAccountIdentityBinding` is the sole production binding for the
V1 PAPER accounting account. The operator supplies three non-secret deployment
configuration values: `PAPER_PRODUCTION_ACCOUNT_ID`,
`PAPER_PRODUCTION_ACCOUNTING_SESSION_ID`, and `PAPER_PRODUCTION_CURRENCY=USDT`.
There are no defaults, test fallbacks, client inputs, UUID generation, or
restart-time rotation. Values are stripped-ambiguity-free, canonical uppercase
identifiers of 3–128 characters using `A-Z`, `0-9`, `_`, and `-`.

The accounting session denotes the durable accounting lifecycle, not a process
session. Restarting any service retains it. Rotation is a separate controlled
operator configuration change and requires its own accounting/baseline review;
it is never implicit. Baseline, accounting, reconciliation, and readonly
reporting consume the resulting `PaperAccountIdentity`. Reporting rejects a
persisted baseline whose identity differs from the configured production one.

## Protected preparation executor

`PaperProductionPreparationExecutor` has an explicit bounded action vocabulary:
ensure `traders_paper_runtime`, reconcile runtime grants, reconcile readonly
grants, bind and validate the runtime credential, deploy a disabled runtime
configuration, and narrowly deploy the Readonly API. It contains no ARM,
START, trading, order, Binance, or LIVE action.

The caller passes no secret and never reads a protected file. A privileged
backend and protected-binding port consume a credential generated inside the
executor with `secrets.token_urlsafe(48)`. Results and exceptions are sanitized:
no password, URI, credential value, hash, fingerprint, or protected path is
returned or logged. Dry-run calls neither port and reports zero mutations.

The runtime allowlist gives upstream data SELECT, immutable baseline SELECT,
and repository PAPER tables only their required SELECT/INSERT/UPDATE subset.
It grants no DELETE, DDL, ownership, role membership, or GRANT OPTION. The
Readonly API allowlist is SELECT-only over PAPER reporting tables. Existing
role state broader than the contract returns
`EXISTING_ROLE_PRIVILEGE_DRIFT`; it is not silently preserved or revoked.

The deployment target guard requires PRODUCTION, PostgreSQL 16, and starting
Alembic `0008_engine_orchestrator_freshness_retry`. Published runtime config is
OFF/DISABLED with no daemon, scheduler, auto-start, auto-arm, or LIVE. Readonly
deployment is a distinct narrow operation and never requires full-stack
restart or `docker compose down`.

## Preparation sequence

The separately authorized preparation retry must: revalidate Git and evidence;
confirm fresh WAL/PITR; resolve the non-secret identity; run sanitized dry-run;
migrate 0008→0013; ensure the exact role and grants; bind/validate the protected
credential through the privileged port; create/get the immutable 100.00 USDT
baseline; deploy only disabled runtime config and the narrow Readonly API;
reconcile; and confirm control remains DISABLED. This source task performs none
of those production mutations.
