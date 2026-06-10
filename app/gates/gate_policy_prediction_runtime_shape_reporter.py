"""JSON reporter для prediction runtime shape discovery.

Модуль форматирует PredictionRuntimeShapeReport для CLI/отчётов.
Он не импортирует prediction_service, predictor, БД и не подключается
к traders-core.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from app.gates.gate_policy_prediction_runtime_shape import (
    PredictionRuntimeShapeFile,
    PredictionRuntimeShapeReport,
)


class GatePolicyPredictionRuntimeShapeReporter:
    """Сериализация prediction runtime shape report."""

    def file_to_dict(self, runtime_file: PredictionRuntimeShapeFile) -> dict[str, Any]:
        """Преобразовать один runtime shape file в JSON-safe словарь."""

        return runtime_file.to_dict()

    def report_to_dict(
        self,
        report: PredictionRuntimeShapeReport,
        *,
        max_files: int | None = None,
    ) -> dict[str, Any]:
        """Преобразовать полный runtime shape report в JSON-safe словарь."""

        files = list(report.files)

        if max_files is not None:
            files = files[:max_files]

        return {
            "root_path": report.root_path,
            "target_paths": list(report.target_paths),
            "total_targets": report.total_targets,
            "existing_targets": report.existing_targets,
            "missing_targets": report.missing_targets,
            "files_with_runtime_shape_signals": report.files_with_runtime_shape_signals,
            "unique_class_names": list(report.unique_class_names),
            "unique_function_names": list(report.unique_function_names),
            "unique_keywords": list(report.unique_keywords),
            "class_name_counts": self._value_counts(
                item.class_names
                for item in report.files
            ),
            "function_name_counts": self._value_counts(
                item.function_names
                for item in report.files
            ),
            "keyword_counts": self._value_counts(
                item.matched_keywords
                for item in report.files
            ),
            "shown_files": len(files),
            "files_truncated": max_files is not None and report.total_targets > max_files,
            "files": [
                self.file_to_dict(item)
                for item in files
            ],
            "integration_status": {
                "prediction_service_imported": False,
                "predictor_imported": False,
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }

    def summary_to_dict(
        self,
        report: PredictionRuntimeShapeReport,
    ) -> dict[str, Any]:
        """Преобразовать runtime shape report в compact summary."""

        return {
            "root_path": report.root_path,
            "target_paths": list(report.target_paths),
            "total_targets": report.total_targets,
            "existing_targets": report.existing_targets,
            "missing_targets": report.missing_targets,
            "files_with_runtime_shape_signals": report.files_with_runtime_shape_signals,
            "unique_class_names": list(report.unique_class_names),
            "unique_function_names": list(report.unique_function_names),
            "unique_keywords": list(report.unique_keywords),
            "class_name_counts": self._value_counts(
                item.class_names
                for item in report.files
            ),
            "function_name_counts": self._value_counts(
                item.function_names
                for item in report.files
            ),
            "keyword_counts": self._value_counts(
                item.matched_keywords
                for item in report.files
            ),
            "integration_status": {
                "prediction_service_imported": False,
                "predictor_imported": False,
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }

    def report_to_json(
        self,
        report: PredictionRuntimeShapeReport,
        *,
        max_files: int | None = None,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать полный runtime shape report в JSON."""

        return json.dumps(
            self.report_to_dict(report, max_files=max_files),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def summary_to_json(
        self,
        report: PredictionRuntimeShapeReport,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать runtime shape summary в JSON."""

        return json.dumps(
            self.summary_to_dict(report),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def _value_counts(
        self,
        value_groups: Iterable[tuple[str, ...]],
    ) -> dict[str, int]:
        """Посчитать частоту значений в группах."""

        counter: Counter[str] = Counter()

        for group in value_groups:
            counter.update(group)

        return {
            key: counter[key]
            for key in sorted(counter)
        }
