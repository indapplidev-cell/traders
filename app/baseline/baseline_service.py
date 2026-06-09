from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.baseline.baseline_evaluator import BaselineEvaluator
from app.baseline.baseline_models import BaselineModels
from app.config.settings import PROJECT_ROOT
from app.dataset.dataset_builder import DatasetBuilder


class BaselineService:
    def __init__(
        self,
        dataset_builder: DatasetBuilder,
        reports_dir: Path | None = None,
        evaluator: BaselineEvaluator | None = None,
    ) -> None:
        self._dataset_builder = dataset_builder
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._evaluator = evaluator or BaselineEvaluator()

    def evaluate(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end=None,
        validation_end=None,
    ) -> dict[str, Any]:
        dataset_rows, dataset_summary = self._dataset_builder.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        splits = self._dataset_builder.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        train_rows = splits["train"]
        validation_rows = splits["validation"]
        test_rows = splits["test"]

        baselines = {
            "always_flat": self._evaluate_baseline(
                validation_rows=validation_rows,
                test_rows=test_rows,
                validation_predictions=BaselineModels.always_flat(validation_rows),
                test_predictions=BaselineModels.always_flat(test_rows),
            ),
        }

        majority_label, validation_predictions = BaselineModels.majority_class(train_rows, validation_rows)
        _, test_predictions = BaselineModels.majority_class(train_rows, test_rows)
        baselines["majority_class"] = {
            "majority_class": majority_label,
            **self._evaluate_baseline(
                validation_rows=validation_rows,
                test_rows=test_rows,
                validation_predictions=validation_predictions,
                test_predictions=test_predictions,
            ),
        }

        baselines["last_return_direction"] = {
            "threshold": 0.0005,
            **self._evaluate_baseline(
                validation_rows=validation_rows,
                test_rows=test_rows,
                validation_predictions=BaselineModels.last_return_direction(validation_rows),
                test_predictions=BaselineModels.last_return_direction(test_rows),
            ),
        }

        baselines["simple_ema_trend"] = self._evaluate_baseline(
            validation_rows=validation_rows,
            test_rows=test_rows,
            validation_predictions=BaselineModels.simple_ema_trend(validation_rows),
            test_predictions=BaselineModels.simple_ema_trend(test_rows),
        )

        report = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "train_end": train_end.isoformat() if train_end is not None else None,
            "validation_end": validation_end.isoformat() if validation_end is not None else None,
            "dataset_summary": dataset_summary,
            "train_rows": len(train_rows),
            "validation_rows": len(validation_rows),
            "test_rows": len(test_rows),
            "baselines": baselines,
        }
        output_path = self._reports_dir / f"baseline_{symbol.lower()}_{interval}_h{horizon_candles}_{feature_version}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def _evaluate_baseline(
        self,
        validation_rows,
        test_rows,
        validation_predictions,
        test_predictions,
    ) -> dict[str, Any]:
        return {
            "validation": self._evaluator.evaluate(validation_rows, validation_predictions),
            "test": self._evaluator.evaluate(test_rows, test_predictions),
        }
