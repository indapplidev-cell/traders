# Persistent protected secret binding

## Purpose and canonical location

The production host keeps the readonly API runtime binding at:

```text
D:\disk_E\game_projects\traders\traders-ml\.env.production.local
```

This is a permanent, host-local control file in the active server root. It is
owned operationally by the production-host administrator and is consumed only
by an explicitly authorized readonly-API deployment. It is not application
source, a deployment artifact, or a client configuration file.

The binding uses the existing runtime configuration names:

```text
TRADERS_READONLY_API_DATABASE_URL
TRADERS_READONLY_API_HOST
TRADERS_READONLY_API_PORT
```

`TRADERS_READONLY_API_DATABASE_URL` is the canonical runtime name for the
credential-bearing database URI. `TRADERS_READONLY_API_HOST` is the canonical
runtime name for the bind host. Competing `...DATABASE_URI` or `...BIND_HOST`
aliases must not be introduced.

## Protection contract

The file must remain untracked and match the exact Git ignore rule
`/.env.production.local`. Docker build context must match the exact
`.dockerignore` rule `.env.production.local`. It must never enter an image
layer, image history, SBOM, Docker-generated source archive, evidence package,
or Git object.

Windows ACL inheritance is disabled. Access is limited to:

- the current interactive user SID, with Modify;
- `S-1-5-18` (LOCAL SYSTEM), with Full Control;
- `S-1-5-32-544` (local Administrators), with Full Control.

Everyone, Authenticated Users, Users, Guests, ANONYMOUS LOGON, Network Service,
all other principals, and deny rules fail the contract. Apply and audit access
by SID, not localized account names.

`.env.production.local` is not a backup target. It must not be copied to
evidence, ZIP, Git, an image, screenshots, logs, clipboard histories, or
general-purpose backup systems.

## Foundation and provisioned states

The approved foundation state contains all three keys, with:

```text
TRADERS_READONLY_API_DATABASE_URL = empty
TRADERS_READONLY_API_HOST = 127.0.0.1
TRADERS_READONLY_API_PORT = 8765
```

An empty database URL is intentional during foundation acceptance. It proves
that storage and access controls exist without creating a production role,
password, or credential-bearing URI. The verifier's normal mode accepts this
state; `--require-provisioned-secret` rejects it.

The provisioned state is reached only by a separately authorized controlled
deployment task. The client never receives the database URL.

## Controlled provisioning and Compose consumption

The next deployment task must:

1. create or verify the dedicated least-privilege `traders_readonly_api`
   PostgreSQL identity;
2. generate a strong password in memory without console output;
3. write the complete `TRADERS_READONLY_API_DATABASE_URL` to the binding
   without echoing the line, value, URI components, value length, or hash;
4. reapply the SID-based ACL contract;
5. run `python scripts/verify_persistent_secret_binding.py
   --require-provisioned-secret`;
6. pass this file only through the approved Docker Compose `--env-file` or
   service `env_file` contract;
7. start or restart only the readonly API after all fresh production gates
   pass.

Compose configuration rendering and diagnostics must never be captured when
they can contain the resolved value. The API remains loopback-only at
`127.0.0.1:8765` unless a later reviewed contract explicitly changes that
boundary.

## Rotation

Controlled rotation creates a new password in memory, updates the database
role, atomically replaces the local binding value, reapplies the ACL, verifies
provisioned mode, restarts only the readonly API, verifies read-only behavior,
and invalidates the old password. Never retain the old or new value in a
temporary file, command history, log, evidence, or backup.

## Revocation and incident handling

For revocation, stop only the readonly API, revoke or disable its database
identity under separate database authorization, clear the local database URL
without printing it, reapply the ACL, and verify foundation mode. Do not delete
the protected foundation file unless its replacement lifecycle is explicitly
approved.

If exposure is suspected, treat the credential as compromised: stop the API,
revoke the credential, preserve only non-secret timestamps and rule IDs for
incident evidence, rotate under the controlled procedure, and inspect Git,
image metadata, logs, screenshots, evidence, and backups by findings count and
path only. Never reproduce a matched fragment.

## Audit

Run:

```powershell
python scripts/verify_persistent_secret_binding.py
git check-ignore -v .env.production.local
git ls-files --error-unmatch .env.production.local
```

The first command must report safe booleans, counts, key names, and SIDs only.
The second must identify the exact ignore rule. The third must exit non-zero.
In provisioned operation, add `--require-provisioned-secret`. Audit Docker
exclusion through the deterministic verifier and tests; do not build an image
solely to inspect this secret-control contract.
