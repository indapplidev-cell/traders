# Stage ML28 Label Grid Experiments Report

Stage ML28 completed.

ML27 still rejected the latest real model because the pipeline reported `QUALITY_REJECTED`, mixed collapse, weak edge over baseline, negative profit-aware behavior, unstable walk-forward behavior, and gap-sensitive data quality.

ML28 adds a label grid experiments runner for research-only candidate comparison. It reuses the existing training and diagnostics stack, runs multiple label configs from `app/labels/label_quality_grid.py`, stores per-experiment runtime outputs in `reports/label_grid_experiments/<experiment_id>/`, writes a human log and JSONL events, exports candidate JSON/Markdown files, and builds a final summary with candidate ranking.

Candidates are trained and evaluated through the existing pipeline chain: build labels, build dataset, train model, probability diagnostics, baseline comparison, profit-aware evaluation, walk-forward evaluation, gate-policy replay evaluation, model quality validation, and candidate selection. The current gate-policy replay path remains sample-backed in the existing training pipeline, so ML28 reports that honestly instead of treating it as a new live/runtime integration.

Candidate ranking is not based on raw accuracy alone. The score blends accuracy edge, anti-collapse outcome, profit factor, total R, walk-forward total R, walk-forward profit factor, gap quality penalties, and failed gate penalties. If every candidate is rejected, ML28 still reports the best rejected candidate and marks the experiment as `COMPLETED_NO_ACCEPTED_CANDIDATE`.

Per experiment, ML28 creates:

- `label_grid_experiment.log`
- `label_grid_experiment_events.jsonl`
- `label_grid_experiment_summary.json`
- `label_grid_experiment_summary.md`
- `candidate_results/<config_id>.json`
- `candidate_results/<config_id>.md`

How to run preview:

```powershell
python -m app.cli.commands label-grid-experiment-preview
```

How to run dry-run:

```powershell
python -m app.cli.commands label-grid-experiment-run --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --dry-run
```

How to run sample-mode:

```powershell
python -m app.cli.commands label-grid-experiment-run --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --sample-mode
```

How to run a real limited grid:

```powershell
python -m app.cli.commands label-grid-experiment-run --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --max-configs 2
```

Safety boundaries remain unchanged:

- no traders-core integration
- no live trading
- no orders
- no auto activation
- no production deploy

The runner does not connect `traders-core`, does not change the public `/predict` API, does not enable live execution, and does not switch active models automatically. Research candidates remain offline artifacts only.

Next stage: ML29 - analyze grid results and refine best label/feature config.
