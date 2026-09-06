# Scalping v2 Parameter Sweep

Parameter Sweep is an offline, read-only research tool. From the project root,
run it with one command:

```powershell
python -m app.research.scalping_v2_parameter_sweep `
  --config config/research/scalping_v2_parameter_sweep.yaml `
  --run-id <manual-run-id>
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

The default dataset is bounded to the newest 5,000 closed `trade-5m-v2` PAPER
positions. Use `--max-rows` to lower that ceiling and `--from` / `--to` with UTC
ISO-8601 timestamps to narrow the period. `--max-configs` bounds the search
space; `--preflight-only` stops after safe database and dataset validation.

Each new run ID creates `RUN_CONFIG.yaml`, `PREFLIGHT.json`, `RESULTS.csv`,
`RESULTS.json`, `TOP_CONFIGS.json`, `REJECTED_CONFIGS.json`, and `REPORT.md`
under `artifacts/scalping_v2_parameter_sweep/<run-id>/`. Existing run IDs are
never overwritten. Expected failures print a short `REASON` code without a
credential-bearing traceback.

Running a sweep does not promote a configuration, change production trading
parameters, call Binance order APIs, or enable LIVE.
