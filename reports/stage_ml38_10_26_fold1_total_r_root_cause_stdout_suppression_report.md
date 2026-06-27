# ML38.10.26 — Fold-1 total-R root cause, regime/time-slice repair and stdout payload suppression

## Цель

Убрать гигантский per-symbol stdout payload для runtime wrapper и добавить compact fold-level root-cause diagnostics для failed walk-forward validation gates, чтобы разбирать крупный negative total-R без дальнейшего blind threshold relaxation.

## Что изменено

- В `app.cli.commands` добавлен `build_ml38_2_fv3_tuning_stdout_payload(...)` и option `--stdout-payload-profile`.
- В `run_fv3_cached_tuning.py` wrapper теперь добавляет `--stdout-payload-profile minimal` и валидирует, что minimal stdout не содержит `candidate_results`.
- Добавлен новый diagnostic `app/diagnostics/walk_forward_fold_root_cause_diagnostics.py`.
- `walk_forward_evaluator`, `walk_forward_validation_candidate_board`, `walk_forward_profit_diagnostics`, `directional_side_signal_recovery_diagnostics`, `directional_side_walk_forward_stability`, `feature_regime_experiment_reporter`, `multi_symbol_feature_regime_analyzer`, `multi_symbol_feature_regime_reporter` протягивают compact root-cause payload до summary/report layer.

## Stdout suppression

- Minimal stdout profile сохраняет только status/count/path fields и tiny best-candidate preview.
- Heavy fields suppressed from stdout:
  - `candidate_results`
  - `ranking`
  - `configs_ranked`
  - fold arrays / nested validation boards / large diagnostics rows

## Fold root cause diagnostics

- Failed validation folds теперь получают `validation_fold_root_cause`.
- Candidate board хранит `worst_fold_root_cause`, `primary_root_cause_counts`, `fold_root_cause_count`.
- Multi-symbol analysis/report содержит compact `walk_forward_fold_root_cause_board`.

## Runtime counts

- fast-debug: 20
- quick-quality SOLUSDT: 21

## Safety

- live trading: disabled
- auto activation: disabled
- lv30 remains research-only
- direct traders-core execution integration: not touched

## Проверки

- py_compile: passed
- targeted pytest: passed
- full pytest: passed
