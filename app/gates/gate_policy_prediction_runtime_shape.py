"""Text-based discovery реальных prediction runtime shapes.

Модуль читает выбранные prediction/runtime файлы как текст.
Он не импортирует prediction_service, predictor, FastAPI routes, БД
и не подключается к traders-core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_RUNTIME_SHAPE_TARGETS: tuple[str, ...] = (
    "app/prediction/predictor.py",
    "app/prediction/prediction_service.py",
    "app/api/schemas.py",
    "tests/test_predictor.py",
    "tests/test_prediction_service.py",
    "tests/test_api_predict.py",
)

DEFAULT_RUNTIME_SHAPE_KEYWORDS: tuple[str, ...] = (
    "prob_up",
    "prob_down",
    "prob_flat",
    "confidence",
    "risk_score",
    "expected_move_atr",
    "tp_before_sl_probability",
    "model_version",
    "prediction",
    "predictor",
    "regime",
    "symbol",
    "interval",
    "candle",
    "candles",
    "model",
)


CLASS_PATTERN = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
FUNCTION_PATTERN = re.compile(
    r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PredictionRuntimeShapeFile:
    """Описание одного runtime prediction файла."""

    path: str
    exists: bool
    class_names: tuple[str, ...]
    function_names: tuple[str, ...]
    matched_keywords: tuple[str, ...]
    line_count: int

    @property
    def has_runtime_shape_signals(self) -> bool:
        """Есть ли признаки runtime shape в файле."""

        return bool(
            self.exists
            and (
                self.class_names
                or self.function_names
                or self.matched_keywords
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Преобразовать файл в JSON-safe словарь."""

        return {
            "path": self.path,
            "exists": self.exists,
            "class_names": list(self.class_names),
            "function_names": list(self.function_names),
            "matched_keywords": list(self.matched_keywords),
            "line_count": self.line_count,
            "has_runtime_shape_signals": self.has_runtime_shape_signals,
        }


@dataclass(frozen=True)
class PredictionRuntimeShapeReport:
    """Отчёт по prediction runtime shape discovery."""

    root_path: str
    target_paths: tuple[str, ...]
    files: tuple[PredictionRuntimeShapeFile, ...]

    @property
    def total_targets(self) -> int:
        """Количество целевых файлов."""

        return len(self.target_paths)

    @property
    def existing_targets(self) -> int:
        """Количество найденных файлов."""

        return sum(1 for item in self.files if item.exists)

    @property
    def missing_targets(self) -> int:
        """Количество отсутствующих файлов."""

        return self.total_targets - self.existing_targets

    @property
    def files_with_runtime_shape_signals(self) -> int:
        """Количество файлов с признаками runtime shape."""

        return sum(1 for item in self.files if item.has_runtime_shape_signals)

    @property
    def unique_class_names(self) -> tuple[str, ...]:
        """Уникальные class names."""

        names: set[str] = set()

        for item in self.files:
            names.update(item.class_names)

        return tuple(sorted(names))

    @property
    def unique_function_names(self) -> tuple[str, ...]:
        """Уникальные function names."""

        names: set[str] = set()

        for item in self.files:
            names.update(item.function_names)

        return tuple(sorted(names))

    @property
    def unique_keywords(self) -> tuple[str, ...]:
        """Уникальные matched keywords."""

        keywords: set[str] = set()

        for item in self.files:
            keywords.update(item.matched_keywords)

        return tuple(sorted(keywords))

    def to_dict(self) -> dict[str, object]:
        """Преобразовать report в JSON-safe словарь."""

        return {
            "root_path": self.root_path,
            "target_paths": list(self.target_paths),
            "total_targets": self.total_targets,
            "existing_targets": self.existing_targets,
            "missing_targets": self.missing_targets,
            "files_with_runtime_shape_signals": self.files_with_runtime_shape_signals,
            "unique_class_names": list(self.unique_class_names),
            "unique_function_names": list(self.unique_function_names),
            "unique_keywords": list(self.unique_keywords),
            "files": [
                item.to_dict()
                for item in self.files
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


class GatePolicyPredictionRuntimeShapeDiscoveryService:
    """Text-based discovery prediction runtime structures."""

    def __init__(
        self,
        *,
        target_paths: Iterable[str] = DEFAULT_RUNTIME_SHAPE_TARGETS,
        keywords: Iterable[str] = DEFAULT_RUNTIME_SHAPE_KEYWORDS,
    ) -> None:
        self.target_paths = tuple(target_paths)
        self.keywords = tuple(keywords)

    def discover(self, root_path: str | Path = Path(".")) -> PredictionRuntimeShapeReport:
        """Собрать runtime shape report по целевым файлам."""

        root = Path(root_path)
        files = tuple(
            self._inspect_target(root, target_path)
            for target_path in self.target_paths
        )

        return PredictionRuntimeShapeReport(
            root_path=str(root),
            target_paths=self.target_paths,
            files=files,
        )

    def _inspect_target(
        self,
        root_path: Path,
        target_path: str,
    ) -> PredictionRuntimeShapeFile:
        """Проверить один целевой файл."""

        file_path = root_path / target_path

        if not file_path.exists():
            return PredictionRuntimeShapeFile(
                path=target_path,
                exists=False,
                class_names=(),
                function_names=(),
                matched_keywords=(),
                line_count=0,
            )

        content = self._read_text_safely(file_path)
        lower_content = content.lower()

        class_names = tuple(CLASS_PATTERN.findall(content))
        function_names = tuple(FUNCTION_PATTERN.findall(content))
        matched_keywords = tuple(
            keyword
            for keyword in self.keywords
            if keyword.lower() in lower_content
        )

        return PredictionRuntimeShapeFile(
            path=target_path,
            exists=True,
            class_names=class_names,
            function_names=function_names,
            matched_keywords=matched_keywords,
            line_count=len(content.splitlines()),
        )

    def _read_text_safely(self, file_path: Path) -> str:
        """Безопасно прочитать файл как текст."""

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="ignore")
