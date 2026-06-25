# ML35 Multi-Symbol Feature/Regime Analysis

## Summary

- symbols: `['BTCUSDT', 'SOLUSDT']`
- experiment_count: `2`
- candidate_count: `16`
- evaluated_candidate_count: `16`
- failed_candidate_count: `0`
- accepted_candidate_count: `0`
- rejected_candidate_count: `16`
- best symbol: `BTCUSDT`
- best candidate config: `lv19_h08_tts_thr065_sqmask060`
- best candidate score: `-1.909237`
- top failed gate: `baseline_edge_gate`

## Symbol Comparison Table

| Symbol | Best Config | Score | Collapse Type | Flat Bias | Down Blindness | Baseline Edge | Profit Factor | Walk-Forward PF | Final Decision | Real Diagnostics | Diag Rows | Regime Features | Regime Count | Candle/TA Context | Candle/TA Count | Failed Gates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `BTCUSDT` | `lv19_h08_tts_thr065_sqmask060` | `-1.909237` | `mixed` | `False` | `False` | `-0.7512864493996569` | `0.9076671290871174` | `None` | `NEEDS_LABEL_REWORK` | `True` | `3884` | `True` | `8` | `True` | `170` | `profit_aware_gate,walk_forward_gate,bias_gate,baseline_edge_gate` |
| `SOLUSDT` | `lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias` | `-2.127594` | `mixed` | `False` | `False` | `-0.82960413080895` | `0.7019361339389568` | `None` | `NEEDS_LABEL_REWORK` | `True` | `3869` | `True` | `8` | `True` | `170` | `profit_aware_gate,walk_forward_gate,bias_gate,baseline_edge_gate` |

## Best Symbol

- best symbol: `BTCUSDT`
- best global config: `lv19_h08_tts_thr065_sqmask060`
- best score: `-1.909237`

## Gate Failures By Symbol

- BTCUSDT: `['profit_aware_gate', 'walk_forward_gate', 'bias_gate', 'baseline_edge_gate']`
- SOLUSDT: `['profit_aware_gate', 'walk_forward_gate', 'bias_gate', 'baseline_edge_gate']`

## Feature Version Check

- all_feature_version_fv2: `False`
- all_feature_version_fv3_candle_ta_context: `False`
- all_feature_version_fv4_book_setup_context: `True`
- feature_versions_by_symbol: `{'BTCUSDT': 'fv4_book_setup_context', 'SOLUSDT': 'fv4_book_setup_context'}`

## Gap Training Safety Check

- all_gap_training_safe: `True`
- gap_severity_by_symbol: `{'BTCUSDT': 'OK', 'SOLUSDT': 'OK'}`
- effective_gap_count_by_symbol: `{'BTCUSDT': 0, 'SOLUSDT': 0}`

## Real Feature Diagnostics Check

- all_real_feature_diagnostics_used: `True`
- symbols_missing_real_diagnostics: `[]`
- real_feature_diagnostics_missing_reason_by_symbol: `{'BTCUSDT': None, 'SOLUSDT': None}`

## Regime Integration Status

- symbols_missing_regime_features: `[]`
- symbols_missing_candle_ta_context_features: `[]`
- regime_features_missing_reason_by_symbol: `{'BTCUSDT': None, 'SOLUSDT': None}`
- candle_ta_context_missing_reason_by_symbol: `{'BTCUSDT': None, 'SOLUSDT': None}`
- book_setup_context_feature_count_by_symbol: `{'BTCUSDT': 54, 'SOLUSDT': 54}`
- missing_context_feature_count_by_symbol: `{'BTCUSDT': 6, 'SOLUSDT': 6}`
- regime_training_applied_by_symbol: `{'BTCUSDT': True, 'SOLUSDT': True}`
- regime_specific_training_applied_any: `True`

## Walk-Forward/Profit-Aware Summary

- walk_forward_summary: `{'walk_forward_failed_count': 2, 'all_failed': True, 'profit_factor_by_symbol': {'BTCUSDT': None, 'SOLUSDT': None}, 'total_r_by_symbol': {'BTCUSDT': None, 'SOLUSDT': None}}`
- profit_aware_summary: `{'profit_aware_failed_count': 2, 'profit_factor_by_symbol': {'BTCUSDT': 0.9076671290871174, 'SOLUSDT': 0.7019361339389568}, 'total_r_by_symbol': {'BTCUSDT': -15.360121186907046, 'SOLUSDT': -17.19936480895271}}`

## Collapse Summary

- collapse_summary: `{'collapse_failed_count': 0, 'all_failed': False, 'collapse_detected_by_symbol': {'BTCUSDT': True, 'SOLUSDT': True}, 'collapse_type_by_symbol': {'BTCUSDT': 'mixed', 'SOLUSDT': 'mixed'}}`
- collapse_diagnostics_v2_by_symbol: `{'BTCUSDT': {'actual_distribution': {'DOWN': 0.04288164665523156, 'FLAT': 0.9228130360205832, 'UP': 0.03430531732418525}, 'class_absence': {'DOWN': False, 'FLAT': False, 'UP': False}, 'collapse_detected': True, 'collapse_type': 'FLAT_UNDERPREDICTION', 'confidence_distribution': {'avg_prob_down': 0.4360841028328416, 'avg_prob_flat': 0.27069803798893916, 'avg_prob_up': 0.29321785666061306, 'max_prob_q50': 0.6414501667022705, 'max_prob_q90': 0.6866395473480225, 'rows_above_thresholds': {'omitted': True, 'original_count': 7, 'original_type': 'dict', 'reason': 'compact_report_profile_heavy_payload'}}, 'diagnostic_name': 'collapse_diagnostics_v2', 'diagnostic_version': 'ml36', 'dominant_class': 'DOWN', 'dominant_class_ratio': 0.6003430531732419, 'down_prediction_rate': 0.6003430531732419, 'feature_version': 'fv4_book_setup_context', 'flat_prediction_rate': 0.09433962264150944, 'flat_underprediction_detected': False, 'label_version': 'lv19_h08_tts_thr065_sqmask060', 'low_margin_detected': False, 'predicted_distribution': {'DOWN': 0.6003430531732419, 'FLAT': 0.09433962264150944, 'UP': 0.3053173241852487}, 'probability_margin_distribution': {'margin_q50': 0.39087975025177, 'margin_q90': 0.47100994884967806}, 'recommendations': ['Increase flat-aware labeling/calibration or add flat threshold diagnostics.'], 'symbol': 'BTCUSDT', 'uniform_probability_detected': False, 'up_prediction_rate': 0.3053173241852487}, 'SOLUSDT': {'actual_distribution': {'DOWN': 0.027538726333907058, 'FLAT': 0.9363166953528399, 'UP': 0.03614457831325301}, 'class_absence': {'DOWN': False, 'FLAT': False, 'UP': False}, 'collapse_detected': True, 'collapse_type': 'FLAT_UNDERPREDICTION', 'confidence_distribution': {'avg_prob_down': 0.40300626839910236, 'avg_prob_flat': 0.2531325324164405, 'avg_prob_up': 0.34386119783796665, 'max_prob_q50': 0.6547300219535828, 'max_prob_q90': 0.689373254776001, 'rows_above_thresholds': {'omitted': True, 'original_count': 7, 'original_type': 'dict', 'reason': 'compact_report_profile_heavy_payload'}}, 'diagnostic_name': 'collapse_diagnostics_v2', 'diagnostic_version': 'ml36', 'dominant_class': 'DOWN', 'dominant_class_ratio': 0.540447504302926, 'down_prediction_rate': 0.540447504302926, 'feature_version': 'fv4_book_setup_context', 'flat_prediction_rate': 0.043029259896729774, 'flat_underprediction_detected': True, 'label_version': 'lv27_h08_tts_epq70_sp45_dbias', 'low_margin_detected': False, 'predicted_distribution': {'DOWN': 0.540447504302926, 'FLAT': 0.043029259896729774, 'UP': 0.4165232358003442}, 'probability_margin_distribution': {'margin_q50': 0.41615621745586395, 'margin_q90': 0.4746806025505066}, 'recommendations': ['Increase flat-aware labeling/calibration or add flat threshold diagnostics.'], 'symbol': 'SOLUSDT', 'uniform_probability_detected': False, 'up_prediction_rate': 0.4165232358003442}}`
- flat_bias_summary: `{'flat_bias_detected_by_symbol': {'BTCUSDT': False, 'SOLUSDT': False}, 'symbol_bias_severity_by_symbol': {'BTCUSDT': 'HIGH', 'SOLUSDT': 'HIGH'}}`
- down_blindness_summary: `{'down_blindness_detected_by_symbol': {'BTCUSDT': False, 'SOLUSDT': False}}`
- baseline_edge_summary: `{'baseline_edge_by_symbol': {'BTCUSDT': -0.7512864493996569, 'SOLUSDT': -0.82960413080895}, 'positive_baseline_edge_symbols': []}`

## Label Mode Audits

- label_mode_audit_summary: `{'diagnostic_name': 'label_mode_audit_multi_symbol_summary', 'diagnostic_version': 'ml38_9_9', 'recommendation_by_symbol': {'BTCUSDT': 'KEEP_FUTURE_CLOSE', 'SOLUSDT': 'KEEP_FUTURE_CLOSE'}, 'conflict_ratio_by_symbol': {'BTCUSDT': 0.05251141552511415, 'SOLUSDT': 0.04587993608765122}, 'ambiguous_ratio_by_symbol': {'BTCUSDT': 0.002511415525114155, 'SOLUSDT': 0.0027391006619493265}}`
- flat_subtype_summary: `{'diagnostic_name': 'flat_subtype_multi_symbol_summary', 'diagnostic_version': 'ml38_9_9', 'dominant_flat_subtype_by_symbol': {'BTCUSDT': 'volatile_flat', 'SOLUSDT': 'failed_breakout_flat'}, 'flat_subtype_counts_by_symbol': {'BTCUSDT': {'ambiguous_touch_flat': 3, 'clean_flat': 101, 'failed_breakout_flat': 498, 'no_setup_flat': 0, 'range_chop_flat': 134, 'volatile_flat': 510}, 'SOLUSDT': {'ambiguous_touch_flat': 3, 'clean_flat': 99, 'failed_breakout_flat': 510, 'no_setup_flat': 0, 'range_chop_flat': 157, 'volatile_flat': 495}}}`
- setup_aware_label_summary: `{'diagnostic_name': 'setup_aware_label_multi_symbol_summary', 'diagnostic_version': 'ml38_9_9', 'recommended_label_mode_by_symbol': {'BTCUSDT': {'nison_context': 'KEEP_FUTURE_CLOSE'}, 'SOLUSDT': {'alt_context': 'INSUFFICIENT_DATA', 'nison_context': 'KEEP_FUTURE_CLOSE', 'support_resistance_context': 'INSUFFICIENT_DATA'}}, 'ambiguous_ratio_by_symbol': {'BTCUSDT': {'nison_context': 0.002511415525114155}, 'SOLUSDT': {'alt_context': 0.0, 'nison_context': 0.002740977615349475, 'support_resistance_context': 0.0}}}`

## Schwager Robustness

- schwager_robustness_summary: `{'diagnostic_name': 'schwager_robustness_multi_symbol_summary', 'diagnostic_version': 'ml38_10_2', 'available_candidate_count': 16, 'final_research_decision_counts': {'NEEDS_LABEL_REWORK': 9, 'TWO_STAGE_REJECTED_UNDERTRADING': 7}, 'primary_failure_counts': {'label_noise_high': 9, 'two_stage_undertrading': 7}, 'top_final_research_decisions': ['NEEDS_LABEL_REWORK', 'TWO_STAGE_REJECTED_UNDERTRADING'], 'top_primary_failures': ['label_noise_high', 'two_stage_undertrading']}`

## Recommendations

- Do not activate model; no accepted candidates were produced.
- ML36 should improve walk-forward stability before more grid expansion.
- Review profit-aware gate thresholds before any broader multi-symbol expansion.
- Keep traders-core, live trading, orders, and auto activation disabled.

## Safety

- approved_for_live_trading: `False`
- approved_for_auto_activation: `False`
- orders_enabled: `False`
- traders_core_connected: `False`


## Entry-Path / Stop-Pressure Audit

| Symbol | Best config | Enabled | EPQ threshold | Stop threshold | MAE threshold | Original | Filtered | Blocked | Stream OK | Stop status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `BTCUSDT` | `lv19_h08_tts_thr065_sqmask060` | `False` | `None` | `None` | `328` | `328` | `0` | `True` | `NO_ENTRY_PATH_FILTER` |
| `SOLUSDT` | `lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias` | `True` | `0.71` | `0.44` | `578` | `139` | `439` | `True` | `STOP_PRESSURE_MIXED_TRUE_AND_FALSE_SIGNAL_BLOCKS` |

## Directional Side Audit

### BTCUSDT
- side_filter_profile: `None`
- allowed_signal_directions: `[]`
- direction_balance_ratio: `None`
- long_total_r: `None`
- short_total_r: `None`
### SOLUSDT
- side_filter_profile: `None`
- allowed_signal_directions: `[]`
- direction_balance_ratio: `None`
- long_total_r: `None`
- short_total_r: `None`

## Directional side ablation comparator

- diagnostic_status: `NO_SIDE_ABLATION_CANDIDATES`
- side_profile_counts: `{'BOTH_DIRECTIONS': 16, 'LONG_ONLY': 0, 'SHORT_ONLY': 0, 'SUPPRESS_SHORT': 0}`
- best LONG_ONLY: `{}`
- best SHORT_ONLY: `{}`
- best SUPPRESS_SHORT: `{}`
- best BOTH_DIRECTIONS: `{'config_id': 'lv19_h08_tts_thr065_sqmask060', 'candidate_status': 'REJECTED', 'profit_factor': None, 'profit_total_r': None, 'walk_forward_profit_factor': 0.0, 'walk_forward_total_r': 0.0, 'resolved_signal_count': 0, 'signal_count': 0, 'directional_side_filter_profile': None, 'allowed_signal_directions': [], 'direction_balance_ratio': None, 'long_total_r': None, 'short_total_r': None, 'long_avg_r': None, 'short_avg_r': None, 'directional_profit_skew_r': None, 'directional_profit_skew_ratio': None, 'side_filter_removed_signal_count': 0, 'side_filter_removed_signal_rate': None, 'research_only': False, 'side_profile': 'BOTH_DIRECTIONS'}`
- long_only_vs_both_delta: `{'available': False, 'left_side_profile': 'LONG_ONLY', 'right_side_profile': 'BOTH_DIRECTIONS', 'profit_factor_delta': None, 'profit_total_r_delta': None, 'walk_forward_profit_factor_delta': None, 'walk_forward_total_r_delta': None, 'resolved_signal_count_delta': None, 'left_config_id': None, 'right_config_id': None}`
- suppress_short_vs_both_delta: `{'available': False, 'left_side_profile': 'SUPPRESS_SHORT', 'right_side_profile': 'BOTH_DIRECTIONS', 'profit_factor_delta': None, 'profit_total_r_delta': None, 'walk_forward_profit_factor_delta': None, 'walk_forward_total_r_delta': None, 'resolved_signal_count_delta': None, 'left_config_id': None, 'right_config_id': None}`
- warnings: `[]`
- recommendations: `['compare_lv28_against_lv27_lv26_before_acceptance', 'do_not_accept_long_only_without_multisymbol_confirmation', 'inspect_short_side_failure_modes_before_live_use']`

| Side profile | Config | PF | Total R | WF PF | WF R | Signals | Long R | Short R |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `BOTH_DIRECTIONS` | `lv19_h08_tts_thr065_sqmask060` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv28_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_only` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv22_h08_tts_thr065_sqmask060_epq070_sp045` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv19_h08_tts_thr065_sqmask060` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv28_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_only` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv22_h08_tts_thr065_sqmask060_epq070_sp045` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |
| `BOTH_DIRECTIONS` | `lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias` | `None` | `None` | `0.0` | `0.0` | `0` | `None` | `None` |