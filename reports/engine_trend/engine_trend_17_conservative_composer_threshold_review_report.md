# ENGINE-TREND-17 — Conservative Composer Threshold Review

## Stage goal
Review and minimally correct the conservative composer path without weakening UNKNOWN safety guards.
## Baseline
60/60 UNKNOWN; confidence 0.3; safety 60/60.
## Files created/changed
Composer ordering fix, replay runner, focused/offline tests, matrices, per-window artifacts, decision documents, manifest, and this report.
## Composer rule inventory
Documented in the dedicated rule review.
## Threshold candidate analysis
All 60 traces showed saturated UP=DOWN=1.0 and zero gap; one ordering correction was selected.
## Composer change
Raw additive scores are ranked before public-value clamp. Threshold constants are unchanged.
## After validation scope
The same 60 definitions were loaded from PostgreSQL in a read-only transaction.
## Before/after result summary
Windows: 60. Regimes: {'UP': 29, 'DOWN': 28, 'UNKNOWN': 3}. Statuses: {'MATCH': 25, 'MISMATCH': 11, 'NEEDS_REVIEW': 21, 'QUESTIONABLE_UNKNOWN': 3}. Improvements: {'IMPROVED': 25, 'REGRESSED': 11, 'NEEDS_REVIEW': 21, 'UNCHANGED_QUESTIONABLE': 3}. Safety violations: 0.
## Per-label summary
{'EXPECTED_DOWN': {'MATCH': 12}, 'EXPECTED_FLAT': {'MISMATCH': 10, 'QUESTIONABLE_UNKNOWN': 2}, 'EXPECTED_UNKNOWN_OR_MIXED': {'NEEDS_REVIEW': 15}, 'EXPECTED_UP': {'MATCH': 13, 'QUESTIONABLE_UNKNOWN': 1, 'MISMATCH': 1}, 'HIGH_VOLATILITY_CHOP': {'NEEDS_REVIEW': 3}, 'RECENT_BASELINE': {'NEEDS_REVIEW': 3}}
## Per-symbol summary
{'BTCUSDT': {'UP': 12, 'DOWN': 8}, 'ETHUSDT': {'UP': 8, 'DOWN': 9, 'UNKNOWN': 3}, 'SOLUSDT': {'UP': 9, 'DOWN': 11}}
## Safety contract verification
60/60 passed.
## Tests executed
Runner compiled successfully. The focused ENGINE-TREND-17 tests passed (10/10), the requested compatibility groups passed (37/37), and the combined relevant ENGINE-TREND suite passed (240/240). Full pytest was intentionally not used because the known unrelated diagnostics failure is outside this stage.
## Scans executed
Protected adapter, DB CLI, and composer diffs are empty after rollback. Changed-file scope contains only the runner, focused tests, and reports. Legacy scan found one pre-existing descriptive `BOOK-L1` reference in `engine_trend/__init__.py` and no legacy imports in new files. Write-SQL scan found no write statements. Trading scan found only safety/non-goal wording and existing safety enforcement. Artifact secret scan found no URL or credential material.
## Known limitations
Reference labels are descriptive, not ground truth. The set is fixed and not an independent holdout. Context remains 96 candles. This establishes neither predictive performance nor trading readiness.
## Decision
REJECTED.
## Next recommended stage
ENGINE-TREND-17B — Narrow Composer Decision Trace Expansion
