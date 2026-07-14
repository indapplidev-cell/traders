# ENGINE-TREND-23 Diagnostic Filter Hypotheses

Every row is **DIAGNOSTIC_HYPOTHESIS_ONLY**. These are in-sample ablations, not production rules and not evidence that the strategy improves. All require a locked definition followed by walk-forward/out-of-time validation.

Baseline clean metrics: winrate **32.21%**, expectancy **-0.19%**.

| Hypothesis | Candidates left | Winrate | Expectancy | PF | Excludes | Why overfit-prone |
| --- | --- | --- | --- | --- | --- | --- |
| VOLUME_RATIO_GTE_0_8 | 152 | 34.00% | -0.14% | 0.6585 | Excludes confirmation candles with volume ratio <0.8. | Cutoff inspected on one in-sample period; volume regimes vary by asset/time. |
| RR_LT_5 | 443 | 32.65% | -0.18% | 0.5712 | Excludes mechanically high RR >=5. | The RR boundary was chosen after observing this sample. |
| STOP_GT_0_75_ATR | 327 | 34.37% | -0.17% | 0.6096 | Excludes stops <=0.75 ATR. | ATR cutoff may proxy setup type and volatility regime. |
| TARGET_LT_4_ATR | 443 | 32.35% | -0.19% | 0.5420 | Excludes targets >=4 ATR. | Target reachability is horizon- and regime-dependent. |
| NO_BOLLINGER_EXTENSION | 446 | 32.20% | -0.19% | 0.5608 | Excludes entries within 0.25 ATR of the directional outer band. | Band distance and 0.25 ATR cutoff are sample-selected diagnostics. |
| CONTINUATION_CORRECTION_LE_6 | 351 | 32.18% | -0.19% | 0.5439 | Excludes continuation corrections older than 6 bars; keeps range setups. | Correction age is not the same as trend age and the cutoff is in-sample. |
| ADX_15_TO_35 | 318 | 31.85% | -0.20% | 0.5450 | Keeps only moderate ADX [15,35]. | Classic indicator bucket mining has high multiple-testing risk. |
| RETEST_DISTANCE_0_1_TO_0_5 | 303 | 32.56% | -0.19% | 0.5373 | Keeps range setups and continuation level distance [0.1,0.5] ATR. | Distance thresholds were evaluated on the same labeled sample. |

Dangerous choices include hour/weekday/month filters, selecting only the best symbol after reading outcomes, indicator bucket mining, optimizing several cutoffs jointly, and ranking by the best in-sample quality decile. These have high multiple-testing and regime-selection risk. No hypothesis may enter runtime before an untouched out-of-time period and sensitivity/stability checks.
