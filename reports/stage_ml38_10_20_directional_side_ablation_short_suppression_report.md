# ML38.10.20 — directional side ablation and short-side suppression research

## Status
Implemented / research-only.

## Why this stage exists
ML38.10.19 showed that recovery guard and directional-bias hardening improved diagnostics but still did not produce an accepted candidate. The main runtime observation was directional asymmetry: LONG side was materially stronger than SHORT side on SOLUSDT, while SHORT side dragged total R and PF below acceptance.

## What changed
- Added directional side filter support to ProfitAwareEvaluatorV2.
- Added side-filter summary diagnostics:
  - original LONG/SHORT signal counts
  - filtered LONG/SHORT signal counts
  - removed LONG/SHORT counts
  - active side filter profile
- Added research-only profiles:
  - long_only_research
  - short_only_research
  - suppress_short_research
- Added lv28 side-ablation configs.
- Added lv28 candidates to fast-debug and quick-quality runtime shortlists.
- Propagated directional audit and side-filter summary into candidate reports and multi-symbol summaries.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- directional suppression: research-only
- short-side suppression is not live-ready execution logic

## Runtime expectations
- fast-debug: 2 symbols * 8 configs = 16 candidates.
- quick-quality SOLUSDT: 1 symbol * 16 configs = 16 candidates.

## What this can affect
This stage may improve PF and Total R by suppressing the currently weak SHORT side. That improvement must be treated carefully because it may overfit to one symbol/time window. A candidate is not acceptable only because LONG-only looks better. It must also preserve walk-forward robustness, signal count, baseline edge, and bias gates.
