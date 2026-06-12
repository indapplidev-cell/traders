# Stage ML27 - Model Quality Improvement

Stage ML27 completed.

## Goal

ML27 extends the real long-history training pipeline with honest model-quality diagnostics instead of trying to force a false approval. The target was the latest `QUALITY_REJECTED` run, where the pipeline completed all 16 stages but still showed gaps, anti-collapse warnings, weak baseline edge, unstable walk-forward performance, and no safe research candidate.

## Why the previous model was rejected

The latest bad run for `BTCUSDT` / `15m` over `2025-01-01 -> 2026-06-12` produced:

- `79 gaps`
- `quality_status = QUALITY_REJECTED`
- strong directional bias toward `UP`
- low-confidence / low-margin predictions
- unstable walk-forward stability
- profit-aware results without a durable positive edge

The rejected model stayed:

- not connected to traders-core
- not used for live
- not used for orders
- not used for auto activation

## What ML27 added

- `app/diagnostics/gap_quality_diagnostics.py`
  - grades gap severity as `OK`, `MINOR`, `MODERATE`, `HIGH`, or `CRITICAL`
  - reports whether the dataset is safe for training
- `app/evaluation/anti_collapse_validator.py`
  - detects single-class collapse, directional bias, low-confidence uniform probabilities, and low-margin collapse
- `app/labels/label_quality_grid.py`
  - provides a reusable label grid plan for follow-up experiments
- `app/evaluation/model_candidate_selector.py`
  - adds a candidate selector that rejects or research-accepts candidates using explicit gates instead of raw accuracy only

## Pipeline extensions

`train-quality-pipeline` now carries additional ML27 sections in the quality report:

- `gap_quality_summary`
- `anti_collapse_summary`
- `candidate_selection_summary`
- `label_config_summary`
- `quality_gates_summary`

The markdown report now shows:

- why a model was accepted or rejected
- which gates failed
- what should be tried next

## CLI previews

Preview commands:

```powershell
python -m app.cli.commands model-anti-collapse-preview
python -m app.cli.commands model-candidate-select-preview
python -m app.cli.commands label-quality-grid-preview
```

Export commands:

```powershell
python -m app.cli.commands model-anti-collapse-export
python -m app.cli.commands model-candidate-select-export
python -m app.cli.commands label-quality-grid-export
```

These previews are deterministic and based on the latest bad-run profile, including directional bias and collapse signals.

## Real rerun

Run the real pipeline again with:

```powershell
python -m app.cli.commands train-quality-pipeline --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --run-id <run_id>
```

Then inspect the JSON report for the ML27 sections:

- `gap_quality`
- `anti_collapse`
- `candidate_selection`

## Safety

- no traders-core connection
- no live trading
- no orders
- no auto activation
- no database migrations
- no production deploy

ML27 is still research-only. It improves diagnostics, candidate selection, gaps analysis, directional bias detection, walk-forward stability interpretation, and profit-aware acceptance logic. It does not enable trading.

## Next stage

ML28 - run label grid experiments and compare candidates
