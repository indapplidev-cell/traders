# Scalping v2 Parameter Sweep

## Result-driven refactor: block 01 internal foundation

The existing GUI and research modes below remain legacy workflows. They do not
implement the result-driven search acceptance. The new shared
`ResultSearchService` currently prepares typed requests and guards durable result
publication; it does not yet schedule simulations. Its controller adapter and CLI
use the same request parser. GUI controls will be integrated in block 06.

Checkout deployment uses `D:\disk_E\game_projects\traders\traders-ml` and
`C:\Program Files\Python311\python.exe`. Inspect the loaded version in a fresh
process:

```powershell
python -m traders_ml.parameter_sweep --result-search-diagnostics
python -m traders_ml.parameter_sweep --result-search-request request.json --result-search-dataset-hash <sha256> --output-root artifacts/result_search
python -m traders_ml.parameter_sweep --result-search-request request.json --result-search-dataset-hash <sha256> --result-search-resume artifacts/result_search/<run-id>
```

Preparation returns `PREPARED`, never a search success. Requests specify UTC
start/end/cutoff, symbols and scope, capital, baseline hash, parameter domains,
constraints, seed, finite trial/time/artifact/storage budgets and data/execution
modes. The default target is one verified configuration with at least one valid
closed trade whose net PnL after costs is positive. Statistical certification is
separate. Open trades, PATH_END, positive gross with negative net and unverified
historical PnL do not qualify. Full simulation and YAML export are not installed
by this foundation block.

Block 02 adds bounded read-only candle/snapshot acquisition, independent of old
PAPER positions, with checksums, coverage and causal closed-candle windows:

```powershell
python -m traders_ml.parameter_sweep --result-search-request request.json --result-search-freeze-history artifacts/result_search/new_dataset
```

The directory must not exist. A `BLOCKED_DATA` manifest returns exit code 2 and
preserves the acquired evidence. Missing historical costs/depth are not replaced
with live values or silently certified. Default warmup is 200 candles per
timeframe and exit tail is one hour, bounded by the request cutoff. These are
acquisition defaults; engine-specific warmup/lifecycle certification is still
required. Reload with `HistoryProvider.load(Path(...))` verifies both content and
manifest fingerprints. No replay command is available until block 03.

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

## Combination-specific historical applicability

History schema 3 separates candle coverage blockers from conditional cost-input
requirements. Missing cost snapshots or raw depth do not reject the entire dataset.
Use the frozen dataset with retained risk decisions and frozen parameter values:

```powershell
python -m traders_ml.parameter_sweep.history_applicability --dataset artifacts/result_search_applicability_01/dataset --combinations artifacts/result_search_applicability_01/combinations.json --output artifacts/result_search_applicability_01/new_assessment.json
```

The output must not exist. This is an admission-prefix assessment using the actual
ScalpingPaperRunner, not a full trade simulator. Supported overrides are
geometry.stop_max_bps, geometry.minimum_planned_rr and economics.min_net_edge_bps.
Upstream decisions and all other parameters stay frozen per historical baseline.
NOT_REQUIRED means the authoritative evaluator rejected before requesting costs.
VERIFIED_SAME_INPUT_SNAPSHOT requires matching symbol, boundary, entry, reference
quantity/notional, policy, source and causal receipt timing. Missing inputs block
only the combinations that demand them. Reaching probability returns
HISTORICAL_PROBABILITY_HIERARCHY_REQUIRED; empty statistics are not a proven rejection.
No PnL, portfolio acceptance, configuration export or LIVE readiness is certified.

## Historical statistics continuation

Freeze the actual production statistical sources without production writes:

```powershell
python -m traders_ml.parameter_sweep.historical_statistics --source reports/calibration/scalping-v2-probability-set2 --parameter-set-id scalping-v2-set-2 --output artifacts/result_search_applicability_01/new_statistics.json
python -m traders_ml.parameter_sweep.history_applicability --dataset artifacts/result_search_applicability_01/dataset --combinations artifacts/result_search_applicability_01/combinations.json --statistics artifacts/result_search_applicability_01/new_statistics.json --output artifacts/result_search_applicability_01/new_statistics_assessment.json
```

Outputs must not exist. Outcomes are frozen with fingerprints and source checksums;
future and undated outcomes are excluded before the production hierarchy builder.
Statistics are cached immutably per assessment, with fresh per-boundary trace.
Historical statistics schema 2 validates completed_at against the recorded closed
candle path, excludes missing/gapped/future evidence, and records exclusion counts.
Its HISTORICAL_VERIFIED scope is causal event-time statistics, not an exact copy of
the production reader filesystem at each instant. The latter is not required for
this historical simulation contract. No statistical threshold, commission, risk
or production configuration is relaxed. An admission rejection is not a trade.

HistoryProvider.freeze accepts statistics_source/parameter_set_id and an optional
independent_interval. The bundled statistics checksum participates in dataset
identity. HistoryProvider.partition exposes warmup, search, exit_tail,
independent_evaluation and independent_exit_tail. search_view deliberately excludes
exit and independent intervals before range generation. Each decision must use
causal_window with its own cutoff. The configured 200-bar warmup exceeds the current
shared orchestrator minimum windows; insufficient warmup is rejected.

Fresh installed history acceptance:
`python -m scripts.result_search_history_acceptance --output artifacts/block02_new_acceptance`
Full trade simulation, optimization and result exports remain subsequent blocks.

## Chronological simulator (block 03)

The internal headless trial now uses the shared PipelineRunner from frozen candles,
then the shared selector, quantity, portfolio, fill-price/fee and exit calculations.
Use `python -m traders_ml.parameter_sweep.chronological_search --dataset <frozen-dir> --overrides <json-file> --capital 100 --output <new-json-file>`.
This runs a trial, not an optimization campaign. FOUND publication is reserved for
the later verifier. A complete baseline with zero trades is a valid simulation,
not a successful search. Required unavailable inputs produce BLOCKED_DATA.

Nine active keys cover signal/setup, regime, confirmation, geometry and economics.
Other overrides are rejected as unsupported consumers. Explicit execution
assumptions produce ASSUMPTION_BASED results. The simulation preserves the
production expiry/next-closed-minute contract and SHADOW timeout semantics.
A 30-second entry validity does not survive a fill requiring the minute close.
Open tails are incomplete, not PATH_END wins. Research opportunity state is in
memory and never loads or persists the production file.
