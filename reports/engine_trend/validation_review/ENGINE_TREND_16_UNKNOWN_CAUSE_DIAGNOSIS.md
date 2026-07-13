# ENGINE-TREND-16 — UNKNOWN Cause Diagnosis

## Input evidence
Reviewed 60 saved result artifacts: 15 from ENGINE-TREND-15 and 45 from ENGINE-TREND-15B. No database or engine execution was used.

## Observed pattern
UNKNOWN occurs in 60/60 windows; confidence equals 0.3 in 60/60. QUESTIONABLE_UNKNOWN occurs in 39 windows and MISMATCH in 0.

## Trace field availability
Decision status, matrix coverage, and candidate scores are complete for 60/60 windows. Fields unavailable in at least one saved artifact: {"confidence_after_conflict": 60, "confidence_after_coverage": 60, "symbol_role": 15}. Null values are retained rather than inferred.

## Reason code evidence
Saved book evidence contains 23618 reason-code occurrences. Directional evidence is therefore created; watched-code counts are in the reason-code summary. Empty directional evidence occurs in 0 windows.

## Matrix coverage and conflict
Coverage: {'HIGH': 60}. Conflict: {'NONE': 48, 'MEDIUM': 10, 'LOW': 2}. This does not support low coverage or high conflict as the universal blocker.

## Candidate score behavior
The top-two candidate gap is at most 0.1 in 60/60 windows. Composer fallback status occurs in 60/60 windows. This locates the observed block at the conservative composer decision path, commonly with tied or near-tied candidates.

## Confidence behavior
Confidence decomposition exists in 60/60 artifacts. Final 0.3 differs from decomposition total in 58 windows, consistent with fallback confidence assignment or clamp; the trace does not expose intermediate confidence-after-conflict/coverage fields.

## Suspected primary cause
B — conservative evidence/composer decision path. Evidence reaches a ready matrix, but candidate separation is often insufficient and the safety fallback selects UNKNOWN.

## Alternative explanations
D — insufficient context length remains possible because all reviewed windows contain 96 candles. A (symbol/window noise) is weakened by the three-symbol design and suitability results. C (validation diversity) remains a limitation but does not explain identical behavior across 60 varied windows. E is not primary because the decisive matrix and candidate fields are present, although intermediate confidence fields are missing.

## What cannot be concluded yet
This review cannot establish how 192/384-candle contexts behave, whether a threshold change is safe, or any predictive or runtime suitability.

## Required next evidence
The selected next stage is **ENGINE-TREND-17 — Conservative Composer Threshold Review**. It must preserve the current baseline, define before/after acceptance metrics, and keep context-length sensitivity as an explicit secondary check.
