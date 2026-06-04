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
    return "\u0437\u0430\u0434\u0430\u043d" if os.environ.get(name) else "\u043d\u0435 \u0437\u0430\u0434\u0430\u043d"


def print_header() -> None:
    print("=" * 80)
    print("\u0414\u0415\u041c\u041e\u041d\u0421\u0422\u0420\u0410\u0426\u0418\u042f \u041f\u0420\u041e\u0415\u041a\u0422\u0410 TRADERS")
    print("\u0420\u0435\u0436\u0438\u043c: paper-only")
    print("\u0420\u0435\u0430\u043b\u044c\u043d\u044b\u0435 \u043e\u0440\u0434\u0435\u0440\u0430: \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d\u044b")
    print("Binance private API: \u043d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f")
    print("Backtest analytics: \u0432\u043a\u043b\u044e\u0447\u0451\u043d")
    print("Session compare: \u0432\u043a\u043b\u044e\u0447\u0451\u043d")
    print("=" * 80)
    print(f"DATABASE_URL: {mask_env_status('DATABASE_URL')}")
    print(f"ASYNC_DATABASE_URL: {mask_env_status('ASYNC_DATABASE_URL')}")
    print("=" * 80)


def print_footer(results: list[StepResult], skipped: list[str]) -> int:
    failed = [result for result in results if not result.ok]

    print()
    print("=" * 80)
    print("\u0418\u0422\u041e\u0413 \u0414\u0415\u041c\u041e\u041d\u0421\u0422\u0420\u0410\u0426\u0418\u0418")
    print("=" * 80)

    for result in results:
        status = "OK" if result.ok else "\u041e\u0428\u0418\u0411\u041a\u0410"
        print(f"- {result.title}: {status}")

    for title in skipped:
        print(f"- {title}: \u041f\u0420\u041e\u041f\u0423\u0429\u0415\u041d\u041e")

    print("-" * 80)

    if failed:
        print("\u0421\u0442\u0430\u0442\u0443\u0441: \u041e\u0428\u0418\u0411\u041a\u0410")
        print(
            "\u041f\u0440\u043e\u0435\u043a\u0442 \u043d\u0435 \u043f\u0440\u043e\u0448\u0451\u043b "
            "\u0434\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0437\u0430\u043f\u0443\u0441\u043a."
        )
        print("\u041f\u0435\u0440\u0432\u044b\u0439 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0439 \u044d\u0442\u0430\u043f:")
        first = failed[0]
        print(first.title)
        print(f"\u041a\u043e\u0434 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0430: {first.returncode}")
        print("=" * 80)
        return 1

    print("\u0421\u0442\u0430\u0442\u0443\u0441: \u0423\u0421\u041f\u0415\u0425")
    print()
    print(
        "\u041f\u0440\u043e\u0435\u043a\u0442 \u043f\u043e\u043a\u0430\u0437\u0430\u043b \u043f\u043e\u043b\u043d\u044b\u0439 "
        "paper-only pipeline, \u0432\u043a\u043b\u044e\u0447\u0430\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u044b\u0439 "
        "backtest \u0438 \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 runner vs backtest."
    )
    print("- \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u043b \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435")
    print("- \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u043b \u0440\u0435\u0435\u0441\u0442\u0440 \u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u0439")
    print("- \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u043b \u043f\u0443\u0431\u043b\u0438\u0447\u043d\u044b\u0435 \u0441\u0432\u0435\u0447\u0438")
    print("- \u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043b \u0440\u044b\u043d\u043e\u043a")
    print("- \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u043b backtest")
    print("- \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u043b backtest session")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b backtest performance")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b backtest history")
    print("- \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u043b paper runner")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b runner history")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b runtime ticks")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b performance analytics")
    print("- \u0441\u0440\u0430\u0432\u043d\u0438\u043b runner session \u0438 backtest session")
    print("- \u043f\u043e\u043a\u0430\u0437\u0430\u043b portfolio analytics")
    print()
    print("\u0420\u0435\u0430\u043b\u044c\u043d\u044b\u0445 \u043e\u0440\u0434\u0435\u0440\u043e\u0432 \u043d\u0435 \u0431\u044b\u043b\u043e.")
    print("Live trading \u043d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043b\u0441\u044f.")
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
    print(f"\u041a\u043e\u043c\u0430\u043d\u0434\u0430: {printable_command}")

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

    status = "OK" if completed.returncode == 0 else "\u041e\u0428\u0418\u0411\u041a\u0410"
    print("-" * 80)
    print(f"\u0421\u0442\u0430\u0442\u0443\u0441: {status}")

    result = StepResult(
        title=title,
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )

    if required and not result.ok:
        print()
        print(
            "\u041a\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u044d\u0442\u0430\u043f "
            "\u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u0441\u044f \u043e\u0448\u0438\u0431\u043a\u043e\u0439. "
            "\u0414\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430."
        )

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


def extract_backtest_session_id(output: str) -> int | None:
    patterns = (
        r"backtest\s+session\s+id\s*[:=]\s*(\d+)",
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
        description=(
            "\u0420\u0443\u0441\u0441\u043a\u0430\u044f \u0442\u0435\u0440\u043c\u0438\u043d\u0430\u043b\u044c\u043d\u0430\u044f "
            "\u0434\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u044f paper-only pipeline "
            "\u043f\u0440\u043e\u0435\u043a\u0442\u0430 traders."
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    parser.add_argument("--strategy", default="simple_trend")
    parser.add_argument("--initial-cash", default="1000")
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
    backtest_session_id: int | None = None
    runner_session_id: int | None = None

    steps: list[tuple[str, list[str], bool]] = [
        ("\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f", ["health"], True),
        (
            "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0430\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u043d\u043e\u0433\u043e "
            "\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u043a \u0411\u0414",
            ["async-health"],
            True,
        ),
        (
            "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0440\u0435\u0435\u0441\u0442\u0440\u0430 "
            "\u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u0439",
            ["strategy-list"],
            True,
        ),
    ]

    if args.skip_load_history:
        skipped.append("\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043f\u0443\u0431\u043b\u0438\u0447\u043d\u044b\u0445 \u0441\u0432\u0435\u0447\u0435\u0439")
    else:
        steps.append(
            (
                "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043f\u0443\u0431\u043b\u0438\u0447\u043d\u044b\u0445 \u0441\u0432\u0435\u0447\u0435\u0439",
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
                "\u0410\u043d\u0430\u043b\u0438\u0437 \u0440\u044b\u043d\u043a\u0430",
                ["analyze", "--symbol", args.symbol, "--interval", args.interval],
                True,
            ),
            (
                "Backtest \u043f\u043e \u0438\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438\u043c \u0441\u0432\u0435\u0447\u0430\u043c",
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
                "Backtest session run",
                [
                    "backtest-run",
                    "--strategy",
                    args.strategy,
                    "--symbol",
                    args.symbol,
                    "--interval",
                    args.interval,
                    "--candles",
                    "300",
                    "--initial-cash",
                    str(args.initial_cash),
                ],
                True,
            ),
        ]
    )

    total_steps = len(steps) + 9

    for index, (title, command_args, required) in enumerate(steps, start=1):
        result = run_cli_step(index, total_steps, title, command_args, required)
        results.append(result)

        if title == "Backtest session run" and result.ok:
            backtest_session_id = extract_backtest_session_id(result.stdout)

        if required and not result.ok:
            return print_footer(results, skipped)

    next_step = len(results) + 1

    if backtest_session_id is None:
        print()
        print(
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
            "\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 "
            "\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c backtest session id."
        )
        print("\u042d\u0442\u0430\u043f backtest-performance \u0431\u0443\u0434\u0435\u0442 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d.")
        skipped.append("Backtest performance")
    else:
        result = run_cli_step(
            next_step,
            total_steps,
            "Backtest performance",
            ["backtest-performance", "--session-id", str(backtest_session_id)],
            True,
        )
        results.append(result)
        if not result.ok:
            return print_footer(results, skipped)
        next_step += 1

    result = run_cli_step(
        next_step,
        total_steps,
        "Backtest history",
        ["backtest-history", "--limit", "5"],
        True,
    )
    results.append(result)
    if not result.ok:
        return print_footer(results, skipped)
    next_step += 1

    result = run_cli_step(
        next_step,
        total_steps,
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
    )
    results.append(result)
    if result.ok:
        runner_session_id = extract_session_id(result.stdout)
    else:
        return print_footer(results, skipped)
    next_step += 1

    result = run_cli_step(
        next_step,
        total_steps,
        "\u0418\u0441\u0442\u043e\u0440\u0438\u044f runner-\u0441\u0435\u0441\u0441\u0438\u0439",
        ["runner-history", "--limit", "5"],
        True,
    )
    results.append(result)
    if not result.ok:
        return print_footer(results, skipped)
    next_step += 1

    if runner_session_id is None:
        print()
        print(
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
            "\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 "
            "\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c runner session id."
        )
        print(
            "\u042d\u0442\u0430\u043f\u044b runner-ticks \u0438 performance-session "
            "\u0431\u0443\u0434\u0443\u0442 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u044b."
        )
        skipped.append("Runtime ticks")
        skipped.append("Performance session")
    else:
        result = run_cli_step(
            next_step,
            total_steps,
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
            total_steps,
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
        total_steps,
        "Performance history",
        ["performance-history", "--limit", "5"],
        True,
    )
    results.append(result)
    if not result.ok:
        return print_footer(results, skipped)
    next_step += 1

    if backtest_session_id is None or runner_session_id is None:
        print()
        print(
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c "
            "\u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 "
            "session-compare: \u043d\u0435\u0442 runner \u0438\u043b\u0438 backtest session id."
        )
        skipped.append("Session compare")
    else:
        result = run_cli_step(
            next_step,
            total_steps,
            "Session compare",
            [
                "session-compare",
                "--left-type",
                "runner",
                "--left-id",
                str(runner_session_id),
                "--right-type",
                "backtest",
                "--right-id",
                str(backtest_session_id),
            ],
            True,
        )
        results.append(result)
        if not result.ok:
            return print_footer(results, skipped)
        next_step += 1

    result = run_cli_step(
        next_step,
        total_steps,
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
