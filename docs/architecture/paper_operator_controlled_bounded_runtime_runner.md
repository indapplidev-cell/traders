# Operator-controlled bounded PAPER runtime runner

## Status

The operator runner is an isolated-only, foreground, one-shot process boundary.
It turns an explicitly prepared immutable configuration manifest and immutable
request manifest into at most one call to the authoritative bounded-sequence
canary. It does not enable a production PAPER runtime.

The public boundary is
`PaperOperatorControlledBoundedRuntimeRunner` in
`app.engine_paper.operator_bounded_runtime_runner`.

## Trust and delegation boundary

The runner owns only:

- strict bounded JSON loading from two explicit regular-file paths;
- schema, no-secret, no-production, PAPER-only, and denial-policy validation;
- exact expiring single-use operator acknowledgement validation;
- resolution of one opaque task-owned isolated PostgreSQL identity;
- cooperative signal/deadline cancellation;
- construction of the authoritative request through the resolver-owned builder;
- one bounded-sequence service call maximum;
- typed result/exit-code translation, bounded output, and cleanup.

The injectable `PaperOperatorIsolatedTargetResolver` verifies task ownership,
database/role identity, and migration head
`0011_paper_close_causal_boundary_and_exit_evaluation_cursor`. Credentials,
connection URIs, environment mappings, production bindings, ORM objects, and
sessions never enter either manifest or the safe result.

The resolver returns an internal non-rendered binding containing the existing
`PaperControlledRuntimeBoundedSequenceCanaryService` and an exact request
builder. Before calling the service, the runner checks that request identity,
ordered stages, and cycle count still equal the immutable manifest. It never
truncates, reorders, appends, discovers, or retries a plan.

## One-shot lifecycle

The lifecycle is `STARTING -> VALIDATING -> ARMED -> RUNNING -> FINALIZING ->
EXITED`. A process installs cooperative SIGINT/SIGTERM handling, validates both
manifests and acknowledgement, resolves the isolated target, invokes the
bounded-sequence boundary once, renders one safe summary, performs cleanup, and
exits.

There is no polling, sleep loop, scheduler, daemon, service installation,
detached process, auto-restart, network fetch, exchange call, or automatic
retry. A signal handler only sets a cancellation event. The overall deadline is
observed through the same cooperative token, so an active child transaction is
allowed to finish before the authoritative sequence boundary evaluates
cancellation and postflight state.

## Manifest limits and denials

Configuration JSON is strict UTF-8, at most 65,536 bytes, and request JSON is
strict UTF-8, at most 262,144 bytes. Both require an explicit path, regular
non-reparse file, JSON object root, exact contract version, unique keys, and no
unknown fields. Supplied request input is recursively immutable and bounded;
floating-point values and unbounded collections are rejected.

Secret-like keys are rejected before child-value validation. Passwords,
tokens, API keys, URI/DSN fields, database URLs, environment mappings,
protected-binding paths, database/role names, remote URLs, shell commands,
filesystem globs, and arbitrary import paths are not accepted. Values that
attempt to select production, LIVE, shared databases, continuous execution,
watching, scheduling, daemons, or dynamic discovery fail closed.

The exact operator acknowledgement binds action, task/request/sequence/config
identities, opaque target identity, symbol, ordered stage list, maximum step
count, expiry, phrase/version, and single-use intent. It cannot authorize a
different or reordered request.

## CLI and safe output

The entrypoint is:

```text
python -m app.engine_paper.operator_bounded_runtime_runner \
  --config <explicit-path> \
  --request <explicit-path> \
  --operator-controlled-bounded-run
```

Optional output is one bounded text summary or one allowlisted JSON object.
An optional explicit result path must be a new file under an existing approved
parent outside the repository and is written atomically. Stdout never contains
raw graph payloads, candles, approvals, SQL, environment data, credentials,
URIs, exceptions, tracebacks, or subprocess output. Stderr contains only a safe
typed error class.

The stable process exit codes are:

| Code | Typed outcome |
|---:|---|
| 0 | `COMPLETED` |
| 10 | `VALIDATION_BLOCKED` |
| 11 | `ACKNOWLEDGEMENT_REJECTED` |
| 12 | `TARGET_REJECTED` |
| 13 | `NEXT_STEP_NOT_READY` |
| 14 | `COMPLETED_WITH_DURABLE_PREFIX_STOP` |
| 15 | `CANCELLED_BEFORE_MUTATION` |
| 16 | `CANCELLED_WITH_DURABLE_PREFIX` |
| 17 | `SEQUENCE_FAILED` |
| 18 | `POSTFLIGHT_FAILED` |
| 19 | `RESUME_STATE_AMBIGUOUS` |
| 20 | `SECURITY_POLICY_VIOLATION` |
| 21 | `CLEANUP_FAILED` |
| 22 | `INTERNAL_SAFE_FAILURE` |

Mapping is based only on typed outcomes, never exception text.

## Proven isolated behavior

The acceptance suite covers one through five ordered steps, targeted
subsequences, completed replay, partial resume after prefixes one through four,
ambiguous resume, concurrent equivalent processes, cancellation, faults,
cleanup failure, CLI denials, bounded output, and deterministic exit mapping.
The full five-stage lifecycle ends with one command, two orders, two fills, one
position, one cursor, one exit decision, eight order events, and twelve journal
rows; the position is closed and fees/PnL are applied once.

This implementation adds no migration, schema, persistent runner lock/history,
API route, client behavior, production target, market-data discovery, Binance
transport, PAPER daemon, scheduler, or LIVE execution path.
