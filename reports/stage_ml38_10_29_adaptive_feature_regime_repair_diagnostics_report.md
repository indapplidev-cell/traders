# ML38.10.29 Adaptive Feature/Regime Repair Diagnostics

## Что исправлено

Добавлены enriched diagnostics для `fold_feature_regime_filter_summary` версии `ml38.10.29`: target-date counters, primary/matched reason counts, date/regime buckets, feature-missing counters и compact signal examples.

Обновлён `FoldFeatureRegimeRepairProbe`: теперь он агрегирует причину блокировок, готовность diagnostics, `verdict_detail` и умеет сравнивать lv31, lv32 и lv33 через единый board.

Исправлена propagation-цепочка для `fold_feature_regime_filter_summary` и `fold_time_slice_blackout_summary` через `label_grid_experiment_runner`, `feature_regime_experiment_runner`, multi-symbol analyzer и reporters, чтобы source-of-truth мог приходить из top-level payload, `profit_aware_diagnostics.summary` или `profit_aware_diagnostics.best_gate`.

Зарегистрированы lv33 adaptive feature/regime repair configs и добавлены в runtime shortlists `fast-debug` и `quick-quality`.

## Какие файлы изменены

- `app/evaluation/profit_aware_evaluator_v2.py`
- `app/diagnostics/fold_feature_regime_repair_probe.py`
- `app/experiments/label_grid_experiment_runner.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/ml38_2_fv3_tuning_matrix.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/labels/label_quality_grid.py`
- `run_fv3_cached_tuning.py`
- `tests/test_ml38_10_29_adaptive_feature_regime_repair_diagnostics.py`
- runtime-count regression tests under `tests/`

## Какие tests выполнены

- `python -m py_compile app/evaluation/profit_aware_evaluator_v2.py app/experiments/label_grid_experiment_runner.py app/experiments/feature_regime_experiment_runner.py app/diagnostics/fold_feature_regime_repair_probe.py app/labels/label_quality_grid.py app/experiments/ml38_2_fv3_tuning_matrix.py app/experiments/multi_symbol_feature_regime_analyzer.py app/experiments/multi_symbol_feature_regime_reporter.py app/experiments/feature_regime_experiment_reporter.py run_fv3_cached_tuning.py`
- `python -m pytest -q tests/test_ml38_10_29_adaptive_feature_regime_repair_diagnostics.py tests/test_ml38_10_28_feature_regime_fold_repair_filter.py tests/test_ml38_10_27_1_runtime_shortlist_config_registration.py`
- `python -m pytest -q`

## Что изменилось в runtime counts

- `FAST_DEBUG_CONFIGS`: `14 -> 16`
- `FAST_DEBUG expected candidates`: `28 -> 32`
- `QUICK_QUALITY_CONFIGS`: `30 -> 34`
- `QUICK_QUALITY expected candidates`: `30 -> 34`

## Что означает lv33

`lv33` это research-only stage `ML38.10.29` для adaptive feature/regime guard v2. Он не использует calendar-date blackout и вместо этого пробует более мягкий adaptive feature filter, ориентированный на bad target fold dates.

## Почему lv31/lv32/lv33 остаются research-only

Эти стадии являются repair probes: они нужны для диагностики и out-of-sample сравнения replacement-логики, а не для auto-acceptance. Они специально блокируются через `research_only_*` gate и не могут автоматически перейти в live-ready статус.

## Что ожидаем увидеть в fast-debug / quick-quality

- `fast-debug`: `expected_candidate_count=32`, `candidate_count=32`, `failed_candidate_count=0`, `accepted_candidate_count=0`
- `quick-quality --quick-quality-symbol SOLUSDT`: `expected_candidate_count=34`, `candidate_count=34`, `failed_candidate_count=0`, `accepted_candidate_count=0`
- В multi-symbol / feature-regime reports должен появиться board `ml38.10.29` с non-empty `aggregate_primary_removed_counts_by_reason` и compact adaptive repair diagnostics section.
