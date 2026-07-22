# Online orchestrator semantic monitoring

The semantic monitor is an additive, read-only layer on `ReliableObserver`. It does not own the observer process, heartbeat, lock, monotonic schedule, or service lifecycle.

## Contract

Enable it with `--semantic-contract SOAK_CONTRACT.md` and `OBSERVER_READ_ONLY_DSN`. The contract must explicitly define the measured interval, symbols, expected counts, required timeframes, deployed freshness grace, missing-run grace, and `FRESHNESS_DEADLINE_POLICY = PERSISTED_OR_RUNTIME_GRACE`. The contract `SOAK_DIRECTORY` must equal `--soak-directory`; a restart with a different contract hash fails closed.

## Data safety

Runs and results are read in one bounded `REPEATABLE READ READ ONLY` transaction with a database clock snapshot. Candles are read in a separate bounded `READ ONLY` transaction. Both use statement and lock timeouts, an application name, indexed symbol/time ranges, and rollback. No observer code performs database writes, `SELECT FOR UPDATE`, migrations, service control, private API calls, or orders.

Result payloads are never persisted. The collector emits only result identity, public result type, timestamp, and a database-computed MD5 content fingerprint. Observer error handling uses the existing centralized redaction.

## Artifacts

- `semantic_snapshots.jsonl`: one summary per observer sample.
- `window_status.jsonl`: only a new expected window or a changed state/diagnostic.
- `incident_log.jsonl`: created at startup, including when empty; semantic incident IDs are deterministic.
- `semantic_state.json`: atomically replaced restart checkpoint.

Every semantic JSONL record is canonical UTF-8, one object per newline, and carries `observer_instance_id`, `sample_sequence`, and `recorded_at_utc`. Existing observer artifacts and schemas remain additive-compatible.

## Failure behavior

Collector status is one of `SUCCESS`, `PARTIAL`, `TIMEOUT`, `UNAVAILABLE`, or `FAILED`. Incomplete semantic data produces a typed collector incident and a `PARTIAL` sample. It never creates missing/cardinality/candle conclusions and never resolves an existing incident. The independent heartbeat continues; repeated partial cycles move the existing observer health state to `DEGRADED` through its unchanged failure threshold.

## Controlled stop and restart

Use the existing `--request-stop` flow. Final state includes `semantic_summary`. On restart, the observer gets a new instance ID, loads the same contract-bound semantic state, appends to old JSONL, suppresses unchanged window transitions, and continues incident occurrence counts. Contract mismatch or corrupt state fails closed and writes `SEMANTIC_STATE_CORRUPTION`.

## Audit

`--audit-only` accepts both legacy artifacts and the two semantic JSONL files. Empty `incident_log.jsonl` is valid. Duplicate semantic sample identity is `(observer_instance_id, sample_sequence, schema_version)`.
