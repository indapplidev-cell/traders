# TRADERS_PARAMETER_SWEEP_BLOCK2_FROZEN_DATASET_RESUME_FIX

BLOCK_2_STATUS = PASS
CONFIRMED_INCIDENT = The supplied ERROR.log traceback raised SweepExpectedError("RESUME_FINGERPRINT_MISMATCH") in engine.py because resume rebuilt rows from the then-current Production PAPER database and compared that changing fingerprint with the checkpoint.
ROOT_CAUSE = Dataset identity, search-plan identity, runtime configuration identity, and engine compatibility were collapsed into one live-recomputed resume fingerprint. Continuous database growth therefore invalidated an otherwise compatible checkpoint.

DATASET_MANIFEST = DATASET_MANIFEST.json, version PARAMETER_SWEEP_DATASET_MANIFEST/1, created once for a new run and hash-protected on resume; DATASET_SNAPSHOT.json is its immutable replay payload.
DATASET_CUTOFF = dataset_cutoff_at plus historical_period_start_ms/historical_period_end_ms are pinned when the run is created and exposed in status, CLI, run config, preflight, search plan, and report.
SOURCE_WATERMARKS = Per-source table, timestamp field, maximum timestamp, row count, primary key, and watermark field are frozen for MARKET_1M, MARKET_5M, pipeline observations/runs, selector, commands, positions, exits, costs/MAE-MFE, and time-stop shadow sources.
DATASET_FINGERPRINT_SOURCE = Hash of manifest version, dataset source/profile, source schema version, and the typed immutable dataset snapshot. Decimal and datetime values retain type through tagged JSON serialization.

RESUME_REBUILDS_LIVE_DATASET = NO
RESUME_USES_FROZEN_MANIFEST = YES

NEW_ROWS_AFTER_CUTOFF_BEHAVIOR = Existing run ignores them because resume reads DATASET_SNAPSHOT.json; a new run creates a new cutoff/manifest and includes them.
OLD_ROWS_MUTATION_BEHAVIOR = Mutation/corruption of the frozen snapshot is detected against dataset_fingerprint and raises RESUME_DATASET_MUTATED. Manifest tampering or incompatibility raises RESUME_DATASET_MANIFEST_MISMATCH.

DATASET_FINGERPRINT = Immutable and checked independently.
SEARCH_PLAN_FINGERPRINT = search_plan_hash covers search space, resolved safe plan, and minimum samples; mismatch raises RESUME_SEARCH_PLAN_MISMATCH.
CONFIG_FINGERPRINT = Authoritative trade-parameter config_hash; mismatch raises RESUME_CONFIG_MISMATCH. Engine schema incompatibility independently raises RESUME_ENGINE_INCOMPATIBLE.

CHECKPOINT_MANIFEST_HASH = Checkpoint persists dataset_manifest_hash, dataset_fingerprint, search_plan_hash, config_hash, engine_version, last durable result index, and durable result count.
STATUS_PROVENANCE = STATUS.json exposes manifest hash, dataset fingerprint, frozen cutoff, and frozen period; current structured failure fields remain authoritative for GUI/controller consumers.
REPORT_PROVENANCE = REPORT.md records frozen cutoff, historical period, manifest hash, and dataset fingerprint.

LIVE_DB_GROWTH_RESUME_TEST = PASS; regression appends a source row after checkpoint, existing run completes with identical manifest/fingerprint/counts, and a new run includes the added row with a new fingerprint.
COMBINED_WRITER_RESUME_TEST = PASS; three injected WinError 32 checkpoint replace failures recover automatically, source then grows, resume completes exactly once with 2/2 durable unique results and integrity PASS.
REAL_HISTORY_RESUME_SMOKE = PASS; Production PAPER read-only run block2-frozen-resume-smoke-20260907-03 pinned 6576 rows, stopped cleanly at 5/20, resumed 15 remaining configs, completed 20/20 with unchanged manifest and fingerprint, durable count 20, integrity PASS, mutations/config writes/approvals/commands/positions/Binance calls 0.

RESUME_FINGERPRINT_MISMATCH_AFTER = 0

Full 5000 configuration sweep was not run. LIVE remained disabled/unchanged.
