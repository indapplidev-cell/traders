Stage: ML38.10.26.3
Goal: root-cause board aggregation fix and fold-1 repair target selection
Runtime commands were NOT executed by Codex
Cleanup commands were NOT executed by Codex
Runtime counts unchanged: fast-debug=20, quick-quality SOLUSDT=21
No new lv configs added
No ML acceptance gate relaxed
No auto-activation / no live trading

Fixed:
- multi-symbol root-cause board now uses candidate_results/full candidate payloads as source-of-truth
- configs_ranked receives capped root-cause fields from matching candidate_results
- fold_1_repair_target_selection added for lv28/lv29/lv30 LONG_ONLY/SUPPRESS_SHORT research candidates
