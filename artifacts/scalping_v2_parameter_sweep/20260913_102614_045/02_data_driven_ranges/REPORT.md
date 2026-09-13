# Single-symbol Data-driven Range Generation

- Symbol/profile: `SUIUSDT` / `trade-5m-v2`
- Separability/sample adequacy: `PASS_LIMITED_SAMPLE` / `DESCRIPTIVE_ONLY`

These ranges are provisional research ranges.
They are not statistically certified.
They must not be promoted automatically.

## Parameter results

- `adverse_fill_reserve_bps` — DERIVED_EVIDENCE via effective_total_cost_bps; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `break_even_activation_target_progress` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `bucket_min_sample` — DIRECT_EVIDENCE via probability_sample_size; NOT_GENERATED_UNUSABLE_EVIDENCE; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; EVIDENCE_ACTIVITY_ALL_MISSING
- `causal_reset_min_conditions` — DERIVED_EVIDENCE via causal_reset_state; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `entry_refinement_1m_confirmation_count` — DERIVED_EVIDENCE via confirmation_state; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `entry_slippage_bps` — DIRECT_EVIDENCE via slippage_bps; NOT_GENERATED_UNUSABLE_EVIDENCE; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; EVIDENCE_ACTIVITY_CONSTANT
- `extension_seconds` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `hard_timeout_seconds` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `max_extensions` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `max_new_commands_per_cycle` — INDIRECT_EVIDENCE via risk_pre_approved; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `max_open_positions` — INDIRECT_EVIDENCE via risk_pre_approved; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `min_ev_reserve_r` — DERIVED_EVIDENCE via expected_ev_r; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `min_mfe_bps_at_soft_timeout` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `min_net_edge_bps` — DIRECT_EVIDENCE via net_edge_bps; PROVISIONAL_LOW_SAMPLE; domain `[1.0, 22.615013, 28.57565, 38.510045, 48.44444, 56.515413]`; confidence DESCRIPTIVE_ONLY; current included True; NO_BOUNDARY_PRESSURE; EMPIRICAL_WINNER_DENSE_TRANSITION_SUPPORT_PLUS_CURRENT
- `min_positive_ev_r` — DIRECT_EVIDENCE via expected_ev_r; NOT_GENERATED_UNUSABLE_EVIDENCE; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; EVIDENCE_ACTIVITY_ALL_MISSING
- `min_remaining_ev_r_at_soft_timeout` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `min_target_progress_at_soft_timeout` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `minimum_planned_rr` — DIRECT_EVIDENCE via planned_rr; PROVISIONAL_LOW_SAMPLE; domain `[0.6, 1.497788, 2.577955, 2.889157, 3.221992, 3.554827, 3.754528]`; confidence DESCRIPTIVE_ONLY; current included True; BOUNDARY_PRESSURE_HIGH; EMPIRICAL_WINNER_DENSE_TRANSITION_SUPPORT_PLUS_CURRENT
- `net_break_even_protection_enabled` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `prior_alpha` — DERIVED_EVIDENCE via estimated_p_win; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `prior_beta` — DERIVED_EVIDENCE via estimated_p_win; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `probability_confidence_level` — DERIVED_EVIDENCE via estimated_p_win; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `regime_lookback_candles` — INDIRECT_EVIDENCE via regime; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `risk_per_trade_bps` — INDIRECT_EVIDENCE via risk_score; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `soft_timeout_seconds` — NO_AUTHORIZED_EVIDENCE_MAPPING via NONE; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING
- `stop_max_bps` — DIRECT_EVIDENCE via stop_distance_bps; PROVISIONAL_LOW_SAMPLE; domain `[14.244403, 17.518161, 22.974424, 28.430687, 45.50224, 50.0]`; confidence DESCRIPTIVE_ONLY; current included True; BOUNDARY_PRESSURE_LOW; EMPIRICAL_WINNER_DENSE_TRANSITION_SUPPORT_PLUS_CURRENT
- `strategy_minimum_score` — DIRECT_EVIDENCE via strategy_score; NOT_GENERATED_UNUSABLE_EVIDENCE; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; EVIDENCE_ACTIVITY_EFFECTIVELY_CONSTANT
- `target_min_bps` — DIRECT_EVIDENCE via target_distance_bps; PROVISIONAL_LOW_SAMPLE; domain `[50.865921, 56.825926, 60.0, 66.759268, 76.692609, 84.758871]`; confidence DESCRIPTIVE_ONLY; current included True; NO_BOUNDARY_PRESSURE; EMPIRICAL_WINNER_DENSE_TRANSITION_SUPPORT_PLUS_CURRENT
- `total_open_risk_limit_bps` — INDIRECT_EVIDENCE via risk_pre_approved; NOT_GENERATED_NO_MAPPING; domain `[]`; confidence UNAVAILABLE; current included False; NO_BOUNDARY_PRESSURE; NO_AUTHORIZED_NUMERIC_DIRECT_RANGE_MAPPING

## Legacy comparison

Legacy values are comparison-only. Unsupported values are not removed from research or production configuration.

Promotion eligible: **NO**. Search executed: **NO**. Adaptive refinement: **NO**. Holdout opened: **NO**.
