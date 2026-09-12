# Single-symbol Winner / Loser Separability

- Final status/verdict: `PASS_LIMITED_SAMPLE` / `PASS_DESCRIPTIVE_ONLY_LOW_SAMPLE_EXACT_PERSISTED_CAUSAL_PREENTRY_ROWS`
- Selected symbol: `SUIUSDT`
- Profile/source: `trade-5m-v2` / `PERSISTED_CAUSAL_OBSERVATION`
- Source history scanned: `2026-09-02T21:35:00+00:00` through `2026-09-12T20:20:00+00:00` (9.947917 days)
- Source history provenance: `PERSISTED_CAUSAL_OBSERVATION_INVENTORY` / `DEEPEST_AVAILABLE_CLEAN_PERSISTED_SELECTED_SYMBOL_HISTORY`
- Trade sample span: `2026-09-05T03:21:00+00:00` through `2026-09-06T13:16:00+00:00` (1.413194 days; `EARLIEST_ENTRY_TIMESTAMP_TO_LATEST_CLOSE_TIMESTAMP`)
- Closed PAPER trades: 14 (WIN 2, LOSS 12, NEUTRAL 0)
- Binary analysis rows: 14
- Causality: persisted exact pre-entry snapshots; future leakage violations 0
- Single-symbol integrity: cross-symbol rows 0; duplicate trade rows 0

## Descriptive evidence

- Top winner-associated numeric features: planned_rr, entry_reference, atr_value, volatility_buffer
- Top loser-associated numeric features: atr_normalized_stop, stop_distance_bps, spread_bps
- Top categorical distinctions: utc_hour, utc_day_of_week, direction, target_source, regime
- Constant/no-op features: setup_quality_score, setup_structural_score, setup_confirmation_score, setup_context_score, source_confidence, strategy_score, strategy_raw_score, strategy_margin_to_threshold, risk_score, plan_score, slippage_bps, setup_type, impulse_phase, setup_quality, strategy_quality, risk_level, confirmation_state, entry_reference_source, stop_source, has_conflict, liquidity_presence, strategy_cap_applied, risk_pre_approved
- Missing/unavailable features: effective_total_cost_bps, commission_bps, probability_sample_size, estimated_p_win, expected_ev_r, causal_reset_state, momentum_score, volume_ratio, dynamic_required_rr
- Top bounded interactions: atr_normalized_stop + entry_reference, atr_normalized_stop + spread_bps, planned_rr + entry_reference, planned_rr + spread_bps, planned_rr + atr_value

## Adequacy and scope

This is descriptive evidence only when either class has fewer than five trades or the binary sample has fewer than 20 rows.  The canonical validation policy (20 trades / 3 UTC days) is recorded elsewhere and is not used to suppress separability output.  No production decision, cutoff, threshold, search range, search run, or holdout access is produced here.

`utc_hour` is a cyclic feature with period 24. It is analyzed as categorical descriptive evidence, is excluded from linear interaction geometry, and is marked machine-readably so downstream range generation cannot treat it as an ordinary linear min/max feature.
