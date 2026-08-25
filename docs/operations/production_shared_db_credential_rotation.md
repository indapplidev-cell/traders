# Production shared DB credential rotation

The production `traders_ml` login is consumed by the market-data, 15m, and 5m
containers. Its only approved persistent credential binding is the untracked
host-local file:

```text
D:\disk_E\game_projects\traders\traders-ml\.secrets.production.local\shared-db-password
```

The directory and file have Windows ACL inheritance disabled. Access is limited
to the current operator SID, Local System, and local Administrators. The path is
excluded from Git and Docker build context. Compose mounts it as a runtime
secret; the credential and full database URI are absent from Docker
`Config.Env`. The application shell constructs its process-local database URI
and immediately replaces itself with the Python runtime.

`scripts/production_db_credential_rotation.py --execute` is a one-shot,
no-echo controller. It identifies the active principal from all affected
bindings, requires exact agreement, creates a high-entropy independent
credential, applies the protected binding, performs the PostgreSQL password
switch, reconnects only the three affected services with their existing images,
runs a real query from each client boundary, and proves SQLSTATE `28P01` for a
fresh connection using the old credential. It never changes privileges, role
membership, schema, Control, canary, LIVE, strategy, risk, or parameters.

PostgreSQL supports one password verifier per role. Consequently the password
activation and old-password invalidation are one atomic `ALTER ROLE` operation;
there is no interval in which fresh connections with both passwords can pass.
Existing authenticated sessions remain valid while the three clients are
narrowly rebound. The PostgreSQL service itself is not restarted.

The safe verifier is:

```powershell
python scripts/verify_shared_db_secret_binding.py
```

It emits only booleans and error classes. It never emits the credential, its
length, any fragment, URI, hash, or fingerprint.
