# ENGINE-TREND-17 — Composer Threshold Tuning Decision

## Baseline problem
All 60 fixed windows were UNKNOWN at confidence 0.3.
## Composer rules reviewed
Score, margin, coverage, conflict, fallback, range exception, and confidence clamp rules were reviewed.
## Candidate adjustment
Preserve raw additive candidate scores until ranking; clamp exported values afterward.
## Change implemented
One composer-only ordering fix; threshold values and evidence extraction are unchanged.
## Before/after validation summary
Windows: 60. Regimes: {'UP': 29, 'DOWN': 28, 'UNKNOWN': 3}. Statuses: {'MATCH': 25, 'MISMATCH': 11, 'NEEDS_REVIEW': 21, 'QUESTIONABLE_UNKNOWN': 3}. Improvements: {'IMPROVED': 25, 'REGRESSED': 11, 'NEEDS_REVIEW': 21, 'UNCHANGED_QUESTIONABLE': 3}. Safety violations: 0.
## Improvement summary
25 questionable UNKNOWN rows became direct matches.
## Regression summary
MISMATCH count: 11; NEEDS_REVIEW count: 21.
## Safety verification
60/60 preserved NOT_EVALUATED / false / false.
## Decision
REJECTED: One or more acceptance gates failed; composer change must be reverted.
## What this does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no model training performed
## Next recommended stage
ENGINE-TREND-17B — Narrow Composer Decision Trace Expansion
