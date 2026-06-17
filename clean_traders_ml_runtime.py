#!/usr/bin/env python
"""Очистка runtime-мусора и технический commit в traders-ml.

Назначение:
- показать текущий git status;
- удалить временные runtime-отчёты, cache и архивы из рабочей папки проекта;
- восстановить изменённые tracked runtime JSON/MD отчёты;
- НЕ трогать runtime-мусор в commit;
- сделать технический commit для оставшихся новых/изменённых файлов проекта.

Логика commit message:
- если есть только изменённые tracked-файлы: "новые изменения";
- если есть только новые untracked-файлы: "новые файлы";
- если есть и новые, и изменённые: "добавлены и изменены".

Запуск из корня проекта:
    python clean_traders_ml_runtime.py

Безопасный режим без удаления и без commit:
    python clean_traders_ml_runtime.py --dry-run

Только очистить мусор, без commit:
    python clean_traders_ml_runtime.py --no-commit

Разрешить commit удалённых файлов:
    python clean_traders_ml_runtime.py --include-deletions
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


RUNTIME_PATHS_TO_CLEAN = [
    "reports/feature_regime_experiments/",
    "reports/label_grid_experiments/",
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
}

TECHNICAL_COMMIT_MESSAGES = {
    "modified_only": "новые изменения",
    "new_only": "новые файлы",
    "mixed": "добавлены и изменены",
}


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
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)

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
        return

    print("Matched tracked runtime reports:")
    for path in matched_files:
        print(f"  {path}")

    args = ["restore", "--worktree", "--staged", "--", *matched_files]

    if dry_run:
        print("DRY RUN: git " + " ".join(args))
        return

    run_git(args, check=True)


def clean_untracked_runtime_files(dry_run: bool) -> None:
    """Удаляет untracked runtime-файлы, папки, cache и архивы."""
    print()
    print("=" * 88)
    print("Clean untracked runtime files")
    print("=" * 88)

    targets = [*RUNTIME_PATHS_TO_CLEAN]
    targets.extend(f":(glob){pattern}" for pattern in RUNTIME_REPORT_PATTERNS)
    targets.extend(f":(glob){pattern}" for pattern in ARCHIVE_PATTERNS_TO_CLEAN)
    targets.extend(CACHE_PATHS_TO_CLEAN)

    preview_args = ["clean", "-nd", "--", *targets]
    print("Preview:")
    run_git(preview_args, check=False)

    if dry_run:
        print("DRY RUN: удаление не выполнялось.")
        return

    clean_args = ["clean", "-fd", "--", *targets]
    print()
    print("Apply clean:")
    run_git(clean_args, check=False)


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


def _is_commit_allowed_path(path: str) -> bool:
    """Проверяет, можно ли путь включать в технический commit."""
    normalized = path.replace("\\", "/")

    if _matches_any(normalized, NEVER_COMMIT_PATTERNS):
        return False

    if normalized in COMMIT_ALLOWED_EXACT_FILES:
        return True

    return any(normalized.startswith(prefix) for prefix in COMMIT_ALLOWED_PREFIXES)


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
        if entry.is_deleted and not include_deletions:
            skipped_entries.append(entry)
            continue
        if not _is_commit_allowed_path(entry.path):
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


def create_technical_commit(*, dry_run: bool, include_deletions: bool, no_commit: bool) -> None:
    """Делает технический commit для оставшихся новых/изменённых проектных файлов."""
    print()
    print("=" * 88)
    print("Technical commit")
    print("=" * 88)

    if no_commit:
        print("Commit отключён флагом --no-commit.")
        return

    entries = get_status_entries()
    if not entries:
        print("Нет изменений для commit.")
        return

    commit_entries, skipped_entries, conflict_entries = _select_commit_entries(
        entries,
        include_deletions=include_deletions,
    )

    if conflict_entries:
        print("Найдены конфликтные файлы. Авто-commit остановлен:")
        for entry in conflict_entries:
            print(f"  {entry.index_status}{entry.worktree_status} {entry.path}")
        raise SystemExit("Сначала разреши git conflicts вручную.")

    if skipped_entries:
        print("Пропущены файлы, которые скрипт не должен коммитить:")
        for entry in skipped_entries:
            print(f"  {entry.index_status}{entry.worktree_status} {entry.path}")

    if not commit_entries:
        print("Нет разрешённых проектных изменений для technical commit.")
        return

    paths = _unique_paths(commit_entries)
    message = _commit_message_for(commit_entries)

    print("Файлы для technical commit:")
    for path in paths:
        print(f"  {path}")
    print(f"Commit message: {message}")

    if dry_run:
        print("DRY RUN: git add -- " + " ".join(paths))
        print(f"DRY RUN: git commit -m {message!r}")
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
        return

    run_git(["commit", "-m", message], check=True)


def warn_if_changes_remain() -> None:
    """Показывает, остались ли изменения, которые скрипт не должен трогать."""
    result = run_git(["status", "--short"], check=False)
    remaining = [line for line in result.stdout.splitlines() if line.strip()]

    if not remaining:
        print()
        print("Готово: рабочая папка чистая.")
        return

    print()
    print("=" * 88)
    print("Остались изменения, которые скрипт НЕ трогал")
    print("=" * 88)
    for line in remaining:
        print(line)

    print()
    print(
        "Это могут быть реальные удаления, конфликтные файлы или файлы вне разрешённых зон. "
        "Проверь их вручную."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean traders-ml runtime garbage and optionally create a technical commit."
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
        "--include-deletions",
        action="store_true",
        help="Разрешить включать удаления файлов в technical commit.",
    )
    args = parser.parse_args()

    ensure_git_repo()
    print_status("Status before cleanup")
    restore_tracked_runtime_reports(dry_run=args.dry_run)
    clean_untracked_runtime_files(dry_run=args.dry_run)
    print_status("Status after cleanup")
    create_technical_commit(
        dry_run=args.dry_run,
        include_deletions=args.include_deletions,
        no_commit=args.no_commit,
    )
    print_status("Status after technical commit")
    warn_if_changes_remain()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
