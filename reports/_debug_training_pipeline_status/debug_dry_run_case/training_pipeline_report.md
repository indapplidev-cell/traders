# Training Pipeline Report - debug_dry_run_case

## Run

- run_id: `debug_dry_run_case`
- status: `DRY_RUN_COMPLETED`
- symbol: `BTCUSDT`
- interval: `15m`
- start_date: `2025-01-01`
- end_date: `2026-06-22`
- dry_run: `true`
- sample_mode: `false`

## Logs

- training_pipeline.log: `reports\_debug_training_pipeline_status\debug_dry_run_case\training_pipeline.log`
- training_pipeline_events.jsonl: `reports\_debug_training_pipeline_status\debug_dry_run_case\training_pipeline_events.jsonl`
- training_pipeline_report.json: `reports\_debug_training_pipeline_status\debug_dry_run_case\training_pipeline_report.json`
- training_pipeline_report.md: `reports\_debug_training_pipeline_status\debug_dry_run_case\training_pipeline_report.md`

## Stages

| Stage | Status | Duration | Message |
| --- | --- | --- | --- |
| `health_check` | `COMPLETED` | `0.00s` | Health check completed in simulated mode |
| `db_check` | `SKIPPED` | `0.00s` | Dry-run does not require DB access |
| `load_candles` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `check_candle_gaps` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `build_features` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `build_labels` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `build_dataset` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `train_model` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `probability_diagnostics` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `baseline_compare` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `calibration_diagnostics` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `profit_aware_evaluation` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `walk_forward_evaluation` | `SKIPPED` | `0.00s` | Dry-run simulated stage |
| `gate_policy_replay_evaluation` | `COMPLETED` | `0.00s` | GatePolicy replay sample evaluation completed |
| `model_quality_validation` | `COMPLETED` | `0.00s` | Model quality validation sample completed |
| `export_reports` | `COMPLETED` | `0.01s` | Reports exported |

## Quality Summary

- quality_status: `NEEDS_MORE_DATA`
- approved_for_traders_core_integration: `False`
- approved_for_live_trading: `False`
- approved_for_auto_activation: `False`

## Model Summary

- model_version: `None`
- model_accuracy: `0.3927`
- collapse_detected: `False`

## Baseline Summary

- baseline_accuracy: `0.3783`

## GatePolicy Replay Summary

- gate_policy_replay_status: `SAMPLE_ONLY`
- total_records: `5`

## Gap Quality

- gap_severity: `OK`
- dataset_safe_for_training: `True`
- gap_count: `0`

## Anti-Collapse

- collapse_detected: `False`
- collapse_type: `NONE`

## Candidate Selection

- candidate_status: `CANDIDATE_REJECTED`
- candidate_decision: `REJECT_FOR_RESEARCH`
- failed_gates: `['profit_aware_gate', 'walk_forward_gate']`

## Label Config

- label_version: `lv1`
- horizon_candles: `8`
- label_mode: `future_close_atr`
- opportunity_probability_threshold: `0.5`
- setup_quality_min_threshold: `None`
- setup_quality_decision_mask_enabled: `False`
- setup_quality_decision_mask_min_threshold: `None`
- opportunity_threshold_sweep_enabled: `False`
- opportunity_threshold_candidates: `[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]`

## Quality Gates

- passed_gates: `['baseline_edge_gate', 'collapse_gate', 'gap_quality_gate', 'gate_policy_replay_gate']`
- failed_gates: `['profit_aware_gate', 'walk_forward_gate']`
- opportunity_baseline_edge: `None`
- opportunity_collapse_gate: `{}`
- no_trade_dominance_gate: `{}`
- setup_edge_gate: `{}`
- opportunity_precision_gate: `{'passed': True, 'minimum': None, 'actual': None}`
- opportunity_recall_gate: `{'passed': True, 'minimum': None, 'actual': None}`
- predicted_trade_rate_gate: `{'passed': True, 'maximum': None, 'actual': None}`
- trade_rate_ratio_gate: `{'passed': True, 'maximum': None, 'actual': None}`
- opportunity_false_positive_gate: `{'passed': True, 'maximum': None, 'actual': None}`

## Label Mode Audit

- recommendation: `None`
- agreement_ratio: `None`
- conflict_ratio: `None`
- ambiguous_ratio: `None`

## Flat Subtype Audit

- dominant_flat_subtype: `None`
- flat_subtype_counts: `None`

## Setup-Aware Label Diagnostics

- recommended_label_mode_by_setup_type: `None`
- ambiguous_ratio_by_setup_type: `None`

## Book-Driven Forensic Audit

- final_diagnosis: `None`
- next_action_recommendation: `None`

## Schwager Slice Robustness

- robustness_flags: `None`
- edge_by_time_slice: `None`
- edge_by_regime: `None`
- edge_by_setup_type: `None`

## Schwager Decision Board

- final_research_decision: `READY_FOR_SINGLE_SYMBOL_FULL_ONLY_IF_USER_APPROVES`
- primary_failure: `no_hard_failure_detected`
- secondary_failures: `['profit_aware_gate', 'walk_forward_gate']`
- what_not_to_do_next: `['do_not_soften_gates']`
- what_to_do_next: `['do_not_tune_class_weights_yet']`

## Class-Margin Objective Decision

- class_margin_objective_allowed: `None`
- reason: `None`
- missing_diagnostics: `None`
- explanation: `None`

## Safety

- no live trading
- no orders
- no traders-core integration
- no auto activation

## Next Recommendations

- Run the pipeline in real long-history mode for actual training.
- Collect longer real history and increase walk-forward coverage.
- Keep live trading, orders, and traders-core integration disabled.
