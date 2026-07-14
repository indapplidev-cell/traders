# ENGINE-TREND-25 Leakage Audit

- Frozen universe: **449** candidates; no V2 candidate discovery or recall claim.
- Split is unchanged: design through 2025-10-31; validation begins 2025-11-01.
- Setup, arming, entry, stop, and target decisions use candles no later than the relevant entry/fill decision.
- Outcomes are evaluated only after the entry decision. Outcome/MFE/MAE fields are never read by `base_stage`, `find_entry`, `trade_geometry`, or `evaluate_variant`.
- The locked default variant was declared before variant metrics were computed: `break_confirmation_low__atr_0_15__nearest_support`.
- Legacy provenance is explicit: discovery attached current-engine replay to top-10 only. For other frozen SHORT candidates, `SHORT_DOWN_CONTINUATION_RETEST` is normalized to the generator's DOWN-continuation hypothesis; any available replay must explicitly confirm DOWN continuation.
- Variant comparisons are diagnostics. A full-sample row is marked `REJECT_IN_SAMPLE_ONLY_UPLIFT` when it improves design expectancy but not validation expectancy.
- 15m OHLC does not identify intrabar order. Ambiguous fill/exit bars and simultaneous TP/SL bars are excluded from clean PF and expectancy.
- Limitation: V1 generated the universe with RR >= 1.5, so this audit cannot measure missed SHORT_V2 setups.

Status: **PASS WITH DECLARED SCOPE LIMITATION**.
