"""Terminal demo pipeline for the current paper-only traders project."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass


DEFAULT_DATABASE_URL = "postgresql+psycopg://traders:traders@127.0.0.1:5432/traders"
DEFAULT_ASYNC_DATABASE_URL = "postgresql+asyncpg://traders:traders@127.0.0.1:5432/traders"


@dataclass
class StepResult:
    title: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class DemoFailed(RuntimeError):
    """Raised when a required demo step fails."""

    def __init__(self, result: StepResult) -> None:
        super().__init__(result.title)
        self.result = result


STEP_COUNTER = 0
TOTAL_STEPS = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Локальная демонстрация paper-only pipeline проекта traders.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    parser.add_argument("--strategy", default="simple_trend")
    parser.add_argument("--skip-load-history", action="store_true")
    return parser.parse_args()


def extract_session_id(output: str) -> int | None:
    patterns = [
        r"session id\s*=\s*(\d+)",
        r"session id\s*:\s*(\d+)",
        r"session id\s+\|\s*(\d+)",
        r"Runner session id\s*:\s*(\d+)",
        r"\bid\s*=\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def print_separator() -> None:
    print("=" * 80)


def safe_terminal_text(value: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return value
    return value.encode(encoding, errors="backslashreplace").decode(encoding)


def print_header(args: argparse.Namespace) -> None:
    print_separator()
    print("ДЕМОНСТРАЦИЯ TRADERS")
    print("Режим: paper-only")
    print("Реальные ордера: запрещены")
    print("Binance private API: не используется")
    print(f"Символ: {args.symbol}")
    print(f"Интервал: {args.interval}")
    print(f"Стратегия: {args.strategy}")
    print(f"DATABASE_URL: {'задан' if os.environ.get('DATABASE_URL') else 'не задан'}")
    print(f"ASYNC_DATABASE_URL: {'задан' if os.environ.get('ASYNC_DATABASE_URL') else 'не задан'}")
    print_separator()


def print_step_result(result: StepResult, required: bool) -> None:
    print(f"Команда: {' '.join(result.command)}")
    print(f"Статус: {'OK' if result.ok else 'ОШИБКА'}")
    if not required:
        print("Тип шага: необязательный")
    if result.stdout.strip():
        print("stdout:")
        print(safe_terminal_text(result.stdout.rstrip()))
    if result.stderr.strip():
        print("stderr:")
        print(safe_terminal_text(result.stderr.rstrip()))


def run_cli_step(title: str, args: list[str], required: bool = True) -> StepResult:
    global STEP_COUNTER
    STEP_COUNTER += 1
    command = [sys.executable, "-m", "app.cli.commands", *args]

    print(f"[{STEP_COUNTER}/{TOTAL_STEPS}] {title}")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
    )
    result = StepResult(
        title=title,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    print_step_result(result, required=required)
    print_separator()

    if required and not result.ok:
        print("Демонстрация остановлена: обязательный шаг завершился ошибкой.")
        raise DemoFailed(result)
    return result


def print_summary(success: bool, reason: str | None = None) -> None:
    print_separator()
    print("ИТОГ ДЕМОНСТРАЦИИ")
    print(f"Статус: {'УСПЕХ' if success else 'ОШИБКА'}")
    if success:
        print(
            "Проект получил данные, сохранил их, проанализировал рынок, запустил стратегию, "
            "проверил risk gate, выполнил paper-runner и показал аналитику."
        )
    elif reason:
        print(reason)
    print_separator()


def main() -> int:
    os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
    os.environ.setdefault("ASYNC_DATABASE_URL", DEFAULT_ASYNC_DATABASE_URL)
    args = parse_args()
    print_header(args)

    try:
        run_cli_step("Проверка синхронного подключения к приложению", ["health"])
        run_cli_step("Проверка асинхронного подключения к БД", ["async-health"])
        run_cli_step("Проверка реестра стратегий", ["strategy-list"])
        if not args.skip_load_history:
            run_cli_step(
                "Загрузка публичных свечей Binance",
                ["load-history", "--symbol", args.symbol, "--interval", args.interval, "--days", str(args.days)],
            )
        run_cli_step("Анализ рынка", ["analyze", "--symbol", args.symbol, "--interval", args.interval])
        run_cli_step("Backtest по историческим свечам", ["backtest", "--symbol", args.symbol, "--interval", args.interval, "--days", str(args.days)])
        runner_result = run_cli_step(
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
        )
        session_id = extract_session_id(f"{runner_result.stdout}\n{runner_result.stderr}")
        if session_id is None:
            print("Не удалось автоматически определить runner session id.")
            print("Шаги runner-ticks и performance-session будут пропущены.")
            print_separator()
        run_cli_step("История runner-сессий", ["runner-history", "--limit", "5"])
        if session_id is not None:
            run_cli_step("Аудит tick-ов runner-сессии", ["runner-ticks", "--session-id", str(session_id)], required=False)
            run_cli_step(
                "Подробная performance analytics по runner-сессии",
                ["performance-session", "--session-id", str(session_id)],
                required=False,
            )
        run_cli_step("История performance analytics", ["performance-history", "--limit", "5"])
        run_cli_step("Portfolio analytics", ["portfolio-analytics", "--symbol", args.symbol])
    except DemoFailed as exc:
        print_summary(False, f"Демонстрация завершилась на шаге: {exc.result.title}")
        return 1

    print_summary(True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
