# ML38.10.60 — real quick-quality rerun readiness plan

## Why ML38.10.60 follows ML38.10.59

ML38.10.59 proved the fixed future writer contract only on a synthetic `tmp_path` fixture. The 45 existing real sidecar sets remain legacy/fail-closed, so ML38.10.60 supplies a no-run readiness plan for a separately approved real rerun without treating the fixture as real validation.

## Previous fixture validation summary

- Decision: `POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN` at commit `fbaed537e279e65e6377eec38b54105ddc34dc5a`.
- Exact written bytes matched summary SHA-256 and byte size; JSONL was LF-only.
- Schema `ml38.10.58`, all four writer contract fields, runtime truth, archive truth, and completion truth passed on the fixture.
- No newly generated exact-byte-valid real sidecar exists; full 6481 cascade/outcome remains blocked.

## No-run scope

This is a no-run readiness plan. During ML38.10.60 quick-quality was not run, training/runtime was not run, and no DB writes were performed. Only a future SOLUSDT 15m invocation is in scope; BTC, ETH, multi-symbol, cascade/outcome, production-like recompute, and tradable-edge claims are excluded. A separate approval is required before execution.

## Exact future command

Working directory: `D:\disk_E\game_projects\traders\traders-ml`

This future command was not executed during ML38.10.60 and requires separate user approval:

```text
python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT
```

Expected runtime may be multiple hours. Logs must stay outside the repository in `D:\disk_E\game_projects\traders\traders-ml-run-logs`. Expected output discovery pattern: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_*`.

## Execution runbook

After separate approval: require clean git status, activate the venv, create a timestamped external log directory, record start timestamps, and launch only the exact command. Retain the process handle, stream stdout/stderr to the external log, print elapsed time every 20 minutes, wait for completion, capture the real Python and controlling-shell exit codes, record end timestamps/duration/timeout state, and write an external completion marker. Do not commit runtime artifacts.

## Timeout and exit-code capture plan

No parent timeout may be shorter than the expected run. Python and controlling-shell exit codes must both be captured; timeout and late child completion must be explicit. A late completion cannot replace a lost exit code, zero cannot be fabricated, and an unknown exit code is fail-closed for production-like or tradable-edge claims.

## Post-run sidecar validation plan

Discover a new SOLUSDT output directory created after the recorded start, inventory new complete sidecar sets, and select the latest new set. Validate exact file SHA-256 and size against summary, LF-only JSONL, schema `ml38.10.58`, the four writer fields, expected row count (6481 or the declared full-dataset count), train/val/test splits, finite probabilities, and model-softmax argmax prediction source. Reject BTC, ETH, multi-symbol artifacts and any actual-label substitution.

## Metadata truth validation plan

Require `sidecar_runtime_truth`; verify requested/completed export truth, stream-created truth, quick-quality execution truth or explicit unknown, and completion/exit-code status. Unknown must not be represented as false. Stale wired/not-executed false/false metadata fails closed.

## Archive/ZIP validation plan

Require an archive status field. If a ZIP exists, validate that it contains the sidecars. If absent, status must truthfully be `MISSING`, `NOT_REQUESTED`, or `UNKNOWN`, with no false retention confirmation. A missing ZIP blocks archive validation but does not by itself invalidate exact sidecar bytes. Archive recovery is outside this stage.

## Label substitution guardrail

`predicted_label` must come from model probability argmax. Using `actual_label`, `ml_labels.direction_label`, or another target label as prediction source blocks acceptance.

## Real artifact guardrail

No existing real artifact was read for validation output or mutated. No new real sidecars or ZIP were created. No archive recovery, DB writes, `ml_labels` writes, or `ml_predictions` writes occurred. Labels, label builders, gates, and model logic are unchanged.

## Decision gate

Invalid exact bytes or stale/false metadata block cascade/outcome. Lost exit status blocks production-like and tradable-edge claims. Even a future newly generated exact-byte-valid sidecar with truthful metadata and validated exit status does not authorize cascade/outcome; that requires another separate stage.

The next allowed stage is **ML38.10.61 — separately approved real SOLUSDT quick-quality run using fixed writer contract**.

## Safety prohibitions

No clean, fast-debug, sequence wrapper, quick-quality, training/runtime, DB-mutating command, real sidecar generation, ZIP creation/recovery, label/gate/model change, or artifact cleanup was performed. `ml_labels` and `ml_predictions` were not written. Existing real artifacts were not mutated, and no new real sidecars or ZIP were created. Full 6481 cascade/outcome remains prohibited. This is not a production-like recompute and not tradable edge.

## Tests run

- `py_compile` for the ML38.10.60 diagnostic: passed.
- ML38.10.60 targeted tests: 6 passed.
- Regression-targeted ML38.10.59/58/57/56/53 tests: 37 passed.
- `TrainingService` direct import: passed (`TrainingService import OK: TrainingService`).
- `tests/test_class_weights.py --collect-only`: 1 test collected.
- Full pytest regression suite: 1088 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 87.35s.
- Wall time: 90.61s.
- External full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_60_20260707_061207.log`.

## Final decision

`REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN`
