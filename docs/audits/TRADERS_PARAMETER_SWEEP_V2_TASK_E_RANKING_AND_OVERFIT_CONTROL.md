# Parameter Sweep v2 — Block E ranking and overfit control

TASK_STATUS = PASS
PERFORMANCE_CLASSES = INVALID,INSUFFICIENT_SAMPLE,NEGATIVE_EXPECTANCY,WEAK,PROMISING_RESEARCH,VALIDATION_CANDIDATE
MIN_SAMPLE_POLICY = YAML_20_TRADES_3_SYMBOLS_3_INDEPENDENT_PERIODS_VALIDATION20
MULTI_METRIC_RANKING = PASS_EXPECTANCY_PF_DRAWDOWN_SAMPLE_SYMBOL_COVERAGE_STABILITY
PARETO = PASS_EXPECTANCY_DRAWDOWN_TRADE_COUNT
TRAIN_VALIDATION_HOLDOUT = CHRONOLOGICAL_HOLDOUT_EXCLUDED_FROM_SELECTION
OVERFIT_GUARD = PASS_PROMOTION_FORBIDDEN_SELECTION_BIAS_RISK
RANK_STABILITY = PASS_PERIOD_POSITIVE_SHARE_AND_SPREAD

`evaluation_status` describes whether evaluation completed; it is never used as
a profitability label. Performance classification is independently derived
from YAML-owned minimum sample and evidence thresholds. Ranking is deterministic
with `config_id` as the final tie breaker. A high hypothesis/evidence ratio
surfaces `PROMOTION_FORBIDDEN_SELECTION_BIAS_RISK`; the tool does not promote a
configuration automatically.

