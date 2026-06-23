# ML38.10.15 — Entry quality / stop pressure effectiveness tuning

## Цель

Настроить entry-path quality / stop-pressure filter так, чтобы он оценивал не только общий setup quality и risk/reward, но и направление прогноза: LONG/SHORT context, wick pressure, exhaustion, trap risk, expected follow-through and invalidation quality.

## Что изменено

- Добавлен score profile `directional_context_v2`.
- Старый режим `legacy_balanced_v1` сохранён для обратной совместимости.
- Добавлены lv23-конфиги:
  - `lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff`;
  - `lv23_h12_tts_thr065_sqmask060_epq065_sp050_eff`;
  - `lv23_h12_tts_thr065_sqmask060_epq068_sp047_eff`.
- Fast debug и quick quality теперь проверяют lv23 против lv22/lv21/lv19.
- Final-stream audit получил дополнительные effectiveness metrics:
  - `filter_false_signal_precision`;
  - `stop_pressure_false_signal_precision`;
  - `correct_signal_retention_rate`;
  - `entry_path_effectiveness_score`.

## Safety

- Live trading disabled.
- Orders disabled.
- Auto activation disabled.
- traders-core integration disabled.
- Entry filter remains ex-ante only and does not use future candles or realized MAE/MFE for filtering.

## Ожидаемый результат runtime

Кандидаты могут остаться rejected. Это нормально. Этап считается успешным, если:

- `--fast-debug` завершился без ошибок;
- `--quick-quality --symbol SOLUSDT` завершился без ошибок;
- lv23 configs есть в reports;
- `entry_path_prediction_filter_summary.diagnostic_version = ml38.10.15`;
- `stream_consistency_ok = true`;
- `entry_path_effectiveness_score` и precision/retention поля появились в candidate reports;
- accepted_candidate_count может быть 0;
- live trading / orders / auto activation остаются false.
