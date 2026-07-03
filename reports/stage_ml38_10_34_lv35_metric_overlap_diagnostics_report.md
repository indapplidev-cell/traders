# ML38.10.34 — lv35 metric-overlap diagnostics

## Goal
Explain why lv35 targeted conditional regime rules can be eligible but still remove zero signals.

## Scope
Code-only diagnostic stage. No runtime execution.

## Added diagnostics
- conditional_regime_rule_metric_failure_count_distribution_by_rule
- conditional_regime_rule_observed_metric_failure_counts_by_rule
- conditional_regime_rule_metric_pair_failure_counts_by_rule
- conditional_regime_rule_outcome_by_failure_count
- conditional_regime_metric_overlap_board

## Safety
- No live trading.
- No auto activation.
- No clean_traders_ml.py execution.
- No fast-debug runtime.
- No quick-quality runtime.
- All lv35 configs remain research-only.

## Expected next runtime interpretation
If lv35 has eligible_count > 0 and actual_removed_count = 0, inspect metric_overlap_status:
- NO_METRIC_FAILURES
- ONLY_ONE_METRIC_FAILURES
- NO_TWO_METRIC_OVERLAP
- REMOVALS_ACTIVE

The next ML stage must use this board before adding new lv rules.
