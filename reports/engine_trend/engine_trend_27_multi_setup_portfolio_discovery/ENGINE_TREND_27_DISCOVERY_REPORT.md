# ENGINE-TREND-27 Multi-Setup Candidate Portfolio Discovery

## Decision

**ENGINE_TREND_27_NO_FAMILY_PASSES_GATE_NO_PAPER**. SHORT_V2 remains closed as a research-only failed forward contract. Runtime and paper trading are unchanged.

This is a single, frozen scan on previously unused common history. It tests whether distinct setup families produce enough clean observations and positive after-cost evidence; it does not claim a profitable strategy.

| Setup family | Candidates | Clean | Win rate | PF | Expectancy | Max DD (1% risk) | Loss streak | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| SHORT_CONTINUATION_PRACTICAL_TARGET | 421 | 377 | 32.626% | 0.594 | -0.339R | 74.477% | 16 | FAIL |
| SHORT_FAILED_REBOUND | 7 | 7 | 71.429% | 0.805 | -0.100R | 3.097% | 2 | FAIL |
| RANGE_BOUNDARY_REJECTION | 28 | 28 | 35.714% | 0.129 | -1.465R | 34.281% | 4 | FAIL |
| TRAP_REVERSAL | 68 | 67 | 44.776% | 0.256 | -0.947R | 49.508% | 5 | FAIL |
| MOMENTUM_BREAKDOWN_PULLBACK | 302 | 299 | 44.147% | 0.550 | -0.386R | 70.014% | 12 | FAIL |

Portfolio research observations: 826 candidates, 778 clean, PF 0.507, expectancy -0.448R, max DD 97.346% under the stated fixed-risk audit model. Same-bar family overlaps are reported and are not silently netted.

Families passing the minimum gate: **none**.

## Boundary

- Costs: 24 bps round trip; close-entry outcomes start on the next candle and ambiguous TP/SL bars are excluded, not guessed.
- Gate is per family: >=30 clean trades, PF >=1.05, expectancy >0 after costs, DD <15%, positive expectancy on at least two symbols, and no single winner above 50% of gross profit.
- Backward-held-out evidence is weaker than a new chronological forward. A pass authorizes only ENGINE-28 performance audit, never paper activation by itself.
- Failure-mode counts and symbol/month partitions are preserved in JSON for audit instead of tuning this window.
