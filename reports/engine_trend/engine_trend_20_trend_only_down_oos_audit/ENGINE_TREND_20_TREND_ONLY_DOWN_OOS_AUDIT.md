# ENGINE-TREND-20 — trend-only DOWN OOS audit

Final status: **TREND_ONLY_DOWN_CONTRACT_PROMISING_BLOCKED_MANUAL_LABELS**.

Audit-only conclusion: runtime implementation is not authorized. Dataset buckets are provisional audit buckets, not ground truth; blind manual labels are absent.

## Metrics

- Windows: 52 total, 52 included, 0 excluded.
- Baseline UP / DOWN / FLAT / UNKNOWN: 12 / 14 / 8 / 18.
- Counterfactual passes: 11.
- Potential false DOWN: 3 (10.34% of provisional controls).
- Missed trend-only DOWN captured counterfactually: 3.

## Answers

1. A future contract is not ready for runtime. Its diagnostic value is conditional on low control-bucket activation and independent blind labels.
2. The provisional false-DOWN risk is reported above; this is bucket-gated, not ground-truth error.
3. The safe-looking envelope requires formal bearish Altunina structure or an LL/LH bearish-majority sequence, a subsequent LH/failed rebound, at least three bearish technical votes, price below multiple averages and VWAP, ADX >= 20, ATR-scaled negative progress, and no confirmed range/reversal/trap conflict.
4. Primary false-DOWN precursors are range detection, confirmed range conflict, weak ADX/progress, missing LH-after-LL, bullish reversal, and trap conflicts.
5. ENGINE-TREND-20B may only be a design stage after blind labels; no implementation stage is recommended now.

## Mandatory cases

- BTC 2026-07-13 16:00: baseline `UNKNOWN`, counterfactual pass `True`, flags `[]`.
- SOL 2026-07-08 11:30: baseline `UNKNOWN`. DOWN_CONTINUATION invalidation is caused by Altunina `structural_pivot_breached=true`; the hypothesis reason code states the outcome but omits pivot/leg values, so this is a reporting gap rather than a newly demonstrated logic defect.

## Acceptance gate

Manual-label-gated metrics: `BLOCKED_MANUAL_LABELS`. Therefore READY_FOR_IMPLEMENTATION is prohibited regardless of proxy metrics.
