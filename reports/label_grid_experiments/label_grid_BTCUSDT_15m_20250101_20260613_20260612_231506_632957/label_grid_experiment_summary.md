# Label Grid Experiment Summary - label_grid_BTCUSDT_15m_20250101_20260613_20260612_231506_632957

## Run

- experiment_id: `label_grid_BTCUSDT_15m_20250101_20260613_20260612_231506_632957`
- status: `ok`
- experiment_status: `SAMPLE_COMPLETED`
- symbol: `BTCUSDT`
- interval: `15m`
- start_date: `2025-01-01`
- end_date: `2026-06-13`
- configs_tested: `1`

## Candidate Ranking

| Rank | Config | Candidate | Quality | Score | Failed Gates |
| --- | --- | --- | --- | --- | --- |
| `1` | `lv2_h08_thr04_tp10_sl10` | `REJECTED` | `QUALITY_REJECTED` | `-4.29` | `baseline_edge_gate,profit_aware_gate,walk_forward_gate` |

## Selection

- best_rejected_candidate: `lv2_h08_thr04_tp10_sl10`
- accepted_candidate_count: `0`
- rejected_candidate_count: `1`

## Diagnostics

- anti-collapse: `{'collapsed': 0, 'non_collapsed': 1}`
- profit-aware: `{'positive_profit_factor_count': 0, 'positive_total_r_count': 0}`
- walk-forward: `{'positive_walk_forward_profit_factor_count': 0, 'positive_walk_forward_total_r_count': 0}`
- gap quality: `{'MINOR': 1}`
- failed gates summary: `{'baseline_edge_gate': 1, 'profit_aware_gate': 1, 'walk_forward_gate': 1}`

## Recommendations

- Run a real limited grid to validate the best sample candidate on actual training.
- Keep traders-core disconnected and keep live trading disabled.

## Safety

- no traders-core integration
- no live trading
- no orders
- no auto activation
