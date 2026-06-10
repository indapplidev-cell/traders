"""Discovery существующих prediction/evaluation файлов для GatePolicy.

Модуль сканирует файлы проекта как текст и не импортирует реальные сервисы.
Это нужно, чтобы перед будущей интеграцией понять, где уже существуют
prediction/evaluation структуры.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SCAN_DIRS: tuple[str, ...] = (
    "app",
    "tests",
)

DEFAULT_FILE_NAME_KEYWORDS: tuple[str, ...] = (
    "predict",
    "prediction",
    "probability",
    "confidence",
    "baseline",
    "profit",
    "regime",
    "model",
    "evaluator",
    "evaluation",
)

DEFAULT_CONTENT_KEYWORDS: tuple[str, ...] = (
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
    "baseline",
    "profit_factor",
    "total_r",
    "regime",
)

IGNORED_DIR_NAMES: tuple[str, ...] = (
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)


@dataclass(frozen=True)
class PredictionDiscoveryFile:
    """Найденный prediction/evaluation файл."""

    path: str
    matched_name_keywords: tuple[str, ...]
    matched_content_keywords: tuple[str, ...]

    @property
    def has_content_matches(self) -> bool:
        """Есть ли совпадения по содержимому файла."""

        return bool(self.matched_content_keywords)

    def to_dict(self) -> dict[str, object]:
        """Преобразовать найденный файл в JSON-safe словарь."""

        return {
            "path": self.path,
            "matched_name_keywords": list(self.matched_name_keywords),
            "matched_content_keywords": list(self.matched_content_keywords),
            "has_content_matches": self.has_content_matches,
        }


@dataclass(frozen=True)
class PredictionServiceDiscoveryReport:
    """Отчёт discovery prediction/evaluation файлов."""

    root_path: str
    scan_dirs: tuple[str, ...]
    files: tuple[PredictionDiscoveryFile, ...]

    @property
    def total_files(self) -> int:
        """Количество найденных файлов."""

        return len(self.files)

    @property
    def files_with_content_matches(self) -> int:
        """Количество файлов, где были совпадения по содержимому."""

        return sum(1 for file in self.files if file.has_content_matches)

    @property
    def unique_content_keywords(self) -> tuple[str, ...]:
        """Уникальные найденные keywords по содержимому."""

        keywords: set[str] = set()

        for file in self.files:
            keywords.update(file.matched_content_keywords)

        return tuple(sorted(keywords))

    def to_dict(self) -> dict[str, object]:
        """Преобразовать discovery report в JSON-safe словарь."""

        return {
            "root_path": self.root_path,
            "scan_dirs": list(self.scan_dirs),
            "total_files": self.total_files,
            "files_with_content_matches": self.files_with_content_matches,
            "unique_content_keywords": list(self.unique_content_keywords),
            "files": [
                file.to_dict()
                for file in self.files
            ],
            "integration_status": {
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
            },
        }


class GatePolicyPredictionDiscoveryService:
    """Сервис поиска prediction/evaluation файлов без импорта проекта."""

    def __init__(
        self,
        *,
        scan_dirs: Iterable[str] = DEFAULT_SCAN_DIRS,
        file_name_keywords: Iterable[str] = DEFAULT_FILE_NAME_KEYWORDS,
        content_keywords: Iterable[str] = DEFAULT_CONTENT_KEYWORDS,
    ) -> None:
        self.scan_dirs = tuple(scan_dirs)
        self.file_name_keywords = tuple(file_name_keywords)
        self.content_keywords = tuple(content_keywords)

    def discover(self, root_path: str | Path = Path(".")) -> PredictionServiceDiscoveryReport:
        """Найти prediction/evaluation файлы в проекте."""

        root = Path(root_path)
        files: list[PredictionDiscoveryFile] = []

        for scan_dir in self.scan_dirs:
            base_path = root / scan_dir

            if not base_path.exists():
                continue

            for file_path in sorted(base_path.rglob("*.py")):
                if self._is_ignored(file_path):
                    continue

                discovered = self._inspect_file(root, file_path)

                if discovered is not None:
                    files.append(discovered)

        return PredictionServiceDiscoveryReport(
            root_path=str(root),
            scan_dirs=self.scan_dirs,
            files=tuple(files),
        )

    def _inspect_file(
        self,
        root_path: Path,
        file_path: Path,
    ) -> PredictionDiscoveryFile | None:
        """Проверить один файл на совпадения."""

        relative_path = self._safe_relative_path(root_path, file_path)
        path_text = str(relative_path).replace("\\", "/").lower()

        matched_name_keywords = tuple(
            keyword
            for keyword in self.file_name_keywords
            if keyword.lower() in path_text
        )

        content = self._read_text_safely(file_path).lower()

        matched_content_keywords = tuple(
            keyword
            for keyword in self.content_keywords
            if keyword.lower() in content
        )

        if not matched_name_keywords and not matched_content_keywords:
            return None

        return PredictionDiscoveryFile(
            path=str(relative_path).replace("\\", "/"),
            matched_name_keywords=matched_name_keywords,
            matched_content_keywords=matched_content_keywords,
        )

    def _is_ignored(self, file_path: Path) -> bool:
        """Проверить, нужно ли игнорировать файл."""

        return any(part in IGNORED_DIR_NAMES for part in file_path.parts)

    def _safe_relative_path(self, root_path: Path, file_path: Path) -> Path:
        """Безопасно получить относительный путь."""

        try:
            return file_path.relative_to(root_path)
        except ValueError:
            return file_path

    def _read_text_safely(self, file_path: Path) -> str:
        """Безопасно прочитать файл как текст."""

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="ignore")
