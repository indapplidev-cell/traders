#!/usr/bin/env python
"""Очистка runtime-мусора и технический commit в traders-ml.

Назначение:
- показать текущий git status;
- удалить временные runtime-отчёты, cache и архивы из рабочей папки проекта;
- восстановить изменённые tracked runtime JSON/MD отчёты;
- НЕ трогать runtime-мусор в commit;
- сделать технический commit для оставшихся новых/изменённых файлов проекта;
- после очистки и commit автоматически собрать light project archive.

Логика commit message:
- если есть только изменённые tracked-файлы: "новые изменения";
- если есть только новые untracked-файлы: "новые файлы";
- если есть и новые, и изменённые: "добавлены и изменены".

Запуск из корня проекта:
    python clean_traders_ml.py

Безопасный режим без удаления и без commit:
    python clean_traders_ml.py --dry-run

Только очистить мусор, без commit:
    python clean_traders_ml.py --no-commit

Отключить автоматическую сборку project archive:
    python clean_traders_ml.py --no-project-archive

Разрешить commit удалённых файлов:
    python clean_traders_ml.py --include-deletions
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


RUNTIME_PATHS_TO_CLEAN = [
    "reports/feature_regime_experiments/",
    "reports/label_grid_experiments/",
    "reports/project_archives/",
]

RUNTIME_REPORT_PATTERNS = [
    "reports/baseline_*.json",
    "reports/calibration_eval_*.json",
    "reports/dataset_summary_*.json",
    "reports/model_comparison_*.json",
    "reports/model_diagnostics_*.json",
    "reports/multi_symbol_feature_regime_analysis.json",
    "reports/multi_symbol_feature_regime_analysis.md",
    "reports/probability_diagnostics_*.json",
    "reports/profit_eval_v2_*.json",
    "reports/walk_forward_eval_*.json",
]

CACHE_PATHS_TO_CLEAN = [
    ".pytest_cache/",
    "htmlcov/",
]

# Эти пути нельзя удалять никакой runtime-очисткой.
# Даже если они ignored в .gitignore, cleaner обязан их защищать.
PROTECTED_CLEANUP_ROOT_NAMES = {
    ".git",
    ".venv",
    ".venv_broken",
    "venv",
    "env",
    "artifacts",
}

PYTHON_CACHE_PATTERNS_TO_CLEAN = [
    "__pycache__",
    "**/__pycache__",
    "**/*.pyc",
]

# Архивы проекта обычно появляются после ручной упаковки или передачи в чат.
# Их нельзя коммитить в репозиторий traders-ml.
ARCHIVE_PATTERNS_TO_CLEAN = [
    "*.zip",
    "*.7z",
    "*.rar",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
]

# Эти пути никогда не должны попадать в технический commit.
NEVER_COMMIT_PATTERNS = [
    "reports/*",
    ".pytest_cache/*",
    "htmlcov/*",
    "*.zip",
    "*.7z",
    "*.rar",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "__pycache__/*",
    "*.pyc",
]

# Нормальные проектные зоны, которые можно коммитить техническим commit-ом.
# Это защита от случайного commit-а мусора из корня проекта.
COMMIT_ALLOWED_PREFIXES = [
    "app/",
    "tests/",
    "alembic/",
    "migrations/",
    "docs/",
    "scripts/",
    "packer/",
]

COMMIT_ALLOWED_EXACT_FILES = {
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "alembic.ini",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "run_fv3_cached_tuning.py",
    "clean_traders_ml_runtime.py",
    "clean_traders_ml.py",
}


# Удаления, которые разрешены без --include-deletions при переезде служебных файлов.
COMMIT_ALLOWED_DELETION_EXACT_FILES = {
    "clean_traders_ml_runtime.py",
    "pack_traders_ml_project.py",
    "project_packager.py",
    "pack_traders_ml_project_percent_progress_clean.patch",
    "clean_runtime_packer_progress_passthrough_clean.patch",
}

CLEANER_LOG_PATH: Path | None = None

TECHNICAL_COMMIT_MESSAGES = {
    "modified_only": "новые изменения",
    "new_only": "новые файлы",
    "mixed": "добавлены и изменены",
}

MODEL_ARTIFACT_ROOT = Path("artifacts/models")
DEFAULT_KEEP_LAST_MODELS = 10
DEFAULT_PROJECT_ARCHIVE_OUTPUT = "reports/project_archives/after_38_10_14_3_traders-ml-light.zip"


def _init_cleaner_log(root: Path) -> Path:
    """Создаёт файл полного лога cleaner-а."""
    global CLEANER_LOG_PATH
    log_dir = root / "reports" / "cleaner_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    CLEANER_LOG_PATH = log_dir / f"clean_traders_ml_{timestamp}.log"
    CLEANER_LOG_PATH.write_text(
        f"clean_traders_ml.py log started_at_utc={datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return CLEANER_LOG_PATH


def _log_detail(message: str) -> None:
    """Пишет подробную строку в cleaner log, не засоряя терминал."""
    if CLEANER_LOG_PATH is None:
        return
    with CLEANER_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(message.rstrip() + "\n")


def _compact_progress(label: str, current: int, total: int) -> None:
    """Одна перерисовываемая строка прогресса в терминале."""
    if total <= 0:
        line = f"{label}: {0:>6}/{0:<6} {100.0:>7.2f}%"
        print(line)
        return

    percent = current / total * 100.0
    line = f"{label}: {current:>6}/{total:<6} {percent:>7.2f}%"
    sys.stdout.write("\r" + line)
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def _emit_detail_group(label: str, lines: list[str]) -> None:
    """Компактный прогресс в терминал + полный список в log."""
    total = len(lines)
    if total == 0:
        return
    for index, line in enumerate(lines, start=1):
        _log_detail(f"{label}: {line}")
        _compact_progress(label, index, total)



@dataclass(frozen=True)
class StatusEntry:
    """Одна строка git status --porcelain."""

    index_status: str
    worktree_status: str
    path: str
    original_path: str | None = None

    @property
    def is_untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"

    @property
    def is_ignored(self) -> bool:
        return self.index_status == "!" and self.worktree_status == "!"

    @property
    def is_conflict(self) -> bool:
        pair = f"{self.index_status}{self.worktree_status}"
        return pair in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}

    @property
    def is_deleted(self) -> bool:
        return self.index_status == "D" or self.worktree_status == "D"

    @property
    def is_new(self) -> bool:
        return self.is_untracked or self.index_status == "A" or self.worktree_status == "A"

    @property
    def is_modified_like(self) -> bool:
        if self.is_untracked or self.is_ignored:
            return False
        return any(status in {"M", "D", "R", "C", "T"} for status in (self.index_status, self.worktree_status))


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Запускает git-команду и печатает её вывод."""
    command = ["git", *args]
    _log_detail("COMMAND: " + " ".join(command))
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.stdout.strip():
        print(result.stdout.rstrip())
        _log_detail("STDOUT:\n" + result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
        _log_detail("STDERR:\n" + result.stderr.rstrip())

    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}")

    return result


def ensure_git_repo() -> Path:
    """Проверяет, что скрипт запущен внутри git-репозитория traders-ml."""
    result = run_git(["rev-parse", "--show-toplevel"], check=False)
    if result.returncode != 0:
        raise SystemExit("Ошибка: скрипт нужно запускать внутри git-репозитория traders-ml.")

    root = Path(result.stdout.strip()).resolve()
    cwd = Path.cwd().resolve()
    print(f"Git root: {root}")
    print(f"Current dir: {cwd}")

    if not (root / "app").exists() or not (root / "reports").exists():
        raise SystemExit(
            "Ошибка: это не похоже на корень traders-ml. "
            "Запусти скрипт из D:\\disk_E\\game_projects\\traders\\traders-ml"
        )

    return root


def print_status(title: str) -> None:
    """Печатает короткий git status."""
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)
    result = run_git(["status", "--short"], check=False)
    if not result.stdout.strip():
        print("git status --short: clean")


def _matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _tracked_runtime_report_files() -> list[str]:
    """Возвращает tracked runtime-отчёты, которые можно безопасно откатить.

    Важно: используем git ls-files, чтобы не передавать git restore pathspec-ы,
    которых нет в индексе. Иначе git restore падает и не откатывает даже
    существующие tracked отчёты.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        return []

    tracked_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    matches: set[str] = set()
    for path in tracked_files:
        for pattern in RUNTIME_REPORT_PATTERNS:
            if fnmatch.fnmatch(path, pattern):
                matches.add(path)
                break
    return sorted(matches)


def restore_tracked_runtime_reports(dry_run: bool) -> None:
    """Откатывает изменения только в tracked runtime-отчётах reports/."""
    print()
    print("=" * 88)
    print("Restore tracked runtime reports")
    print("=" * 88)

    matched_files = _tracked_runtime_report_files()
    if not matched_files:
        print("No tracked runtime report files matched restore patterns.")
        _log_detail("No tracked runtime report files matched restore patterns.")
        return

    _emit_detail_group("Matched tracked runtime reports", matched_files)

    args = ["restore", "--worktree", "--staged", "--", *matched_files]

    if dry_run:
        print("DRY RUN: git " + " ".join(args))
        _log_detail("DRY RUN: git " + " ".join(args))
        return

    run_git(args, check=True)


def _relative_display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_protected_cleanup_path(root: Path, path: Path) -> bool:
    """Запрещает runtime-cleaner удалять .venv, .git, artifacts и другие корневые зоны."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True

    if not relative.parts:
        return True

    return relative.parts[0] in PROTECTED_CLEANUP_ROOT_NAMES


def _iter_project_tree_without_protected_roots(root: Path):
    """os.walk по проекту без .venv/.git/artifacts, чтобы не сканировать гигантские protected trees."""
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if current == root:
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in PROTECTED_CLEANUP_ROOT_NAMES
            ]
        yield current, dirnames, filenames


def _expand_cleanup_patterns(root: Path, patterns: list[str]) -> list[Path]:
    """Раскрывает cleanup patterns без прохода по protected root-директориям.

    Важно:
    - не сканируем .venv/.git/artifacts для **/*.pyc и **/__pycache__;
    - если pattern указывает на директорию с trailing slash, возвращаем её детей;
    - tracked historical reports не удаляются дальше через tracked guard.
    """
    result: list[Path] = []

    for pattern in patterns:
        normalized = pattern.replace("\\", "/").strip()
        if not normalized:
            continue

        if normalized == "**/*.pyc":
            for current, _, filenames in _iter_project_tree_without_protected_roots(root):
                for filename in filenames:
                    if filename.endswith(".pyc"):
                        result.append(current / filename)
            continue

        if normalized == "**/__pycache__":
            for current, dirnames, _ in _iter_project_tree_without_protected_roots(root):
                for dirname in dirnames:
                    if dirname == "__pycache__":
                        result.append(current / dirname)
            continue

        if normalized == "__pycache__":
            path = root / normalized
            if path.exists():
                result.append(path)
            continue

        if any(symbol in normalized for symbol in "*?["):
            result.extend(root.glob(normalized))
            continue

        path = root / normalized

        if normalized.endswith("/") and path.exists() and path.is_dir():
            result.extend(path.iterdir())
            continue

        result.append(path)

    return result


def _git_tracked_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        return set()

    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }


def _is_tracked_or_contains_tracked_path(
    *,
    root: Path,
    path: Path,
    tracked_paths: set[str],
) -> bool:
    relative_path = _relative_display_path(root, path).rstrip("/")

    if relative_path in tracked_paths:
        return True

    if path.is_dir():
        prefix = f"{relative_path}/"
        return any(tracked_path.startswith(prefix) for tracked_path in tracked_paths)

    return False


def _collect_runtime_cleanup_candidates(root: Path) -> list[Path]:
    """Собирает только явно разрешённые runtime/cache/report targets.

    Терминал получает compact progress, полный список уходит в reports/cleaner_logs/*.log.
    """
    patterns = [
        *RUNTIME_PATHS_TO_CLEAN,
        *RUNTIME_REPORT_PATTERNS,
        *ARCHIVE_PATTERNS_TO_CLEAN,
        *CACHE_PATHS_TO_CLEAN,
        *PYTHON_CACHE_PATTERNS_TO_CLEAN,
    ]

    tracked_paths = _git_tracked_paths(root)
    expanded_paths = _expand_cleanup_patterns(root, patterns)
    _log_detail(f"Expanded cleanup path count: {len(expanded_paths)}")

    candidates: list[Path] = []
    protected_skips: list[str] = []
    tracked_skips: list[str] = []

    total = len(expanded_paths)
    if total:
        for index, path in enumerate(expanded_paths, start=1):
            _compact_progress("Prepare cleanup scan", index, total)
            if not path.exists():
                _log_detail(f"SKIP missing cleanup path: {_relative_display_path(root, path)}")
                continue

            if _is_protected_cleanup_path(root, path):
                protected_skips.append(_relative_display_path(root, path))
                continue

            if _is_tracked_or_contains_tracked_path(
                root=root,
                path=path,
                tracked_paths=tracked_paths,
            ):
                tracked_skips.append(_relative_display_path(root, path))
                continue

            candidates.append(path)
    else:
        _compact_progress("Prepare cleanup scan", 0, 0)

    _emit_detail_group("SKIP protected cleanup path", protected_skips)
    _emit_detail_group("SKIP tracked cleanup path", tracked_skips)

    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve())] = path

    return sorted(
        unique.values(),
        key=lambda item: (len(item.resolve().parts), str(item.resolve())),
        reverse=True,
    )


def _remove_runtime_cleanup_candidate(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def clean_untracked_runtime_files(*, root: Path, dry_run: bool) -> None:
    """Удаляет только явно разрешённые runtime-файлы, cache и архивы."""
    print()
    print("=" * 88)
    print("Clean runtime files")
    print("=" * 88)

    candidates = _collect_runtime_cleanup_candidates(root)

    if not candidates:
        print("No runtime cleanup candidates found.")
        _log_detail("No runtime cleanup candidates found.")
        return

    candidate_lines = [
        f"Would remove {_relative_display_path(root, path)}"
        for path in candidates
    ]
    _emit_detail_group("Cleanup candidates", candidate_lines)

    if dry_run:
        print("DRY RUN: удаление не выполнялось.")
        _log_detail("DRY RUN: cleanup deletion was not applied.")
        return

    removal_lines = [
        _relative_display_path(root, path)
        for path in candidates
    ]
    for index, path in enumerate(candidates, start=1):
        display_path = _relative_display_path(root, path)
        _log_detail(f"Removing: {display_path}")
        _compact_progress("Removing", index, len(candidates))
        _remove_runtime_cleanup_candidate(path)


def _safe_dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def _model_artifact_dirs(root: Path) -> list[Path]:
    model_root = root / MODEL_ARTIFACT_ROOT
    if not model_root.exists():
        return []
    return sorted(
        [path for path in model_root.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _active_model_artifact_paths() -> tuple[set[str], str | None]:
    try:
        from sqlalchemy import select

        from app.db.models import MlModelVersions
        from app.db.session import get_session

        active_paths: set[str] = set()
        with get_session() as session:
            rows = list(
                session.scalars(
                    select(MlModelVersions).where(MlModelVersions.is_active.is_(True))
                )
            )
            for row in rows:
                if row.artifact_path:
                    active_paths.add(str(row.artifact_path).replace("\\", "/"))
        return active_paths, None
    except Exception as exc:
        return set(), f"{type(exc).__name__}: {exc}"


def _is_active_artifact_dir(path: Path, active_paths: set[str]) -> bool:
    normalized = path.as_posix()
    for active_path in active_paths:
        if active_path and (active_path in normalized or normalized in active_path):
            return True
    return False


def cleanup_model_artifacts(
    *,
    root: Path,
    keep_last_models: int,
    apply: bool,
    force_without_db: bool,
) -> None:
    print()
    print("=" * 88)
    print("Model artifact retention cleanup")
    print("=" * 88)

    model_dirs = _model_artifact_dirs(root)
    model_root = root / MODEL_ARTIFACT_ROOT
    print(f"Model artifact root: {model_root}")
    print(f"Model directory count: {len(model_dirs)}")
    print(f"Keep last models: {keep_last_models}")

    if not model_dirs:
        print("No model artifact directories found.")
        return

    active_paths, db_error = _active_model_artifact_paths()
    if db_error:
        print(f"Active model DB check failed: {db_error}")
        if apply and not force_without_db:
            raise SystemExit(
                "Refusing to delete model artifacts because active-model DB check failed. "
                "Use --models-force-without-db only if you intentionally accept this risk."
            )
    else:
        print(f"Active model artifact paths from DB: {len(active_paths)}")

    keep_last_models = max(0, int(keep_last_models))
    kept_by_recency = set(model_dirs[:keep_last_models])
    delete_candidates: list[Path] = []
    protected_active: list[Path] = []

    for path in model_dirs:
        if path in kept_by_recency:
            continue
        if _is_active_artifact_dir(path, active_paths):
            protected_active.append(path)
            continue
        delete_candidates.append(path)

    bytes_to_delete = sum(_safe_dir_size_bytes(path) for path in delete_candidates)
    print(f"Delete candidate count: {len(delete_candidates)}")
    print(f"Protected active count: {len(protected_active)}")
    print(f"Estimated bytes to delete: {bytes_to_delete}")
    print(f"Estimated MB to delete: {bytes_to_delete / (1024 * 1024):.3f}")

    print()
    print("Newest kept directories:")
    for path in model_dirs[:keep_last_models]:
        print(f"  KEEP {path}")

    print()
    print("Delete candidates:")
    for path in delete_candidates[:50]:
        print(f"  DELETE {path}")
    if len(delete_candidates) > 50:
        print(f"  ... and {len(delete_candidates) - 50} more")

    if protected_active:
        print()
        print("Protected active model dirs:")
        for path in protected_active:
            print(f"  ACTIVE_KEEP {path}")

    if not apply:
        print()
        print("DRY RUN: model artifacts were not deleted.")
        return

    for path in delete_candidates:
        shutil.rmtree(path)
    print(f"Deleted model artifact dirs: {len(delete_candidates)}")


def _parse_porcelain_line(line: str) -> StatusEntry | None:
    """Парсит строку git status --porcelain v1.

    Поддерживает обычные строки и rename/copy формат: "R  old -> new".
    """
    if not line:
        return None
    if len(line) < 4:
        return None

    index_status = line[0]
    worktree_status = line[1]
    path_part = line[3:]

    original_path: str | None = None
    path = path_part
    if " -> " in path_part:
        original_path, path = path_part.split(" -> ", 1)

    return StatusEntry(
        index_status=index_status,
        worktree_status=worktree_status,
        path=path.strip(),
        original_path=original_path.strip() if original_path else None,
    )


def get_status_entries() -> list[StatusEntry]:
    """Возвращает текущий git status --porcelain."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError("Не удалось получить git status --porcelain")

    entries: list[StatusEntry] = []
    for line in result.stdout.splitlines():
        entry = _parse_porcelain_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def _is_commit_allowed_path(path: str, *, is_deletion: bool = False) -> bool:
    """Проверяет, можно ли путь включать в технический commit."""
    normalized = path.replace("\\", "/").rstrip("/")

    if is_deletion and normalized in COMMIT_ALLOWED_DELETION_EXACT_FILES:
        return True

    normalized_for_match = path.replace("\\", "/")

    if _matches_any(normalized_for_match, NEVER_COMMIT_PATTERNS):
        return False

    if normalized in COMMIT_ALLOWED_EXACT_FILES or normalized_for_match in COMMIT_ALLOWED_EXACT_FILES:
        return True

    return any(normalized_for_match.startswith(prefix) for prefix in COMMIT_ALLOWED_PREFIXES)


def _select_commit_entries(
    entries: list[StatusEntry],
    *,
    include_deletions: bool,
) -> tuple[list[StatusEntry], list[StatusEntry], list[StatusEntry]]:
    """Разделяет изменения на commit-ready, skipped и conflicts."""
    commit_entries: list[StatusEntry] = []
    skipped_entries: list[StatusEntry] = []
    conflict_entries: list[StatusEntry] = []

    for entry in entries:
        if entry.is_ignored:
            continue
        if entry.is_conflict:
            conflict_entries.append(entry)
            continue

        is_safe_service_deletion = (
            entry.is_deleted
            and entry.path.replace("\\", "/").rstrip("/") in COMMIT_ALLOWED_DELETION_EXACT_FILES
        )

        if entry.is_deleted and not include_deletions and not is_safe_service_deletion:
            skipped_entries.append(entry)
            continue

        if not _is_commit_allowed_path(entry.path, is_deletion=entry.is_deleted):
            skipped_entries.append(entry)
            continue

        commit_entries.append(entry)

    return commit_entries, skipped_entries, conflict_entries


def _commit_message_for(entries: list[StatusEntry]) -> str:
    """Выбирает техническое сообщение commit-а по типу изменений."""
    has_new = any(entry.is_new for entry in entries)
    has_modified = any(entry.is_modified_like for entry in entries)

    if has_new and has_modified:
        return TECHNICAL_COMMIT_MESSAGES["mixed"]
    if has_new:
        return TECHNICAL_COMMIT_MESSAGES["new_only"]
    return TECHNICAL_COMMIT_MESSAGES["modified_only"]


def _unique_paths(entries: list[StatusEntry]) -> list[str]:
    """Возвращает уникальные пути в стабильном порядке."""
    result: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.path not in seen:
            seen.add(entry.path)
            result.append(entry.path)
    return result


def _commit_paths_for_entries(root: Path, entries: list[StatusEntry]) -> list[str]:
    """Раскрывает untracked-директории в конкретные файлы, чтобы не добавить мусор."""
    paths: list[str] = []
    seen: set[str] = set()

    for entry in entries:
        normalized = entry.path.replace("\\", "/")
        absolute = root / normalized

        if entry.is_deleted:
            if normalized not in seen:
                seen.add(normalized)
                paths.append(normalized)
            continue

        if entry.is_untracked and absolute.exists() and absolute.is_dir():
            for item in sorted(absolute.rglob("*")):
                if not item.is_file():
                    continue
                rel = item.relative_to(root).as_posix()
                if _is_commit_allowed_path(rel, is_deletion=False) and rel not in seen:
                    seen.add(rel)
                    paths.append(rel)
            continue

        if normalized not in seen:
            seen.add(normalized)
            paths.append(normalized)

    return paths


def create_technical_commit(
    *,
    root: Path,
    dry_run: bool,
    include_deletions: bool,
    no_commit: bool,
) -> None:
    """Делает технический commit для оставшихся новых/изменённых проектных файлов."""
    print()
    print("=" * 88)
    print("Technical commit")
    print("=" * 88)

    if no_commit:
        print("Commit отключён флагом --no-commit.")
        _log_detail("Commit disabled by --no-commit.")
        return

    entries = get_status_entries()
    if not entries:
        print("Нет изменений для commit.")
        _log_detail("No changes for commit.")
        return

    commit_entries, skipped_entries, conflict_entries = _select_commit_entries(
        entries,
        include_deletions=include_deletions,
    )

    if conflict_entries:
        conflict_lines = [
            f"{entry.index_status}{entry.worktree_status} {entry.path}"
            for entry in conflict_entries
        ]
        _emit_detail_group("Conflict commit entries", conflict_lines)
        raise SystemExit("Сначала разреши git conflicts вручную.")

    if skipped_entries:
        skipped_lines = [
            f"{entry.index_status}{entry.worktree_status} {entry.path}"
            for entry in skipped_entries
        ]
        _emit_detail_group("Skipped commit entries", skipped_lines)

    if not commit_entries:
        print("Нет разрешённых проектных изменений для technical commit.")
        _log_detail("No allowed project changes for technical commit.")
        return

    paths = _commit_paths_for_entries(root, commit_entries)
    if not paths:
        print("Нет разрешённых файлов после раскрытия директорий для technical commit.")
        _log_detail("No allowed files after expanding commit directories.")
        return

    message = _commit_message_for(commit_entries)

    _emit_detail_group("Files for technical commit", paths)
    print(f"Commit message: {message}")
    _log_detail(f"Commit message: {message}")

    if dry_run:
        print("DRY RUN: git add -- " + " ".join(paths))
        print(f"DRY RUN: git commit -m {message!r}")
        _log_detail("DRY RUN: git add -- " + " ".join(paths))
        _log_detail(f"DRY RUN: git commit -m {message!r}")
        return

    run_git(["add", "--", *paths], check=True)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if staged.returncode == 0:
        print("После git add нет staged изменений. Commit не нужен.")
        _log_detail("No staged changes after git add.")
        return

    run_git(["commit", "-m", message], check=True)


def _run_command_passthrough(
    command: list[str],
    *,
    cwd: Path,
) -> None:
    """Запускает команду напрямую и оставляет её stdout/stderr видимыми в терминале.

    Процентный прогресс теперь печатает сам pack_traders_ml_project.py, потому что
    только packer знает total files и текущий добавляемый файл.
    """
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
    )
    returncode = process.wait()

    if returncode != 0:
        raise RuntimeError(f"Command failed with exit code {returncode}: {' '.join(command)}")


def build_project_archive(*, root: Path, output: str, dry_run: bool, disabled: bool) -> None:
    """Собирает lightweight project archive после cleanup и technical commit.

    Важно:
    - запуск идёт через текущий Python interpreter, чтобы использовать активную .venv;
    - output передаётся в packer/pack_traders_ml_project.py как отдельный аргумент;
    - archive создаётся после warn_if_changes_remain(), поэтому ожидаемый untracked zip
      не мешает проверке чистоты рабочей папки после commit;
    - процентный прогресс печатает packer/pack_traders_ml_project.py по каждому
      добавленному файлу.
    """
    print()
    print("=" * 88)
    print("Build project archive")
    print("=" * 88)

    if disabled:
        print("Project archive build отключён флагом --no-project-archive.")
        return

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path

    command = [
        sys.executable,
        "packer/pack_traders_ml_project.py",
        "--output",
        str(output_path),
        "--max-archive-size-mb",
        "100",
    ]

    print("Archive output:", output_path)
    print("Command:", " ".join(command))

    if dry_run:
        print("DRY RUN: project archive не собирался.")
        return

    _run_command_passthrough(
        command,
        cwd=root,
    )

    if not output_path.exists():
        raise RuntimeError(f"Project archive was not created: {output_path}")

    print(f"Project archive created: {output_path}")

def warn_if_changes_remain() -> None:
    """Показывает, остались ли изменения, которые скрипт не должен трогать."""
    result = run_git(["status", "--short"], check=False)
    remaining = [line for line in result.stdout.splitlines() if line.strip()]

    if not remaining:
        print()
        print("Готово: рабочая папка чистая.")
        _log_detail("Working tree is clean before archive build.")
        _compact_progress("Remaining changes", 0, 0)
        return

    print()
    print("=" * 88)
    print("Остались изменения, которые скрипт НЕ трогал")
    print("=" * 88)
    _emit_detail_group("Remaining changes", remaining)

    print()
    print(
        "Остались изменения вне разрешённых зон. Полный список смотри в cleaner log."
    )
    _log_detail(
        "These may be real deletions, conflicts, or files outside allowed commit zones."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean traders-ml runtime garbage, optionally commit project changes, then build lightweight archive."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать действия, без удаления, restore, git add и commit.",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Очистить runtime-мусор, но не создавать technical commit.",
    )
    parser.add_argument(
        "--no-project-archive",
        action="store_true",
        help="Не собирать lightweight project archive после cleanup и technical commit.",
    )
    parser.add_argument(
        "--project-archive-output",
        default=DEFAULT_PROJECT_ARCHIVE_OUTPUT,
        help=(
            "Куда сохранить lightweight project archive. "
            f"Default: {DEFAULT_PROJECT_ARCHIVE_OUTPUT}"
        ),
    )
    parser.add_argument(
        "--include-deletions",
        action="store_true",
        help="Разрешить включать удаления файлов в technical commit.",
    )
    parser.add_argument(
        "--models-dry-run",
        action="store_true",
        help="Показать, какие artifacts/models будут удалены по retention policy, но не удалять.",
    )
    parser.add_argument(
        "--models-apply",
        action="store_true",
        help="Применить очистку artifacts/models по retention policy.",
    )
    parser.add_argument(
        "--models-only",
        action="store_true",
        help="Выполнить только model artifact retention cleanup и выйти.",
    )
    parser.add_argument(
        "--keep-last-models",
        type=int,
        default=DEFAULT_KEEP_LAST_MODELS,
        help="Сколько последних model artifact директорий оставить.",
    )
    parser.add_argument(
        "--models-force-without-db",
        action="store_true",
        help="Разрешить удаление model artifacts, даже если не удалось проверить active models в БД.",
    )
    args = parser.parse_args()

    root = ensure_git_repo()

    log_path = _init_cleaner_log(root)
    print("Идет подготовка к очистке и добавлении проекта в git ...")
    print(f"Лог очистки: {log_path}")
    _log_detail(f"Project root: {root}")

    if args.models_dry_run and args.models_apply:
        raise SystemExit("Use either --models-dry-run or --models-apply, not both.")

    if args.models_dry_run or args.models_apply:
        cleanup_model_artifacts(
            root=root,
            keep_last_models=args.keep_last_models,
            apply=args.models_apply,
            force_without_db=args.models_force_without_db,
        )
        if args.models_only:
            return 0

    print_status("Status before cleanup")

    restore_tracked_runtime_reports(dry_run=args.dry_run)
    clean_untracked_runtime_files(root=root, dry_run=args.dry_run)
    print_status("Status after cleanup")
    create_technical_commit(
        root=root,
        dry_run=args.dry_run,
        include_deletions=args.include_deletions,
        no_commit=args.no_commit,
    )
    print_status("Status after technical commit")
    warn_if_changes_remain()
    build_project_archive(
        root=root,
        output=args.project_archive_output,
        dry_run=args.dry_run,
        disabled=args.no_project_archive,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
