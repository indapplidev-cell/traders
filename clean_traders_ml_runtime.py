#!/usr/bin/env python
"""Очистка runtime-мусора в traders-ml.

Назначение:
- показать текущий git status;
- удалить временные runtime-отчёты из reports/;
- восстановить изменённые tracked runtime JSON/MD отчёты;
- НЕ трогать код, тесты, миграции, README, docs и финальные архивы вне reports/.

Запуск из корня проекта:
    python clean_traders_ml_runtime.py

Безопасный режим без удаления, только посмотреть:
    python clean_traders_ml_runtime.py --dry-run
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
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


def ensure_git_repo() -> None:
    """Проверяет, что скрипт запущен внутри git-репозитория."""
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


def print_status(title: str) -> None:
    """Печатает короткий git status."""
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)
    result = run_git(["status", "--short"], check=False)
    if not result.stdout.strip():
        print("git status --short: clean")


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
    """Удаляет untracked runtime-файлы и папки."""
    print()
    print("=" * 88)
    print("Clean untracked runtime files")
    print("=" * 88)

    targets = [*RUNTIME_PATHS_TO_CLEAN]
    targets.extend(f":(glob){pattern}" for pattern in RUNTIME_REPORT_PATTERNS)
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


def warn_if_code_changes_remain() -> None:
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
        "Это могут быть реальные правки кода/тестов. "
        "Проверь их вручную перед commit."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean traders-ml runtime report garbage.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать, что будет очищено, без удаления.",
    )
    args = parser.parse_args()

    ensure_git_repo()
    print_status("Status before cleanup")
    restore_tracked_runtime_reports(dry_run=args.dry_run)
    clean_untracked_runtime_files(dry_run=args.dry_run)
    print_status("Status after cleanup")
    warn_if_code_changes_remain()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
