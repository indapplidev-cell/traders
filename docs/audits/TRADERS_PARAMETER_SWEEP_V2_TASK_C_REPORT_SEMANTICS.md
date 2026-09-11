# Parameter Sweep v2 — Task C: report semantics

```text
TASK_STATUS = PASS
HISTORICAL_BASELINE_CONTROL = EXPLICIT_NON_COMPARABLE_POPULATION_WITH_98_TRADES_IN_ARCHIVED_RUN
SEARCH_VALIDATION_BASELINE = EXPLICIT_SAME_SPLIT_POPULATION_WITH_0_TRADES_IN_ARCHIVED_RUN
SAME_SPLIT_COMPARISON = PASS
STATUS_RESULTS_PARITY = PASS
REPORT_RESULTS_PARITY = PASS
PROMOTION_TERMINOLOGY = PROMOTION_EVALUATION_ALLOWED_SEPARATE_FROM_CANDIDATE_PROMOTION_ELIGIBLE
INSUFFICIENT_SAMPLE_GATE_DETAILS = PASS_EXACT_CURRENT_REQUIRED_DEFICIT_PER_FAILED_GATE
```

`RESULTS.jsonl` is the canonical aggregation input. The final STATUS counters,
REPORT classification counts, checkpoint summary, and GUI-observed counters use
the same classification semantics. A config classified as
`INSUFFICIENT_SAMPLE` therefore increments `insufficient_configs` exactly once.

Historical Set #2 control remains available for context but is explicitly not
comparable to candidates. Candidate comparisons use
`SEARCH_VALIDATION_BASELINE`, evaluated with the same frozen dataset, validation
split, cutoff, cost snapshot and evaluator contract.
