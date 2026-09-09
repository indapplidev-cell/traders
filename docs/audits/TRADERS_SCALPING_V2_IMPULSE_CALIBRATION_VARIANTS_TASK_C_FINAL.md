# Scalping v2 bounded impulse variants — Task C final

TASK_STATUS = PASS
FINAL_VERDICT = NO_CANDIDATE
VARIANTS_EVALUATED = 6
BEST_VARIANT = NONE; BEST_DIAGNOSTIC_ONLY=FLOOR_0_50PCT_PLUS_1_0ATR
BASELINE_CONFIRMED_IMPULSE_RATE = 0.183688%
VARIANT_CONFIRMED_IMPULSE_RATE = 68.993387%_BEST_DIAGNOSTIC_ONLY
BASELINE_CANDIDATES_PER_HOUR = 0.0
VARIANT_CANDIDATES_PER_HOUR = 44.470588
BASELINE_EXPECTANCY = UNAVAILABLE_ZERO_SCOREABLE
VARIANT_EXPECTANCY = -0.392726R
BASELINE_PF = UNAVAILABLE_ZERO_SCOREABLE
VARIANT_PF = 0.157868
BASELINE_ACHIEVABILITY = UNAVAILABLE_ZERO_CANDIDATES
VARIANT_ACHIEVABILITY = 0.340829
QUALITY_GAIN = NOT_PROVEN_FULL_SAMPLE_NEGATIVE
FREQUENCY_CHANGE = LARGE_DIAGNOSTIC_INCREASE_WITHOUT_ACCEPTABLE_QUALITY
VALIDATION_RESULT = NO_VARIANT_MET_ALL_SELECTION_GATES
OVERFIT_RISK = HIGH_SAME_DAY_SINGLE_MARKET_REGIME
SHADOW_ALLOWED = NO
NEXT_TASK = CONTINUE_FRESH_V3_COLLECTION_NO_TASK_D_DEPLOY

## Method

Exactly the frozen Task A cohort and v3 outcomes were reused; no legacy outcome
is primary evidence. Six definitions, and no more, were evaluated:

1. baseline `max(3%, 2.5 ATR)`;
2. ATR-only `1.0 ATR`;
3. ATR-only `1.5 ATR`;
4. `max(0.25%, 1.0 ATR)`;
5. `max(0.50%, 1.0 ATR)`;
6. two-stage fallback `0.25% + volatility_ratio>=0.9`, then `1.0 ATR`.

These values come directly from Task A's requested intensity bands, observed
move/ATR distribution, and the existing fallback contract. They are not a
large sweep. The chronological split uses the first 70% of boundaries for
development and the remaining 30% for validation. Costs, Dynamic Required RR,
minimum RR, confidence/probability authority, reserves, risk and position caps
are unchanged.

## Results

| Definition | Confirmed | Rate | Scoreable | Expectancy R | PF | Achievability |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 5 | 0.184% | 0 | n/a | n/a | n/a |
| ATR 1.0x | 2722 | 100.000% | 108 | -0.386983 | 0.143839 | 0.296192 |
| ATR 1.5x | 2721 | 99.963% | 108 | -0.386983 | 0.143839 | 0.296192 |
| floor 0.25% + ATR | 2624 | 96.400% | 108 | -0.386983 | 0.143839 | 0.296192 |
| floor 0.50% + ATR | 1878 | 68.993% | 89 | -0.392726 | 0.157868 | 0.340829 |
| two stage | 1483 | 54.482% | 108 | -0.386983 | 0.143839 | 0.296192 |

The 0.50% diagnostic has the best validation expectancy (`+0.053967R`, PF
`1.26625`) on only 20 scoreable validation rows, but its development/full
sample remains strongly negative and its validation achievability is only
0.218673. This is precisely the kind of same-day slice that cannot authorize
a candidate. All definitions also have zero production RR passes in this
frozen cohort because unchanged downstream probability/cost gates continue to
fail closed.

The baseline's practical zero rate means quality cannot be compared reliably
against it; frequency alone is not quality. No definition satisfies positive
development and validation expectancy plus improved achievability. Therefore
there is no research candidate and SHADOW is not allowed.

Full metrics, including candidate/RR-input rates, conservative p_win, Net PnL,
drawdown, costs and MFE/MAE, are in
`artifacts/scalping_v2_impulse_calibration_01/TASK_C_REPORT.json`.

Safety: no authoritative deploy, no parameter promotion, LIVE disabled, real
Binance order calls zero.
