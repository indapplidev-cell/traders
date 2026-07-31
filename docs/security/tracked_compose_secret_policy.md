# Tracked Compose secret policy

Tracked Compose files may contain only required environment references or
approved external-secret references at credential-bearing key paths. A
required environment reference has no fallback value and fails preparation
when the protected value is absent. Literal credentials, credential-bearing
URLs, optional references, and references with defaults are rejected.

`scripts.security_retry_controls` parses only structural key paths and returns
fixed value classes. Its renderers never return source values, raw lines,
exception messages, hashes, fingerprints, or any other secret-derived output.
Parser failures report only file, document index, key path, and error class.

The protected local binding `.env.production.local` remains ignored and
untracked. Repository scanners must reject it before open, read, hash, or
fingerprint operations. Credential verification is a separate explicitly
authorized control and is not a scanner operation.

Production inspection is limited to container name and ID, image ID, restart
count, running and health states, safe port bindings, Alembic status, HTTP
status, and route counts. Full Docker objects, environment fields, rendered
Compose configuration, environment dumps, and secret-bearing arguments are
forbidden.
