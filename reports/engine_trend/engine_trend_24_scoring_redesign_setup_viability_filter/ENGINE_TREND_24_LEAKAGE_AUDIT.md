# ENGINE-TREND-24 Leakage Audit

## Result

**PASS**. `pre_entry_features()` explicitly copies only frozen pre-entry fields. `score_features()` and `filter_features()` accept that isolated view, not a candidate outcome object. Mutation tests prove score/filter invariance when forbidden outcome fields change.

## Allowed inputs

setup_type, symbol, direction, entry_time, entry_price, stop_price, target_1, invalidation_price, planned_rr, source_regime, source_hypothesis, structure_evidence, range_breakout_evidence, candle_evidence, technical_confirmation, no_trade_risks, future_data_used_for_generation, current_engine_trend_replay, coverage_status.

## Forbidden inputs

bars_to_outcome, bars_to_sl, bars_to_tp, candidate_rank, failure_bucket, future_close, future_high, future_low, gross_return_pct, label_status, mae, mae_r, mfe, mfe_r, net_return_pct, outcome, post_entry_drawdown, realized_return.

ENGINE-TREND-23 failure buckets are not inputs because their assignment may use outcomes. Old score is reported only as a baseline and is not a v2 feature. Historical MFE/MAE distributions are not used: without an independently frozen train-only model they would create leakage risk. Reachability uses causal ATR distance and a target already anchored to a pre-entry swing or range midline.

Chronological split: design through 2025-10-31 23:45 UTC; validation starts 2025-11-01 00:00 UTC. Full-sample diagnostics never select thresholds or acceptance status.
