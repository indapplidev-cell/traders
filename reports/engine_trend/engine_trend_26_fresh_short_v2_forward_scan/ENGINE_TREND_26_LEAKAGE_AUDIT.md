# ENGINE-TREND-26 Leakage Audit

- The scanner reads no ENGINE-TREND-23/24/25 candidates, labels, metrics, or selected IDs.
- Rules and the common-symbol window are constants in code and recorded in `ENGINE_TREND_26_LOCKED_SCANNER_CONTRACT.json`.
- Forward confirmations: `2025-12-18T00:00:00Z` through `2026-06-14T20:00:00Z`; every entry has 96 common-symbol future bars available through `2026-06-15T20:00:00Z`.
- Pre-entry plans were written and frozen before `label_plan` ran. Freeze SHA-256: `8596067f8ed165355c6953b0ef709b6c85a79838c975466443ec7ef368e62b0f`.
- `scan_symbol`, `engine_hypothesis`, `find_break_entry`, and target/risk construction do not access outcome labels, MFE, MAE, or post-fill returns.
- Post-confirmation candles up to the actual fill are entry-decision data, not outcome data. Outcome labelling begins at the frozen fill.
- Fill-bar stop ambiguity and simultaneous TP/SL ambiguity are excluded from clean PF/expectancy.
- No threshold, entry, stop, target, symbol, or month is selected from forward results. There is one locked reference mode.

Status: **PASS**.
