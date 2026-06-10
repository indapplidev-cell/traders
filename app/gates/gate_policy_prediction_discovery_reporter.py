"""JSON reporter для GatePolicy prediction discovery.

Модуль форматирует PredictionServiceDiscoveryReport для CLI/отчётов.
Он не импортирует prediction_service, не читает БД и не подключается
к traders-core.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from app.gates.gate_policy_prediction_discovery import (
    PredictionDiscoveryFile,
    PredictionServiceDiscoveryReport,
)


class GatePolicyPredictionDiscoveryReporter:
    """Сериализация prediction discovery report."""

    def file_to_dict(self, discovered_file: PredictionDiscoveryFile) -> dict[str, Any]:
        """Преобразовать найденный файл в JSON-safe словарь."""

        return discovered_file.to_dict()

    def report_to_dict(
        self,
        report: PredictionServiceDiscoveryReport,
        *,
        max_files: int | None = None,
    ) -> dict[str, Any]:
        """Преобразовать полный discovery report в JSON-safe словарь."""

        files = list(report.files)

        if max_files is not None:
            files = files[:max_files]

        return {
            "root_path": report.root_path,
            "scan_dirs": list(report.scan_dirs),
            "total_files": report.total_files,
            "files_with_content_matches": report.files_with_content_matches,
            "unique_name_keywords": list(self._unique_name_keywords(report)),
            "unique_content_keywords": list(report.unique_content_keywords),
            "name_keyword_counts": self._keyword_counts(
                item.matched_name_keywords
                for item in report.files
            ),
            "content_keyword_counts": self._keyword_counts(
                item.matched_content_keywords
                for item in report.files
            ),
            "shown_files": len(files),
            "files_truncated": max_files is not None and report.total_files > max_files,
            "files": [
                self.file_to_dict(item)
                for item in files
            ],
            "integration_status": {
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }

    def summary_to_dict(
        self,
        report: PredictionServiceDiscoveryReport,
    ) -> dict[str, Any]:
        """Преобразовать discovery report в короткую сводку."""

        return {
            "root_path": report.root_path,
            "scan_dirs": list(report.scan_dirs),
            "total_files": report.total_files,
            "files_with_content_matches": report.files_with_content_matches,
            "unique_name_keywords": list(self._unique_name_keywords(report)),
            "unique_content_keywords": list(report.unique_content_keywords),
            "name_keyword_counts": self._keyword_counts(
                item.matched_name_keywords
                for item in report.files
            ),
            "content_keyword_counts": self._keyword_counts(
                item.matched_content_keywords
                for item in report.files
            ),
            "integration_status": {
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }

    def report_to_json(
        self,
        report: PredictionServiceDiscoveryReport,
        *,
        max_files: int | None = None,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать полный discovery report в JSON."""

        return json.dumps(
            self.report_to_dict(report, max_files=max_files),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def summary_to_json(
        self,
        report: PredictionServiceDiscoveryReport,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать discovery summary в JSON."""

        return json.dumps(
            self.summary_to_dict(report),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def _unique_name_keywords(
        self,
        report: PredictionServiceDiscoveryReport,
    ) -> tuple[str, ...]:
        """Вернуть уникальные name keywords."""

        keywords: set[str] = set()

        for item in report.files:
            keywords.update(item.matched_name_keywords)

        return tuple(sorted(keywords))

    def _keyword_counts(
        self,
        keyword_groups: Iterable[tuple[str, ...]],
    ) -> dict[str, int]:
        """Посчитать частоту keyword по набору keyword-групп."""

        counter: Counter[str] = Counter()

        for group in keyword_groups:
            counter.update(group)

        return {
            key: counter[key]
            for key in sorted(counter)
        }
