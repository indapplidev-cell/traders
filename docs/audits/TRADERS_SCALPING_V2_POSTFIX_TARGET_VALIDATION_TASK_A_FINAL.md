# TRADERS_SCALPING_V2_POSTFIX_TARGET_VALIDATION — Task A

```text
TASK_STATUS = PASS_LIMITED
FINAL_VERDICT = POSTFIX_SAMPLE_LIMITED_BUT_NO_REGRESSION
DEPLOYMENT_CUTOFF = cycle > 1788962100000; final image started 2026-09-09T13:59:09.557590374Z
ANCHOR = LATEST_COMPLETED_5M_CYCLE 1788973200000 / completed 2026-09-09T17:01:17.385502Z / exact10 / config 1d0afbb4d1fb2cfb8afba03f718c28796a47e23b9d17c1f6e0109ace3d3717e7 / schema 0031_scalping_parameter_sets
POSTFIX_COHORT_COUNT = 63 production target/RR-evaluation rows; 52 exact collector-linked replay rows
MULTI_TARGET_OPPORTUNITY_COUNT = 62 production rows; 11 exact collector-linked replay rows
FARTHER_TARGET_EVALUATED_COUNT = 45 production rows; 10 exact collector-linked replay rows
FARTHER_TARGET_MISSED_COUNT = 0
OLD_ORDERING_DEFECT_REPRODUCED = NO
NEW_REGRESSION_FOUND = NO
POSTFIX_RR_INPUT_COUNT = 44 production rows; 10 exact collector-linked replay rows
POSTFIX_RR_PASS_COUNT = 0
TARGET_FIX_VALIDATED = PARTIAL_NO_REGRESSION_PATH_NOT_NATURALLY_EXERCISED
LIMITATION = no fresh farther target met unchanged Dynamic Required RR; legacy v2 outcome timing is contaminated and not used for acceptance
NEXT_TASK = TASK_B_NO_IMPULSE_UNKNOWN_REGIME
```

`TARGET_ORDERING_FIX_COMMIT` is
`305d793ca9c48a77d50a445ecd5c0e27dbb6d9f1`.  The final deployed source is
`a115cbcd5c7d796ccd9a0962b5d8296df617b0ae` in image
`sha256:222bf516ac402d311a3d339009a6430dafca4fffbe1a43bbda919a9bebea2f2b`.
The conservative cutoff excludes the 13:55Z boundary because it was not wholly
after the final container start; the first included boundary is 14:00Z.

The production SELECT-only cohort contains 212 ordered target considerations.
Forty-five opportunities retain a farther causal target and 43 retain targets
after the first actionable target.  All are directionally valid, future-safe,
and carry persisted source/timeframe/index data.  Regression counts are zero
for first-positive early stop, stale ordering, nearest-only fallback, wrong
direction, wrong timeframe, lookahead, duplicate evaluation, and index order.
The pre-fix miss count remains 59; the fresh post-fix miss count is zero.

The exact linked subset has Net RR count 10, median `0.719963545`, range
`0.61798094..1.13828442`; Dynamic Required RR count 10, median
`4.1101042744`, range `3.8605822756..4.6703746248`.  Zero RR passes is not a
selector failure.  The fixed late-Dynamic continuation branch is covered by a
focused deterministic test, but it was not naturally exercised in this fresh
sample, so the stronger `POSTFIX_TARGET_FIX_VALIDATED` verdict is deliberately
withheld.

Evidence: `artifacts/scalping_v2_postfix_setup_regime_01/TASK_A_REPORT.json`
and `TASK_A_POSTFIX_COHORT.jsonl`.  Safety remained PAPER-only, LIVE false,
commands/positions/order calls created by this audit zero.
