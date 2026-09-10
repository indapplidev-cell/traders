# Parameter Sweep v2 — Block G bounded acceptance

TASK_STATUS = PASS_TOOLING_NO_CANDIDATE
SMOKE_CONFIGS = 10_INTEGRITY_PASS
TARGETED_CONFIGS = 144_OF_144_INTEGRITY_PASS
BASELINE_INCLUDED = YES_SET2_FIRST
BEST_PERFORMANCE_CLASS = INSUFFICIENT_SAMPLE
SET3_CANDIDATE_CREATED = NO
PRODUCTION_CONFIG_CHANGED = NO

ACTUAL_ARTIFACT_SIZE = 111028543_BYTES_INCLUDING_109999189_BYTE_FROZEN_DATASET
BYTES_PER_CONFIG = 1547.014_RESULTS_JSONL
PROJECTED_5K_SIZE = 118540843_BYTES_113.05_MIB
SIZE_BUDGET_PASS = YES_SOFT_AND_HARD

LIVE = FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

Evidence run:
`artifacts/scalping_v2_parameter_sweep/parameter-sweep-v2-targeted-final-20260910`.
Frozen dataset fingerprint:
`83bed0d86a34b45411a23f9b8533ac8a000f41a3a66c3ef01f0dcdc38b66cd3e`;
cutoff `2026-09-10T20:20:00+00:00`; 10,000 opportunity rows, 5,461
outcome/time-stop/full replay eligible rows, 137,340 historical market rows.

Stage counts were baseline 1, one-factor sensitivity 10, small-family 60,
top-region refinement 40 and local-finalist validation 33. All 144 evaluations
completed deterministically; none met the validation minimum. Set #2 baseline
control replayed 98 trades, while the chronological validation slice produced no
eligible candidate under unchanged economics/safety gates. Therefore the correct
research outcome is `NO_CANDIDATE`; no Set #3 artifact was created.

`RESULTS.jsonl` is 222,770 bytes and contains zero inline market paths. The
artifact integrity gate passed all schema, identity, checkpoint, fingerprint and
count checks.

