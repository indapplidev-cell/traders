# Scalping v2 impulse threshold provenance — Task B final

TASK_STATUS = PASS
FINAL_VERDICT = TIMEFRAME_MISMATCH_AND_POLICY_MISMATCH_NO_WIRING_DEFECT
ABSOLUTE_THRESHOLD = 3.0_PERCENT
ATR_MULTIPLIER = 2.5
SOURCE_FILE = app/engine_analysis/impulse_phase_diagnostics.py:292
CONFIG_KEY = NONE_HARDCODED_GENERIC_DIAGNOSTIC
INTRODUCED_COMMIT = cca167e8c89feb8494c8d8c7af1f103ffd43e6f8
ORIGINAL_PROFILE = trade-15m-v1
ORIGINAL_TIMEFRAME = 15m
USED_BY_5M = YES
USED_BY_15M = YES_HISTORICAL_DISABLED_RUNTIME
USED_BY_OTHER_TF = NO_DIRECT_PRODUCTION_TRIGGER_1M_1H_4H_ARE_CONTEXT_ONLY
SETUP_FALLBACK_THRESHOLD = 0.25_PERCENT_PLUS_VOLATILITY_RATIO_0.9
THRESHOLD_RATIO = 12.0_AT_ABSOLUTE_FLOOR
CONTRACT_INTENT = IMPULSE_IS_GENERIC_RESEARCH_ANALYSIS_PHASE_SETUP_CANDIDATE_IS_SEPARATE_PROFILE_SPECIFIC_ACTIONABILITY
LEGACY_DRIFT_FOUND = YES
TIMEFRAME_MISMATCH_FOUND = YES
POLICY_MISMATCH_FOUND = YES
SOFTWARE_DEFECT_FOUND = NO_PROFILE_WIRING_EXECUTES_CODE_AS_WRITTEN
PRODUCTION_FIX_REQUIRED = NO_NOT_WITHOUT_VALIDATED_REPLACEMENT
NEXT_TASK = TASK_C_BOUNDED_VARIANTS

## Trace

The only effective definition is the hard-coded expression
`max(3.0, atr_pct * 2.5)` in `diagnose_impulse_phase`. There is no YAML key,
schema field, parameter-set override, resolver field, or runtime object for
either term. `build_analysis_quality_basis` passes the caller's timeframe and
the configured lookback to the generic diagnostic. The current 5m profile sets
an eight-bar lookback; the threshold itself remains unchanged.

The first traceable Git object is recovered-baseline commit
`cca167e8c89feb8494c8d8c7af1f103ffd43e6f8` (2026-07-17 22:10:39 +0300).
That commit introduced the file as a generic research-only analysis component,
while its orchestrator configuration accepted only `primary_timeframe=15m` and
the contemporaneous test invoked the diagnostic with `timeframe="15m"`.
Because this is a recovered baseline import, earlier authorship and economic
rationale are not present in available Git history. The strongest provable
origin is therefore 15m, generic impulse-phase research—not a calibrated
`trade-5m-v2` parameter.

Current production calls it for the active 5m primary analysis. The disabled
15m pipeline uses the same code when run. Although the function accepts an
arbitrary timeframe string, current orchestrators do not directly run it as a
primary diagnostic on 1m, 1h, or 4h; those frames supply context. Thus the
semantic concern is reuse from 15m into 5m without profile-specific calibration,
not evidence that all five timeframes actively execute the same threshold.

## Contract classification

`IMPULSE` means an eight-closed-bar generic analysis phase. A
`SETUP_CANDIDATE` means the 5m profile-specific setup layer found actionable
short-horizon momentum/structure. The code legitimately permits the latter
while the former is `NO_IMPULSE`; the contracts are distinct. However, the Set
#2 fallback admits `move>=0.25%` with volatility ratio `>=0.9`, while the
generic impulse floor requires `>=3%`. The 12x gap has no documented timeframe
or economic rationale, and Task A shows the larger floor dominates every row.
This is `LEGACY_THRESHOLD_DRIFT + TIMEFRAME_MISMATCH + POLICY_MISMATCH`, not a
runtime routing defect. Existing tests assert causality/serialization and a
15m call, but do not encode a threshold boundary or economic rationale; they
therefore did not prove 3% suitable for 5m.

Safety: no production code/config change, no deploy, authoritative Set #2 and
RR/probability/cost/risk policies unchanged, LIVE disabled, Binance order calls
zero.
