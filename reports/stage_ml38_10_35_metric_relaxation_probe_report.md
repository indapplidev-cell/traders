# ML38.10.35 — metric-relaxation diagnostic probe

## Scope

- Code-only stage.
- No cleanup.
- No runtime.
- No fast-debug.
- No quick-quality.

## Why

ML38.10.34 showed lv35 two-metric overlap was absent or too sparse.
This stage adds a diagnostic min_count=1 relaxation probe and top-level aggregate diagnostics.

## Added diagnostics

- conditional_regime_rule_relaxation_probe_board
- aggregate_conditional_regime_rule_relaxation_probe_board
- conditional_regime_relaxation_probe_summary
- aggregate_conditional_regime_relaxation_probe_summary

## Added configs

- lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe
- lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe
- lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe
- lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe
- lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_probe
- lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe

## Safety

- lv36 is research-only.
- lv36 is diagnostic-only.
- lv36 must not be accepted.
- lv36 must not be approved for live.
- lv36 must not auto-activate.

## Runtime policy

Runtime was not executed in this stage.
