# TRADERS_PARAMETER_SWEEP_BLOCK1_WINDOWS_ARTIFACT_WRITER_FIX

BLOCK_1_STATUS = PASS
ROOT_CAUSE = The engine thread and heartbeat thread independently replaced STATUS.json through the same fixed STATUS.json.tmp path. Other JSON artifacts repeated the fixed-temp pattern. On Windows, competing replace/open activity can surface intermittent sharing/access failures and the wrapper treated them as fatal. RESULTS.jsonl and RESULTS.csv also had no single exactly-once owner.
FAILING_ARTIFACT = STATUS.json is the proven architectural race target; the original 20260907_204044_090 run directory is absent from this checkout, so the overwritten PermissionError traceback cannot be recovered.
FAILING_OPERATION = Fixed-temp write followed by os.replace; exact incident call site unavailable because ERROR.log history was overwritten/not retained in the available workspace.
WINERROR = Original value unavailable; explicit transient coverage now includes PermissionError and WinError 5/32/33.
WRITER_RACE = Main StatusStore updates and parameter-sweep-heartbeat both wrote STATUS.json via STATUS.json.tmp.
SINGLE_WRITER = DurableResultWriter is the sole owner of RESULTS.jsonl and derived RESULTS.csv persistence.
PER_FILE_LOCK = Process-wide canonical-path RLock serializes every target artifact.
UNIQUE_TEMP = .<target>.<pid>.<thread>.<uuid>.tmp in the target directory; handles are flushed, fsynced, and closed before os.replace.
RETRY_POLICY = Bounded immediate attempt plus 50/100/250/500/1000/2000 ms backoff for transient Windows filesystem errors; exhaustion returns path, operation, winerror, attempts, exception type, and message.
STATUS_SEMANTICS = Exhausted STATUS write is observational/nonfatal, retained as a structured warning, and retried by the next update/heartbeat.
CHECKPOINT_SEMANTICS = Exhausted checkpoint replacement raises CHECKPOINT_WRITE_FAILED; the previous checkpoint remains parseable and resume_available remains true. Checkpoint advances only after a durable result.
RESULT_EXACTLY_ONCE = Identity is run_id/result_index/config_hash. JSONL is the durable authority, ambiguous replace completion is reconciled by content, duplicate identity is idempotent, index conflicts fail closed, and CSV is atomically regenerated from JSONL. Integrity enforces unique identities and CHECKPOINT.evaluated_count == durable_result_count == JSONL count.
ERROR_HISTORY_PRESERVED = ERROR.log is append-only with timestamped sections and every failure also gets a uniquely named ERROR.<timestamp>.<pid>.<thread>.log snapshot.
FAULT_TESTS = PASS; status failures at 1 and 3 attempts, persistent status failure, checkpoint preservation on retry exhaustion, ambiguous replace completion, result JSONL/CSV recovery, and WinError 5/32/33 classifier are covered.
WRITER_STRESS = PASS; 500 concurrent serialized replacement cycles, valid final JSON, zero orphan temp files, zero manual continuation.
REAL_HISTORY_SMOKE = PASS; run block1-windows-writer-smoke-20260907 used Production PAPER DB through a read-only session, 6560 rows, 20/20 configs, 20 durable unique results, INTEGRITY PASS, fatal PermissionError 0, manual Continue 0, production mutations/config writes/approvals/commands/positions/Binance calls 0.
MANUAL_CONTINUE_REQUIRED = NO

## Writer inventory

| Artifact | Authoritative writer / owner | Frequency and concurrency |
|---|---|---|
| STATUS.json | StatusStore and heartbeat through ArtifactWriter | frequent; per-file serialized |
| CHECKPOINT.json | engine through ArtifactWriter | after each durable result and terminal transition |
| SEARCH_PLAN.json, PREFLIGHT.json, manifest/config JSON | engine through ArtifactWriter | lifecycle transitions |
| RUN_CONFIG.yaml | engine through ArtifactWriter | initial/final |
| RESULTS.jsonl, RESULTS.csv | DurableResultWriter | exactly once per result |
| RESULTS.json, TOP_CONFIGS.json, REJECTED_CONFIGS.json | finalizer through ArtifactWriter | finalization |
| REPORT.md | finalizer through ArtifactWriter | replace then serialized integrity append |
| INTEGRITY.json | integrity verifier through ArtifactWriter | verification |
| ERROR.log and ERROR.*.log | run wrapper through ArtifactWriter | append/snapshot per failure |
| .parameter_sweep.lock | SingleRunLock | once per process-run; exclusive creation and owner-checked removal |

## Evidence

- `python -m pytest tests/research/test_parameter_sweep_artifact_writer.py tests/research/test_scalping_v2_parameter_sweep.py -q` => 60 passed before the final three explicit checkpoint/temp-cleanup cases; the added writer suite then passed 13/13 (63 focused cases in total, with the shared 10 writer cases not double-counted).
- Production read-only smoke artifact: `artifacts/scalping_v2_parameter_sweep/block1-windows-writer-smoke-20260907/INTEGRITY.json` => PASS.
- Full 5000 configuration sweep was not run.
