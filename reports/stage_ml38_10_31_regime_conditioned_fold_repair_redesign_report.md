# ML38.10.31-BIG — regime-conditioned fold repair redesign

1. Root cause:
   hard blocked_regime after ML38.10.30 became too aggressive.

2. What changed:
   - evaluator supports conditional_regime_rules;
   - lv34 configs added;
   - matrix/runtime registration updated;
   - reporter/analyzer/probe preserve conditional rule diagnostics.

3. New counts:
   fast-debug = 36
   quick-quality SOLUSDT = 38

4. Research-only safety:
   lv34 cannot be accepted.

5. Expected research question:
   Can conditional regime-risk filtering preserve useful trend_down/high_volatility signals
   while removing only poor-quality regime-risk entries?
