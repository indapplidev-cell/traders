from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StepResult:
    title: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def mask_env_status(name: str) -> str:
    return "задан" if os.environ.get(name) else "не задан"


def print_header() -> None:
    print("=" * 80)
    print("ДЕМОНСТРАЦИЯ ПРОЕКТА TRADERS")
    print("Режим: paper-only")
    print("Реальные ордера: запрещены")
    print("Binance private API: не используется")
    print("=" * 80)
    print(f"DATABASE_URL: {mask_env_status('DATABASE_URL')}")
    print(f"ASYNC_DATABASE_URL: {mask_env_status('ASYNC_DATABASE_URL')}")
    print("=" * 80)


def print_footer(results: list[StepResult], skipped: list[str]) -> int:
    failed = [result for result in results if not result.ok]

    print()
    print("=" * 80)
    print("ИТОГ ДЕМОНСТРАЦИИ")
    print("=" * 80)

    for result in results:
        status = "OK" if result.ok else "ОШИБКА"
        print(f"- {result.title}: {status}")

    for title in skipped:
        print(f"- {title}: ПРОПУЩЕНО")

    print("-" * 80)

    if failed:
        print("Статус: ОШИБКА")
        print("Проект не прошел демонстрационный запуск.")
        print("Первый проблемный этап:")
        first = failed[0]
        print(first.title)
        print(f"Код возврата: {first.returncode}")
        print("=" * 80)
        return 1

    print("Статус: УСПЕХ")
    print()
    print("Проект выполнил демонстрационный paper-only pipeline:")
    print("- проверил подключение")
    print("- проверил реестр стратегий")
    print("- загрузил публичные свечи")
    print("- проанализировал рынок")
    print("- выполнил backtest")
    print("- запустил paper runner")
    print("- показал runner history")
    print("- показал runtime ticks")
    print("- показал performance analytics")
    print("- показал portfolio analytics")
    print()
    print("Реальных ордеров не было.")
    print("Live trading не использовался.")
    print("=" * 80)
    return 0


def build_cli_command(args: list[str]) -> list[str]:
    return [sys.executable, "-m", "app.cli.commands", *args]


def run_cli_step(
    step_number: int,
    total_steps: int,
    title: str,
    args: list[str],
    required: bool = True,
) -> StepResult:
    command = build_cli_command(args)
    printable_command = " ".join(command)

    print()
    print(f"[{step_number}/{total_steps}] {title}")
    print(f"Команда: {printable_command}")

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if stdout:
        print("-" * 80)
        print(stdout)

    if stderr:
        print("-" * 80)
        print("STDERR:")
        print(stderr)

    status = "OK" if completed.returncode == 0 else "ОШИБКА"
    print("-" * 80)
    print(f"Статус: {status}")

    result = StepResult(
        title=title,
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )

    if required and not result.ok:
        print()
        print("Критический этап завершился ошибкой. Демонстрация остановлена.")

    return result


def extract_session_id(output: str) -> int | None:
    patterns = (
        r"runner\s+session\s+id\s*[:=]\s*(\d+)",
        r"session\s+id\b[^\d\r\n]*(\d+)",
        r"session\s+id\s*[:=]\s*(\d+)",
        r"\bid\s*[:=]\s*(\d+)",
    )

    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Русская терминальная демонстрация paper-only pipeline проекта traders."
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    parser.add_argument("--strategy", default="simple_trend")
    parser.add_argument("--skip-load-history", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://traders:traders@127.0.0.1:5432/traders",
    )
    os.environ.setdefault(
        "ASYNC_DATABASE_URL",
        "postgresql+asyncpg://traders:traders@127.0.0.1:5432/traders",
    )

    print_header()

    results: list[StepResult] = []
    skipped: list[str] = []

    steps: list[tuple[str, list[str], bool]] = [
        ("Проверка приложения", ["health"], True),
        ("Проверка асинхронного подключения к БД", ["async-health"], True),
        ("Проверка реестра стратегий", ["strategy-list"], True),
    ]

    if args.skip_load_history:
        skipped.append("Загрузка публичных свечей")
    else:
        steps.append(
            (
                "Загрузка публичных свечей",
                [
                    "load-history",
                    "--symbol",
                    args.symbol,
                    "--interval",
                    args.interval,
                    "--days",
                    str(args.days),
                ],
                True,
            )
        )

    steps.extend(
        [
            (
                "Анализ рынка",
                ["analyze", "--symbol", args.symbol, "--interval", args.interval],
                True,
            ),
            (
                "Backtest по историческим свечам",
                [
                    "backtest",
                    "--symbol",
                    args.symbol,
                    "--interval",
                    args.interval,
                    "--days",
                    str(args.days),
                ],
                True,
            ),
            (
                "Paper runner",
                [
                    "runner-start",
                    "--strategy",
                    args.strategy,
                    "--symbol",
                    args.symbol,
                    "--interval",
                    args.interval,
                    "--ticks",
                    str(args.ticks),
                    "--sleep-seconds",
                    str(args.sleep_seconds),
                ],
                True,
            ),
            ("История runner-сессий", ["runner-history", "--limit", "5"], True),
        ]
    )

    total_base_steps = len(steps) + 4

    runner_session_id: int | None = None

    for index, (title, command_args, required) in enumerate(steps, start=1):
        result = run_cli_step(index, total_base_steps, title, command_args, required)
        results.append(result)

        if title == "Paper runner" and result.ok:
            runner_session_id = extract_session_id(result.stdout)

        if required and not result.ok:
            return print_footer(results, skipped)

    next_step = len(results) + 1

    if runner_session_id is None:
        print()
        print("Не удалось автоматически определить runner session id.")
        print("Этапы runner-ticks и performance-session будут пропущены.")
        skipped.append("Runtime ticks")
        skipped.append("Performance session")
    else:
        print()
        print(f"Определен runner session id: {runner_session_id}")

        result = run_cli_step(
            next_step,
            total_base_steps,
            "Runtime ticks",
            ["runner-ticks", "--session-id", str(runner_session_id)],
            True,
        )
        results.append(result)
        if not result.ok:
            return print_footer(results, skipped)

        next_step += 1

        result = run_cli_step(
            next_step,
            total_base_steps,
            "Performance session",
            ["performance-session", "--session-id", str(runner_session_id)],
            True,
        )
        results.append(result)
        if not result.ok:
            return print_footer(results, skipped)

        next_step += 1

    result = run_cli_step(
        next_step,
        total_base_steps,
        "Performance history",
        ["performance-history", "--limit", "5"],
        True,
    )
    results.append(result)
    if not result.ok:
        return print_footer(results, skipped)

    next_step += 1

    result = run_cli_step(
        next_step,
        total_base_steps,
        "Portfolio analytics",
        ["portfolio-analytics", "--symbol", args.symbol],
        True,
    )
    results.append(result)
    if not result.ok:
        return print_footer(results, skipped)

    return print_footer(results, skipped)


if __name__ == "__main__":
    raise SystemExit(main())
