# ENGINE-TREND-24 Scoring Redesign + Setup Viability Filter

## Decision

**ENGINE_TREND_24_COMPLETED_V2_FILTER_NEGATIVE**

Infrastructure Gate A: PASS. Research promising Gate B: FAIL. Paper-trading Gate C: FAIL.

## Candidate accounting

- processed: 449
- filter PASS/FAIL: 125 / 324
- train/design: 327 candidates; PASS 88
- out-of-time validation: 122 candidates; PASS 37

## Performance (net of the frozen 24 bps cost model)

- train PASS: n=88, clean=87, winrate=28.7356%, avg/expectancy=-0.1859%, PF=0.5975, max loss streak=15, naive max DD=22.8475%
- validation PASS: n=37, clean=37, winrate=45.9459%, avg/expectancy=-0.0376%, PF=0.9088, max loss streak=6, naive max DD=7.2965%
- full PASS diagnostic: n=125, clean=124, winrate=33.8710%, avg/expectancy=-0.1420%, PF=0.6824, max loss streak=15, naive max DD=26.8684%
- full baseline: n=449, clean=444, winrate=32.2072%, avg/expectancy=-0.1895%, PF=0.5567, max loss streak=13, naive max DD=87.4799%

## Ranking diagnostic

- old score vs net / win: -0.0082 / -0.0538
- score_v2 vs net / win: 0.0258 / 0.0335
- winners/losers mean score_v2: 64.7000 / 63.4990
- old top-10: n=10, clean=10, winrate=20.0000%, avg/expectancy=-0.3201%, PF=0.4107, max loss streak=4, naive max DD=3.2006%
- v2 top-10: n=10, clean=10, winrate=20.0000%, avg/expectancy=-0.3923%, PF=0.2496, max loss streak=7, naive max DD=4.9560%

Score_v2 changes correlation from -0.0082 to 0.0258, but its top-10 is worse than the old top-10 and remains negative. Ranking improvement is therefore **mixed and not decision-grade**. These are full-period diagnostics only. Acceptance uses the fixed out-of-time split.

## Filter diagnostics

Top hard-fail reasons: WEAK_CONFIRMATION_VOLUME=259, TOO_TIGHT_STOP=122, SCORE_V2_BELOW_PROVISIONAL_FLOOR=111, ENTRY_AFTER_EXHAUSTION=98, CHOPPY_SIDEWAYS_CONTEXT=28, HIGH_RR_LOW_PROBABILITY=4, TARGET_TOO_FAR_WITHOUT_SWING_ANCHOR=2, OPPOSING_REVERSAL_TRAP_CONFLICT=1.

Rejected winners: 101 (70.63% of all clean winners). Passed losers: 82. The filter is aggressive and still imperfect. See dedicated audits; no post-fact threshold changes were made.

## Baseline replay

All candidates, clean distribution, old score top-N and deciles, expectancy and PF are reproduced in the JSON/CSV artifacts. Ambiguous/expired observations are excluded from clean binary counts.

## Sensitivity and walk-forward

Sensitivity variants are diagnostic, not a best-threshold search. Every requested stop/volume sensitivity remains negative on OOS; RR-penalty and target-cap variants do not change the selected subset because other causal hard fails dominate. Exact expanding-design → next-month windows for September–December are recorded, while the final gate remains November–December out-of-time validation.

## Safety and next stage

Leakage audit: PASS. Runtime, trading runtime, composer, setup contracts and production thresholds were not changed. The system is **not** declared profitable. Next stage: **ENGINE-TREND-25 setup contract redesign**.
