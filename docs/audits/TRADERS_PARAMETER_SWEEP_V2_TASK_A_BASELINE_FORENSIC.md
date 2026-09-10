# Parameter Sweep v2 — Block A baseline forensic

TASK_STATUS = PASS
CURRENT_SCHEMA_VERSION = V1_LEGACY
CURRENT_TOTAL_SIZE = 1157485547_BYTES
CURRENT_RESULTS_JSONL_SIZE = 1085211667_BYTES
CURRENT_DATASET_SIZE = 70895354_BYTES
DOMINANT_DUPLICATED_FIELDS = validation/calibration/holdout.trades[].market_path_1m
MARKET_PATH_DUPLICATION_SHARE = 87.937_PERCENT_ON_FIRST_50_REPRESENTATIVE_ROWS
RESUME_MODEL = CHECKPOINT_PLUS_FROZEN_DATASET_MANIFEST_AND_EXACTLY_ONCE_RESULT_INDEX
DETERMINISM_MODEL = SEEDED_LAZY_MIXED_RADIX_WALK_PLUS_CONFIG_HASH

Representative source: `artifacts/scalping_v2_parameter_sweep/20260907_235854_595`.
The existing run contains 1,277 result rows. It was inspected without rerunning
5,000 configurations. The module inventory is:

- entry points: `traders_ml.parameter_sweep.__main__`, CLI and Tk thin client;
- orchestration/evaluation: `engine.py`, production formula reuse in
  `historical_replay.py` and `app.engine_paper.stale_position_shadow`;
- frozen input: `dataset.py`, `DATASET_MANIFEST.json`, `DATASET_SNAPSHOT.json`;
- durability: `artifact_writer.py`, `checkpoint.py`, `state.py`, `locking.py`;
- ranking/reporting: `_aggregate_results`, `TOP_CONFIGS.json`, `REPORT.md`;
- validation/readers: `integrity.py`; legacy output had no explicit schema-v2
  adapter before this task.

The legacy run artifacts and roles were recorded as follows:

| Artifact | Role | Resume required | Human-facing | Heavy duplication |
|---|---|---:|---:|---:|
| RESULTS.jsonl / RESULTS.json | complete config results | yes / no | no | yes |
| RESULTS.csv | summary | no | yes | no |
| DATASET_SNAPSHOT.json | immutable replay data | yes | no | shared fixed cost |
| DATASET_MANIFEST.json | dataset identity/watermarks | yes | yes | no |
| CHECKPOINT.json | exactly-once resume cursor | yes | yes | no |
| TOP_CONFIGS.json | ranking | no | yes | inherited full rows |
| REJECTED_CONFIGS.json | rejected results | no | yes | inherited full rows |
| REPORT.md | operator report | no | yes | no |

Baseline hashes at forensic capture:

- engine revision: `cdd514d78f48812a7508cb61912df492af6ff053`;
- authoritative research YAML blob: `4966b171d151574f0488002961d5cbc3cf024b9f`;
- representative dataset manifest: `48c68c595596d3247cc34c29b4c25adba2dd06a832959748f25cd2580915c90e`;
- representative dataset fingerprint: `7235d52b13af65583117464660d0f1eb2691e4fd5046e292a494d1252e298b55`;
- legacy result schema: implicit v1 (no `artifact_schema_version`).

