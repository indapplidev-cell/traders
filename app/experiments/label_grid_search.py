from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from app.baseline.baseline_evaluator import BaselineEvaluator
from app.baseline.baseline_models import BaselineModels
from app.dataset.dataset_builder import DatasetBuilder
from app.dataset.dataset_models import DatasetRow
from app.experiments.experiment_models import LabelGridCandidate
from app.experiments.experiment_reporter import ExperimentReporter
from app.labels.label_builder import LabelBuilder
from app.labels.label_config import LabelConfig


class LabelGridSearchService:
    HORIZONS = [4, 8, 12, 16]
    DIRECTION_THRESHOLDS = [0.3, 0.5, 0.8]
    TAKE_PROFITS = [1.0, 1.5, 2.0]
    STOP_LOSSES = [1.0]
    TRAIN_END = date(2025, 3, 1)
    VALIDATION_END = date(2025, 3, 16)

    def __init__(
        self,
        candle_repository,
        feature_repository,
        label_repository,
        dataset_builder: DatasetBuilder,
        baseline_service: BaselineService,
        reporter: ExperimentReporter | None = None,
        label_builder: LabelBuilder | None = None,
        baseline_evaluator: BaselineEvaluator | None = None,
    ) -> None:
        self._candle_repository = candle_repository
        self._feature_repository = feature_repository
        self._label_repository = label_repository
        self._dataset_builder = dataset_builder
        self._baseline_service = baseline_service
        self._reporter = reporter or ExperimentReporter()
        self._label_builder = label_builder or LabelBuilder()
        self._baseline_evaluator = baseline_evaluator or BaselineEvaluator()

    def run(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        start_at,
        end_at,
    ) -> dict[str, Any]:
        candles = self._candle_repository.get_range(symbol=symbol, interval=interval, start_at=start_at, end_at=end_at)
        feature_rows = self._feature_repository.get_all(symbol=symbol, interval=interval, feature_version=feature_version)
        candidates: list[LabelGridCandidate] = []

        for horizon_candles in self.HORIZONS:
            for threshold in self.DIRECTION_THRESHOLDS:
                for take_profit in self.TAKE_PROFITS:
                    for stop_loss in self.STOP_LOSSES:
                        label_version = self._build_label_version(horizon_candles, threshold, take_profit, stop_loss)
                        config = LabelConfig(
                            label_version=label_version,
                            horizon_candles=horizon_candles,
                            direction_atr_threshold=threshold,
                            take_profit_atr=take_profit,
                            stop_loss_atr=stop_loss,
                            flat_class_enabled=True,
                        )
                        labels = self._label_builder.build(
                            candles=candles,
                            symbol=symbol,
                            interval=interval,
                            horizon_candles=horizon_candles,
                            label_version=label_version,
                            config=config,
                        )
                        dataset_rows, dataset_summary = self._build_dataset_rows(feature_rows, labels)
                        split_rows = self._dataset_builder.split_rows(
                            dataset_rows,
                            train_end=self.TRAIN_END,
                            validation_end=self.VALIDATION_END,
                        )
                        baseline_report = self._evaluate_baselines(split_rows)
                        best_baseline_name, best_baseline_result = max(
                            baseline_report["baselines"].items(),
                            key=lambda item: (item[1]["test"]["accuracy"], -item[1]["test"]["brier_score"]),
                        )
                        test_counts = self._label_counts(split_rows["test"])
                        test_total = max(len(split_rows["test"]), 1)
                        flat_ratio = test_counts["FLAT"] / test_total
                        up_ratio = test_counts["UP"] / test_total
                        down_ratio = test_counts["DOWN"] / test_total
                        reject_reason = self._reject_reason(
                            dataset_rows=dataset_summary["dataset_rows"],
                            test_counts=test_counts,
                            best_baseline_accuracy=best_baseline_result["test"]["accuracy"],
                        )
                        candidate_score = self._candidate_score(
                            best_baseline_accuracy=best_baseline_result["test"]["accuracy"],
                            flat_ratio_test=flat_ratio,
                            up_ratio_test=up_ratio,
                            down_ratio_test=down_ratio,
                            reject_reason=reject_reason,
                        )
                        candidates.append(
                            LabelGridCandidate(
                                label_version=label_version,
                                horizon_candles=horizon_candles,
                                direction_atr_threshold=threshold,
                                take_profit_atr=take_profit,
                                stop_loss_atr=stop_loss,
                                dataset_rows=dataset_summary["dataset_rows"],
                                train_rows=len(split_rows["train"]),
                                validation_rows=len(split_rows["validation"]),
                                test_rows=len(split_rows["test"]),
                                label_counts_train=self._label_counts(split_rows["train"]),
                                label_counts_validation=self._label_counts(split_rows["validation"]),
                                label_counts_test=test_counts,
                                best_baseline_name=best_baseline_name,
                                best_baseline_accuracy=best_baseline_result["test"]["accuracy"],
                                flat_ratio_test=flat_ratio,
                                up_ratio_test=up_ratio,
                                down_ratio_test=down_ratio,
                                candidate_score=candidate_score,
                                reject_reason=reject_reason,
                            )
                        )

        candidates = sorted(candidates, key=lambda item: item.candidate_score, reverse=True)
        payload = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "candidates": [candidate.to_dict() for candidate in candidates],
        }
        payload["report_path"] = self._reporter.write_json(
            file_name=f"label_grid_search_{symbol.lower()}_{interval}.json",
            payload=payload,
        )
        return payload

    def _build_dataset_rows(self, feature_rows: list[Any], labels: list[Any]) -> tuple[list[DatasetRow], dict[str, Any]]:
        labels_by_open_time = {row.candle_open_time: row for row in labels}
        dataset_rows: list[DatasetRow] = []
        dropped_incomplete_features = 0
        dropped_missing_labels = 0

        for feature_row in feature_rows:
            if any(value is None for value in feature_row.features_json.values()):
                dropped_incomplete_features += 1
                continue
            label_row = labels_by_open_time.get(feature_row.candle_open_time)
            if label_row is None:
                dropped_missing_labels += 1
                continue
            dataset_rows.append(
                DatasetRow(
                    symbol=feature_row.symbol,
                    interval=feature_row.interval,
                    candle_open_time=feature_row.candle_open_time,
                    feature_version=feature_row.feature_version,
                    label_version=label_row.label_version,
                    horizon_candles=label_row.horizon_candles,
                    features_json=dict(feature_row.features_json),
                    direction_label=label_row.direction_label,
                    tp_before_sl=label_row.tp_before_sl,
                    future_return=float(label_row.future_return),
                    future_move_atr=float(label_row.future_move_atr),
                    max_favorable_move_atr=float(label_row.max_favorable_move_atr),
                    max_adverse_move_atr=float(label_row.max_adverse_move_atr),
                )
            )

        return dataset_rows, {
            "dataset_rows": len(dataset_rows),
            "dropped_incomplete_features": dropped_incomplete_features,
            "dropped_missing_labels": dropped_missing_labels,
        }

    def _evaluate_baselines(self, split_rows: dict[str, list[DatasetRow]]) -> dict[str, Any]:
        train_rows = split_rows["train"]
        validation_rows = split_rows["validation"]
        test_rows = split_rows["test"]
        baselines = {
            "always_flat": {
                "validation": self._baseline_evaluator.evaluate(validation_rows, BaselineModels.always_flat(validation_rows)),
                "test": self._baseline_evaluator.evaluate(test_rows, BaselineModels.always_flat(test_rows)),
            }
        }
        majority_label, validation_predictions = BaselineModels.majority_class(train_rows, validation_rows)
        _, test_predictions = BaselineModels.majority_class(train_rows, test_rows)
        baselines["majority_class"] = {
            "majority_class": majority_label,
            "validation": self._baseline_evaluator.evaluate(validation_rows, validation_predictions),
            "test": self._baseline_evaluator.evaluate(test_rows, test_predictions),
        }
        baselines["last_return_direction"] = {
            "threshold": 0.0005,
            "validation": self._baseline_evaluator.evaluate(validation_rows, BaselineModels.last_return_direction(validation_rows)),
            "test": self._baseline_evaluator.evaluate(test_rows, BaselineModels.last_return_direction(test_rows)),
        }
        baselines["simple_ema_trend"] = {
            "validation": self._baseline_evaluator.evaluate(validation_rows, BaselineModels.simple_ema_trend(validation_rows)),
            "test": self._baseline_evaluator.evaluate(test_rows, BaselineModels.simple_ema_trend(test_rows)),
        }
        return {"baselines": baselines}

    @staticmethod
    def _build_label_version(horizon_candles: int, threshold: float, take_profit: float, stop_loss: float) -> str:
        return (
            f"lv_h{horizon_candles}_thr{str(threshold).replace('.', '')}"
            f"_tp{str(take_profit).replace('.', '')}_sl{str(stop_loss).replace('.', '')}"
        )

    @staticmethod
    def _label_counts(rows: list[Any]) -> dict[str, int]:
        counts = Counter(row.direction_label for row in rows)
        return {"UP": counts.get("UP", 0), "DOWN": counts.get("DOWN", 0), "FLAT": counts.get("FLAT", 0)}

    @staticmethod
    def _reject_reason(dataset_rows: int, test_counts: dict[str, int], best_baseline_accuracy: float) -> str:
        test_total = sum(test_counts.values())
        ratios = {label: (count / test_total if test_total else 0.0) for label, count in test_counts.items()}
        if dataset_rows < 3000:
            return "dataset_too_small"
        if any(ratio > 0.70 for ratio in ratios.values()):
            return "class_distribution_too_imbalanced"
        if ratios["FLAT"] > 0.60:
            return "flat_ratio_too_high"
        if best_baseline_accuracy >= 0.45:
            return "baseline_too_strong"
        return "ok"

    @staticmethod
    def _candidate_score(
        best_baseline_accuracy: float,
        flat_ratio_test: float,
        up_ratio_test: float,
        down_ratio_test: float,
        reject_reason: str,
    ) -> float:
        if reject_reason != "ok":
            return 0.0
        balance_bonus = min(up_ratio_test, down_ratio_test, 1.0 - flat_ratio_test)
        return (1.0 - best_baseline_accuracy) + (1.0 - flat_ratio_test) + balance_bonus
