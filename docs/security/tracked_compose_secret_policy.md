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

For an extended production container diagnostic use only:

```powershell
python scripts/safe_production_inspector.py `
  --extended-container <exact-container-name>
```

The extended inspector reduces the captured Docker document in memory before
returning. It may emit environment key names, non-secret DB principal names,
runtime-secret binding identities, executable basenames, image/container IDs,
restart count, state, health, and a validated source revision. It never emits
environment values, mount source paths, arguments, raw labels, or the raw
Docker document. Structured diagnostics that may contain passwords, tokens,
authorization values, database URLs, or DSNs must pass through
`redact_diagnostic`; credential-bearing URI userinfo must pass through
`redact_uri` before serialization.

The following production diagnostic forms are forbidden, including in task
evidence and troubleshooting instructions:

```text
docker inspect <production-container>
docker container inspect <production-container>
docker inspect --format '{{json .Config.Env}}' <production-container>
docker compose config
docker exec <production-container> env
docker exec <production-container> printenv
```

Terminal redaction after one of these commands has emitted output is not an
acceptable control. Failures from the safe inspectors must be reported only as
normalized error classes; raw stdout, stderr, configuration, and exception
messages are not diagnostic output.
