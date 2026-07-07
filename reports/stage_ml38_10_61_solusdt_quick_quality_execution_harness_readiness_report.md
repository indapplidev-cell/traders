# ML38.10.61 — SOLUSDT quick-quality execution harness readiness

## Why ML38.10.61 follows ML38.10.60

ML38.10.60 produced a no-run readiness plan and prepared one future command without executing it. The user selected Variant A, the no-run path, so ML38.10.61 converts that plan into a guarded no-run harness while preserving the separate execution approval boundary. This stage does not perform the real run.

## Wrapper file

Root-level `run_solusdt_quick_quality_once.py` is the only execution entry point added by this stage. Its default mode is dry-run/plan. Real execution requires both `--execute` and `--i-understand-this-runs-real-quick-quality`; neither flag was used in ML38.10.61.

## Exact future command

The wrapper fixes this single allowed logical command, with no command, symbol, or passthrough arguments:

```text
python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT
```

It is restricted to SOLUSDT 15m. The wrapper uses the current Python environment's `sys.executable` to launch the fixed script arguments after separate approval.

## Dry-run behavior

`python run_solusdt_quick_quality_once.py` only prints the exact future command, repository cwd, external log and completion-marker path templates, and safety constraints. It does not inspect git, spawn a subprocess, create logs, run training/runtime, or create runtime artifacts. It prints `REAL QUICK-QUALITY WAS NOT RUN`. The permitted dry-run validation confirmed this behavior; quick-quality was not run.

## Execute-mode safety

Execute mode is gated by two explicit flags and was not used in this stage. Before a child or log is created it requires clean `git status --porcelain`. There is no short parent timeout. The parent retains the process handle, streams output, emits elapsed progress every 20 minutes, waits for completion, and records start/end timestamps. A separate approval is required for execute.

## External logging contract

Timestamped combined stdout/stderr logs and completion marker JSON are written only below `D:\disk_E\game_projects\traders\traders-ml-run-logs`. The dry-run prints templates but creates neither file. No execution log or completion marker is written in `reports/`.

## Exit-code contract

On execute, the wrapper captures the actual Python child exit code and returns that code. It does not synthesize a zero or use a short timeout that could lose child completion status. An unknown exit code fails closed and is represented as unknown in the completion marker, never as successful.

## Command scope guardrails

Only the fixed SOLUSDT quick-quality argv is constructed. BTC, ETH, multi-symbol, clean, fast-debug, sequence, cascade/outcome, and user-supplied command injection are unavailable. No custom symbol or command option exists.

## Real artifact guardrails

Quick-quality and training/runtime were not executed. No DB writes, `ml_labels` writes, or `ml_predictions` writes occurred. Existing real artifacts were not mutated; no real sidecar or ZIP was created; no archive recovery was performed. Labels, label builders, gates, and model logic are unchanged. Full 6481 cascade/outcome remains prohibited. This is not a production-like recompute and does not confirm tradable edge.

## Safety prohibitions

No execute flags, quick-quality, clean, fast-debug, sequence, cascade/outcome, training/runtime, DB-mutating command, artifact cleanup, sidecar generation, ZIP creation, or archive recovery is permitted in this stage. A later execution remains limited to SOLUSDT 15m and requires separate approval.

## Tests run

- `py_compile` for the wrapper and ML38.10.61 diagnostic: passed.
- Wrapper default dry-run: passed; it printed the exact command, external path templates, safety constraints, and `REAL QUICK-QUALITY WAS NOT RUN`.
- ML38.10.61 targeted tests: 8 passed.
- ML38.10.60/59/58 regression-targeted tests: 16 passed.
- `TrainingService` import: passed (`TrainingService import OK: TrainingService`).
- `tests/test_class_weights.py --collect-only`: 1 test collected.
- Full pytest regression suite: 1096 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 97.94s.
- Wall time: 101.30s.
- External full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_61_20260707_064328.log`.

## Final decision

`SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN`

The next allowed stage is **ML38.10.62 — separately approved real SOLUSDT quick-quality execution using wrapper**.
