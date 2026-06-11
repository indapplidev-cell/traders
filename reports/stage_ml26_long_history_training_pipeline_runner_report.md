# Stage ML26 - Long-history Training Pipeline Runner

Stage ML26 completed.

## Goal

ML26 adds a long-history training pipeline runner that can be launched from the terminal without Codex. The main command is `train-quality-pipeline`, and each run now creates a dedicated runtime folder with a human-readable log, a JSONL event log, a JSON report, and a markdown report.

## Main command

```powershell
python -m app.cli.commands train-quality-pipeline --symbol BTCUSDT --interval 15m --start-date 2025-01-01
```

Dry-run example:

```powershell
python -m app.cli.commands train-quality-pipeline --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --dry-run
```

Sample mode example:

```powershell
python -m app.cli.commands train-quality-pipeline --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --sample-mode
```

## What was added

- long-history training pipeline runner
- training pipeline logger
- training pipeline reporter
- CLI command `train-quality-pipeline`
- deterministic `dry-run`
- deterministic sample mode
- runtime reports under `reports/training_pipeline_runs/<run_id>/`

## Pipeline stages

- `health_check`
- `db_check`
- `load_candles`
- `check_candle_gaps`
- `build_features`
- `build_labels`
- `build_dataset`
- `train_model`
- `probability_diagnostics`
- `baseline_compare`
- `calibration_diagnostics`
- `profit_aware_evaluation`
- `walk_forward_evaluation`
- `gate_policy_replay_evaluation`
- `model_quality_validation`
- `export_reports`

## Runtime logs and reports

For each run the pipeline creates:

- human-readable log: `reports/training_pipeline_runs/<run_id>/training_pipeline.log`
- JSONL event log: `reports/training_pipeline_runs/<run_id>/training_pipeline_events.jsonl`
- JSON report: `reports/training_pipeline_runs/<run_id>/training_pipeline_report.json`
- markdown report: `reports/training_pipeline_runs/<run_id>/training_pipeline_report.md`

The human-readable log is intended for operator review. The JSONL event log is intended for machine-readable event analysis and contains `pipeline_started`, `stage_started`, `stage_completed`, `stage_failed`, `pipeline_completed`, and `pipeline_failed` events.

## Dry-run and sample mode

`dry-run` does not perform a real candle load, does not run real training, does not require DB access, and does not write training outputs to the database. It still creates logs, JSONL events, a JSON report, a markdown report, and a quality summary.

Sample mode also avoids real long training and uses deterministic sample diagnostics. It exists for fast local validation and tests. Sample mode does not produce a real candidate approval and does not imply readiness for traders-core.

Observed dry-run verification result:

- `status`: `DRY_RUN_COMPLETED`
- `stage_count`: `16`
- `completed_stage_count`: `4`
- `failed_stage_count`: `0`
- `skipped_stage_count`: `12`
- `quality_status`: `NEEDS_MORE_DATA`

## Real mode intent

Real mode is intended for real long-history execution from the terminal. ML26 does not rewrite the training architecture. It reuses the existing project layers where safe and explicitly marks unavailable direct stages as skipped so the operator can see what still requires a real long-history run path.

## ML25 quality integration

The pipeline ends with the ML25 model quality validation layer. In dry-run and sample mode it uses deterministic sample diagnostics and returns `quality_status = NEEDS_MORE_DATA`. It does not emit a false `QUALITY_APPROVED`.

## Safety boundaries

- no auto activation
- no live trading
- no orders
- no traders-core integration
- no database migrations
- runtime artifacts are not committed

Dry-run and sample mode do not train a real production-ready model. Real mode is intended for real history only. Live, orders, and traders-core remain forbidden in ML26.

## Runtime artifact policy

Everything inside `reports/training_pipeline_runs/` is a runtime artifact and must not be committed. The stage report is committed:

- `reports/stage_ml26_long_history_training_pipeline_runner_report.md`

## Optional latest-summary command

`train-quality-pipeline-latest` was left as a future enhancement rather than implemented in ML26.

## Final validation

- Targeted ML26 tests passed:
  - `tests/test_training_pipeline_logger.py`
  - `tests/test_training_pipeline_runner.py`
  - `tests/test_training_pipeline_reporter.py`
  - `tests/test_training_pipeline_cli.py`
  - `tests/test_stage_ml26_training_pipeline_report.py`
- CLI dry-run check passed:
  - `python -m app.cli.commands train-quality-pipeline --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --dry-run`
  - runtime files created: `training_pipeline.log`, `training_pipeline_events.jsonl`, `training_pipeline_report.json`, `training_pipeline_report.md`
  - JSONL first/last events: `pipeline_started` / `pipeline_completed`
- `python -m py_compile` passed for the new logger, runner, reporter, CLI, and test files.
- Full `pytest` result: `288 passed, 1 warning`

## Next stage

ML27 - Real long-history training run and candidate model selection
