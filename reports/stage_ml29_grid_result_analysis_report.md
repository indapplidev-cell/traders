# Stage ML29 Grid Result Analysis Report

Stage ML29 completed.

ML29 adds an analyzer for completed label-grid experiments, a markdown/json reporter for candidate comparison, and a next experiment planner that converts repeated gate failures into a concrete follow-up plan.

The analyzer reads the latest or explicit experiment run from `reports/label_grid_experiments/<experiment_id>/label_grid_experiment_summary.json`, aggregates gate failures, compares candidate outcomes, extracts the best accepted or best rejected candidate, and summarizes collapse, profitability, walk-forward, and baseline-edge behavior.

The reporter writes:

- `label_grid_result_analysis.json`
- `label_grid_result_analysis.md`
- `next_label_experiment_plan.json`
- `next_label_experiment_plan.md`

The markdown report includes a candidate comparison table with rank, config, score, candidate status, quality status, accuracy edge, collapse type, profit factor, walk-forward profit factor, failed gates, and recommendation.

How to read results:

- start from `top_failed_gate`
- inspect which candidate is the best rejected or accepted candidate
- compare `accuracy_edge`, `collapse_type`, `profit_factor`, and `walk_forward_profit_factor`
- use `next_label_experiment_plan` to decide whether to change labels, features, gap handling, thresholds, or training configuration

How to run:

```powershell
python -m app.cli.commands label-grid-results-analyze --latest
```

```powershell
python -m app.cli.commands label-grid-results-analyze --experiment-dir reports\label_grid_experiments\<experiment_id>
```

Safety remains unchanged:

- no traders-core integration
- no live trading
- no orders
- no auto activation

The next stage is ML30: implement selected label/feature improvements.
