# Parameter Sweep historical data source inventory

Inventory captured from the protected production PostgreSQL binding in an explicit
`READ ONLY` transaction.  Profile scope is `trade-5m-v2`; observed period is
2026-09-02T21:35:00Z through 2026-09-07T17:25:00Z.

| SOURCE | TABLE / MODEL | TIME RANGE | ROW COUNT | SYMBOL COVERAGE | TIMEFRAME | PRIMARY KEY | TIMESTAMP / WATERMARK | CONFIG / STRATEGY PROVENANCE | REPLAY USE |
|---|---|---|---:|---:|---|---|---|---|---|
| Market path | `candles_1m` | v2 period | 69,500 | 10 | 1m | `id`; unique `(symbol, open_time_ms)` | `close_time_ms` / `data_checksum` | Binance persisted closed candles | stop/target ordering, time-stop, MAE/MFE |
| Market boundary | `candles_5m` | v2 period | 13,900 | 10 | 5m | `id`; unique `(symbol, open_time_ms)` | `close_time_ms` / `data_checksum` | Binance persisted closed candles | chronological research timeline |
| Market/analysis/setup snapshots | `online_pipeline_results` | v2 period | 13,470 | 10 | 5m | `run_id` | `closed_until_ms` | runtime parameter-set id in payload | structural inputs, geometry, targets, costs, decisions |
| Pipeline decision state | `online_pipeline_runs` | v2 period | 13,470 corresponding results | 10 | 5m | `run_id` | `closed_until_ms` | `trade_profile_id=trade-5m-v2` | gate/status parity |
| Persisted setup candidates | setup payloads in `online_pipeline_results` | v2 period | 6,532 | 10 | 5m | `setup_id` / causal identity | `closed_until_ms` | runtime setup policy | persisted plus reconstructed opportunity universe |
| Selector lifecycle | `paper_plan_execution_outcomes` | v2 period | 97 v2-linked candidates (120 table rows at inventory time) | 10 | 5m | `pipeline_run_id` | `boundary_closed_at_ms` | eligible-approval-ranking-v1 | selector parity/control |
| Commands | `paper_execution_commands` | v2 period | 54 | 10 | event | `command_id` | `closed_until_ms` | configuration fingerprint and policy ids | execution parity |
| Orders/fills/positions | `paper_orders`, `paper_fills`, `paper_positions` | v2 period | 107 / 107 / 53 | 10 | event | record ids | causal timestamps | PAPER simulation policies | known execution outcome control |
| Exit decisions | `paper_exit_decisions` | v2 period | 53 | 10 positions | event | `exit_decision_id` | `source_closed_until_ms` | exit reason/cause | exit parity |
| MAE/MFE diagnostics | `scalping_outcome_diagnostics` | available history | 1 | 1 position | event | `position_id` | `created_at` | diagnostic version | optional persisted parity |
| Time-stop shadow | `scalping_stale_position_shadow_diagnostics` | available history | 0 | 0 | 5m | `(position_id,evaluation_closed_until_ms)` | same | policy/config hash | optional parity only, never replay prerequisite |
| Causal opportunity registry | `scalping_opportunities` | available history | 0 | 0 | event | `causal_opportunity_id` | `updated_at` | reset policy | optional persisted registry; payload identities remain usable |

Inventory conclusions:

- `PERSISTED_CLOSED_POSITIONS = 53` is a control sample, not the research dataset.
- `TOTAL_OPPORTUNITY_UNIVERSE = 6532`; 97 are linked to persisted selector/command state and 6,435 are reconstructed-only/historically rejected.
- `TIME_STOP_SHADOW_ROWS = 0` does not block replay because 69,500 causal 1m candles cover the v2 period.
- The adapter streams server-side result batches of 1,000 rows and bounded per-symbol candle ranges. It issues `SELECT` only and the PostgreSQL session is forced `READ ONLY`.
