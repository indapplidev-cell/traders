# Scalping v2 Parameter Sweep

Parameter Sweep is an offline, read-only research tool implemented by the
authoritative `traders_ml/parameter_sweep/` package. The GUI and CLI are thin
front ends over the same headless engine.

Open the Russian Windows GUI from the project root:

```powershell
python -m traders_ml.parameter_sweep
```

Run the native CLI explicitly:

```powershell
python -m traders_ml.parameter_sweep `
  --config config/research/research_parameters.yaml `
  --run-id <manual-run-id>
```

The historical entrypoint is retained as a delegating compatibility shim:

```powershell
python -m app.research.scalping_v2_parameter_sweep `
  --config config/research/scalping_v2_parameter_sweep.yaml `
  --run-id <manual-run-id>
```

Inspect a run without attaching to it:

```powershell
python -m traders_ml.parameter_sweep --status <run-id>
```

The normal operator path resolves the existing protected project database
binding automatically. Do not export `DATABASE_URL`, copy a password, inspect
Docker secrets, or edit Python. `--database-url` exists only as an explicit
dev/test/admin override; `DATABASE_URL` remains a compatibility fallback after
the protected binding.

The PostgreSQL session is forced read-only, the research adapter accepts only
SELECT-oriented statements, and preflight verifies that INSERT, UPDATE, DELETE,
and DDL are rejected. No credential is written to the research YAML, artifacts,
console, Git, or image.

The default dataset is bounded to 10,000 current `trade-5m-v2` PAPER
opportunities/positions. Use `--max-rows` to lower that ceiling and `--from` / `--to` with UTC
ISO-8601 timestamps to narrow the period. The default `targeted` planner
calculates raw cardinality without enumerating the Cartesian product. It runs
Set #2 baseline, one-factor sensitivity, small-family search, top-region
refinement and local finalist validation. The targeted phase is capped at 500
configurations in YAML and uses batches of 25. Economics, costs, risk/safety and
lifecycle-shadow remain frozen. `--stage STAGE_NAME` runs one stage;
`--max-configs` may lower the automatic budget for a smoke;
`--preflight-only` stops after safe database, dataset, search, and memory-plan
validation.

Every run evaluates the current production baseline from
`config/trading/trade_parameters.yaml` before any sampled configuration. Closed
trade outcomes are reported separately from causal admission and time-stop
replay. Timestamped time-stop evidence is read directly from
`scalping_stale_position_shadow_diagnostics`; missing market or historical cost
timelines are never replaced with current values. If the baseline cannot replay,
or no row can support a searched causal dimension, the run ends with an exact
`BASELINE_REPLAY_INVALID` or `NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS` reason
before mass evaluation.

Known-invalid conditional combinations are omitted by the generator. In
particular, `soft_timeout_seconds >= hard_timeout_seconds` is never emitted;
disabled extension and break-even children collapse to one canonical value.
Each evaluated configuration records an exact gate funnel rather than the
opaque `ALL_TRADES_FILTERED` label.

The GUI creates a local-time, sortable `YYYYMMDD_HHMMSS_mmm` run ID with a
collision check. Each new run creates `RUN_CONFIG.yaml`, `PREFLIGHT.json`, `SEARCH_PLAN.json`,
`RUN_MANIFEST.json`, `DATASET_MANIFEST.json`, `CHECKPOINT.json`, `RESULTS.csv`,
compact `RESULTS.jsonl`, `ACCEPTED_CONFIGS.jsonl`, `REJECTED_CONFIGS.jsonl`,
`TOP_CONFIGS.json`, bounded `FINALIST_TRADES.jsonl`, `ARTIFACT_SIZES.json`,
`REPORT.md`, `STATUS.json`, and `INTEGRITY.json`
under `artifacts/scalping_v2_parameter_sweep/<run-id>/`. Existing run IDs are
never overwritten. Use `--resume` only for a compatible interrupted run;
dataset, research config, search space, artifact schema, engine compatibility
and baseline fingerprints are checked separately. Results
and checkpoints are durable incrementally, while TOP/Pareto aggregation is
disk-backed. Expected failures print a short `REASON` code without a
credential-bearing traceback.

The primary stop action is graceful: finish the current configuration, fsync
its result, atomically checkpoint, and stop before the next configuration.
`STATUS.json` is written atomically and refreshed by a five-second heartbeat.
The status command reports stale/dead `RUNNING` states as `INTERRUPTED` instead
of trusting them indefinitely. A project-local lock rejects a second live run
and safely replaces a stale lock whose process no longer exists.

Completion is published only after content-aware integrity validation checks
required files, JSON/YAML parsing, run/config/dataset identities, and durable
result counts. A failed integrity check leaves the run non-completed.

## GUI parameter and replay semantics

The GUI deliberately separates two concepts:

- **Параметры исследования** lists the dimensions and values published by the
  engine's typed search plan, including conditional dimensions, raw search
  space, planned evaluations, and strategy.
- **Текущая комбинация** exists only after `CONFIG_STARTED`. Before then it says
  `Комбинация ещё не запущена`; it never renders an empty JSON object, and the
  all/changed-parameter toggle is disabled. Once a configuration exists, the
  default view contains values that differ from the production baseline; the
  toggle reveals the full resolved configuration.

Active runs use future wording (`Будет исследовано`). Terminal runs use factual
wording (`Запланировано` and `Фактически обработано`). Progress always reports
`Обработано N из F`; there is no synthetic "configuration 0". A terminal state
retains the last real configuration when one existed.

If planning succeeds but replay validation fails before configuration 1, the
run persists `state=FAILED`, `phase=REPLAY_VALIDATION`,
`current_config_index=null`, and `resume_available=false`. The GUI explicitly
states that no configuration was processed and that new historical observations
are required. `--status` reads the same model and prints the planned count,
actual completed count, `CURRENT_CONFIG = NONE`, and structured failure code.

The **Диагностика replay** panel is sourced from engine state—not YAML, the
database, or artifacts read by the GUI—and distinguishes:

- `OUTCOME_REPLAY`: repeated evaluation from closed PAPER trade outcomes;
- `TIME_STOP_REPLAY`: causal time-stop evaluation with timestamped market and
  historical cost observations;
- `FULL_CAUSAL_REPLAY`: complete outcome, admission, market, and cost evidence.

It also shows dataset rows, post-instrumentation rows, and missing market/cost
timeline counts. Failed-before-evaluation integrity uses its own artifact
contract and does not misclassify absent full result files as corruption.

Run artifacts include a dataset fingerprint and row/time boundaries, full field
coverage, baseline metrics, replayable/partial/unreplayable counts, and start,
finish, and duration values. Invalid or unreplayable configurations cannot enter
TOP or Pareto results.

When a large hypothesis space meets a small dataset, the report emits
`LARGE_HYPOTHESIS_SPACE_SMALL_SAMPLE` and sets promotion eligibility to `NO`.
Holdout is evaluation-only and cannot affect sampling, refinement, ranking, or
stage selection.

Running a sweep does not promote a configuration, change production trading
parameters, call Binance order APIs, or enable LIVE.

## Artifact schema v2 and migration

Every `RESULTS.jsonl` row has `artifact_schema_version: 2`, compact overrides,
evaluation status, an independent performance class, required metrics,
rejection distribution, cost source, dataset-manifest reference and finalist
trade reference. Full candles, snapshots, YAML documents, opportunities, trade
arrays and `market_path_1m` are forbidden in result rows. Detailed trades are
written only for the YAML-bounded finalist subset and use a hash-checked
`market_path_ref` into the immutable frozen dataset.

The finalizer reports total/results/finalist/dataset bytes. YAML budgets are
120 MiB soft and 200 MiB hard for the run, and 50/100 MiB for RESULTS. Crossing
a hard limit fails with `ARTIFACT_SIZE_BUDGET_EXCEEDED`.

Legacy v1 rows remain readable through the adapter. Non-destructive migration
supports dry-run and atomic target-directory publication:

```powershell
python -m traders_ml.parameter_sweep --migrate-v1 <old-run-dir> --dry-run
python -m traders_ml.parameter_sweep --migrate-v1 <old-run-dir> --migration-target <new-v2-dir>
```

The source directory is never rewritten. Set #2 remains the immutable baseline;
an evidence-backed Set #3 may only be emitted as a research candidate file and
is never activated by Parameter Sweep.
