"""Stage 8 paper runner control check.

Проверяет безопасный bounded paper runner:
- без live trading;
- без private Binance API;
- без бесконечного paper-runner;
- только runner-start с явным --ticks.
"""

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
class CheckResult:
    name: str
    ok: bool
    details: str


def run_command(args: list[str], *, expect_success: bool = True) -> CheckResult:
    process = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    output = process.stdout.strip()
    ok = process.returncode == 0 if expect_success else process.returncode != 0

    return CheckResult(
        name=" ".join(args),
        ok=ok,
        details=output,
    )


def require_no_private_binance_env() -> CheckResult:
    forbidden = [
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "BINANCE_SECRET_KEY",
    ]

    found = [name for name in forbidden if os.getenv(name)]

    return CheckResult(
        name="private Binance env guard",
        ok=not found,
        details="OK: private Binance env is absent" if not found else f"FORBIDDEN ENV: {', '.join(found)}",
    )


def extract_session_id(output: str) -> int:
    match = re.search(r"session id\s+│\s+(\d+)", output)
    if match:
        return int(match.group(1))

    match = re.search(r"session id\s*[:|]\s*(\d+)", output, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    raise RuntimeError("Cannot extract runner session id from runner-start output.")


def assert_contains(name: str, output: str, expected: str) -> CheckResult:
    return CheckResult(
        name=name,
        ok=expected in output,
        details=f"FOUND: {expected}" if expected in output else f"NOT FOUND: {expected}\n\n{output}",
    )


def print_result(result: CheckResult) -> None:
    status = "OK" if result.ok else "FAIL"
    print(f"[{status}] {result.name}")
    if result.details:
        print(result.details)
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="simple_trend")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--initial-cash", default="1000")
    args = parser.parse_args()

    python_exe = sys.executable
    results: list[CheckResult] = []

    results.append(require_no_private_binance_env())

    results.append(
        run_command(
            [
                python_exe,
                "-m",
                "app.cli.commands",
                "health",
            ]
        )
    )

    results.append(
        run_command(
            [
                python_exe,
                "-m",
                "app.cli.commands",
                "async-health",
            ]
        )
    )

    no_ticks = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "runner-start",
            "--strategy",
            args.strategy,
            "--symbol",
            args.symbol,
            "--interval",
            args.interval,
            "--sleep-seconds",
            "0",
        ],
        expect_success=False,
    )
    results.append(no_ticks)
    results.append(assert_contains("runner-start requires --ticks", no_ticks.details, "Missing option '--ticks'"))

    zero_ticks = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "runner-start",
            "--strategy",
            args.strategy,
            "--symbol",
            args.symbol,
            "--interval",
            args.interval,
            "--ticks",
            "0",
            "--sleep-seconds",
            "0",
        ],
        expect_success=False,
    )
    results.append(zero_ticks)
    results.append(assert_contains("runner-start rejects --ticks 0", zero_ticks.details, "ticks must be > 0"))

    disabled_runner = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "paper-runner",
        ],
        expect_success=False,
    )
    results.append(disabled_runner)
    results.append(
        assert_contains(
            "paper-runner disabled",
            disabled_runner.details,
            "paper-runner is disabled for Stage 8",
        )
    )

    runner_start = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
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
            "0",
        ]
    )
    results.append(runner_start)
    results.append(assert_contains("runner-start stopped", runner_start.details, "STOPPED"))
    results.append(assert_contains("runner-start completed requested ticks", runner_start.details, str(args.ticks)))

    session_id = extract_session_id(runner_start.details)

    runner_history = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "runner-history",
            "--limit",
            "5",
        ]
    )
    results.append(runner_history)
    results.append(assert_contains("runner-history contains session", runner_history.details, str(session_id)))

    runner_ticks = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "runner-ticks",
            "--session-id",
            str(session_id),
        ]
    )
    results.append(runner_ticks)
    results.append(assert_contains("runner-ticks contains session id", runner_ticks.details, str(session_id)))
    results.append(assert_contains("runner-ticks contains session header", runner_ticks.details, "Runner ticks session"))

    performance = run_command(
        [
            python_exe,
            "-m",
            "app.cli.commands",
            "performance-session",
            "--session-id",
            str(session_id),
        ]
    )
    results.append(performance)
    results.append(assert_contains("performance has STOPPED", performance.details, "STOPPED"))
    results.append(assert_contains("performance has requested ticks", performance.details, f"ticks requested       | {args.ticks}"))
    results.append(assert_contains("performance has completed ticks", performance.details, f"ticks completed       | {args.ticks}"))
    results.append(assert_contains("performance has audit ticks", performance.details, f"audit ticks           | {args.ticks}"))
    results.append(assert_contains("performance has zero error ticks", performance.details, "error ticks           | 0"))
    results.append(assert_contains("performance has COMPLETE data quality", performance.details, "COMPLETE"))
    results.append(assert_contains("performance has execution metrics", performance.details, "Execution metrics"))

    for result in results:
        print_result(result)

    failed = [result for result in results if not result.ok]
    if failed:
        print("СТАТУС: ОШИБКА")
        return 1

    print("СТАТУС: УСПЕХ")
    print(f"runner session id: {session_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
