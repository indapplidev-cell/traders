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
    return "Р·Р°РґР°РЅ" if os.environ.get(name) else "РЅРµ Р·Р°РґР°РЅ"


def print_header() -> None:
    print("=" * 80)
    print("Р”Р•РњРћРќРЎРўР РђР¦РРЇ РџР РћР•РљРўРђ TRADERS")
    print("Р РµР¶РёРј: paper-only")
    print("Р РµР°Р»СЊРЅС‹Рµ РѕСЂРґРµСЂР°: Р·Р°РїСЂРµС‰РµРЅС‹")
    print("Binance private API: РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ")
    print("=" * 80)
    print(f"DATABASE_URL: {mask_env_status('DATABASE_URL')}")
    print(f"ASYNC_DATABASE_URL: {mask_env_status('ASYNC_DATABASE_URL')}")
    print("=" * 80)


def safe_terminal_text(value: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return value
    return value.encode(encoding, errors="backslashreplace").decode(encoding)


def print_footer(results: list[StepResult], skipped: list[str]) -> int:
    failed = [result for result in results if not result.ok]

    print()
    print("=" * 80)
    print("РРўРћР“ Р”Р•РњРћРќРЎРўР РђР¦РР")
    print("=" * 80)

    for result in results:
        status = "OK" if result.ok else "РћРЁРР‘РљРђ"
        print(f"- {result.title}: {status}")

    for title in skipped:
        print(f"- {title}: РџР РћРџРЈР©Р•РќРћ")

    print("-" * 80)

    if failed:
        print("РЎС‚Р°С‚СѓСЃ: РћРЁРР‘РљРђ")
        print("РџСЂРѕРµРєС‚ РЅРµ РїСЂРѕС€С‘Р» РґРµРјРѕРЅСЃС‚СЂР°С†РёРѕРЅРЅС‹Р№ Р·Р°РїСѓСЃРє.")
        print("РџРµСЂРІС‹Р№ РїСЂРѕР±Р»РµРјРЅС‹Р№ СЌС‚Р°Рї:")
        first = failed[0]
        print(f"{first.title}")
        print(f"РљРѕРґ РІРѕР·РІСЂР°С‚Р°: {first.returncode}")
        print("=" * 80)
        return 1

    print("РЎС‚Р°С‚СѓСЃ: РЈРЎРџР•РҐ")
    print()
    print("РџСЂРѕРµРєС‚ РІС‹РїРѕР»РЅРёР» РґРµРјРѕРЅСЃС‚СЂР°С†РёРѕРЅРЅС‹Р№ paper-only pipeline:")
    print("- РїСЂРѕРІРµСЂРёР» РїРѕРґРєР»СЋС‡РµРЅРёРµ")
    print("- РїСЂРѕРІРµСЂРёР» СЂРµРµСЃС‚СЂ СЃС‚СЂР°С‚РµРіРёР№")
    print("- Р·Р°РіСЂСѓР·РёР» РїСѓР±Р»РёС‡РЅС‹Рµ СЃРІРµС‡Рё")
    print("- РїСЂРѕР°РЅР°Р»РёР·РёСЂРѕРІР°Р» СЂС‹РЅРѕРє")
    print("- РІС‹РїРѕР»РЅРёР» backtest")
    print("- Р·Р°РїСѓСЃС‚РёР» paper runner")
    print("- РїРѕРєР°Р·Р°Р» runner history")
    print("- РїРѕРєР°Р·Р°Р» runtime ticks")
    print("- РїРѕРєР°Р·Р°Р» performance analytics")
    print("- РїРѕРєР°Р·Р°Р» portfolio analytics")
    print()
    print("Р РµР°Р»СЊРЅС‹С… РѕСЂРґРµСЂРѕРІ РЅРµ Р±С‹Р»Рѕ.")
    print("Live trading РЅРµ РёСЃРїРѕР»СЊР·РѕРІР°Р»СЃСЏ.")
    print("=" * 80)
    return 0


def build_cli_command(args: list[str]) -> list[str]:
    return [sys.executable, "-m", "app.cli.commands", *args]


def configure_utf8_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


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
    print(f"РљРѕРјР°РЅРґР°: {printable_command}")

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=build_subprocess_env(),
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if stdout:
        print("-" * 80)
        print(safe_terminal_text(stdout))

    if stderr:
        print("-" * 80)
        print("STDERR:")
        print(safe_terminal_text(stderr))

    status = "OK" if completed.returncode == 0 else "РћРЁРР‘РљРђ"
    print("-" * 80)
    print(f"РЎС‚Р°С‚СѓСЃ: {status}")

    result = StepResult(
        title=title,
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )

    if required and not result.ok:
        print()
        print("РљСЂРёС‚РёС‡РµСЃРєРёР№ СЌС‚Р°Рї Р·Р°РІРµСЂС€РёР»СЃСЏ РѕС€РёР±РєРѕР№. Р”РµРјРѕРЅСЃС‚СЂР°С†РёСЏ РѕСЃС‚Р°РЅРѕРІР»РµРЅР°.")

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
        description="Р СѓСЃСЃРєР°СЏ С‚РµСЂРјРёРЅР°Р»СЊРЅР°СЏ РґРµРјРѕРЅСЃС‚СЂР°С†РёСЏ paper-only pipeline РїСЂРѕРµРєС‚Р° traders."
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
    configure_utf8_output()
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
        ("РџСЂРѕРІРµСЂРєР° РїСЂРёР»РѕР¶РµРЅРёСЏ", ["health"], True),
        ("РџСЂРѕРІРµСЂРєР° Р°СЃРёРЅС…СЂРѕРЅРЅРѕРіРѕ РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє Р‘Р”", ["async-health"], True),
        ("РџСЂРѕРІРµСЂРєР° СЂРµРµСЃС‚СЂР° СЃС‚СЂР°С‚РµРіРёР№", ["strategy-list"], True),
    ]

    if args.skip_load_history:
        skipped.append("Р—Р°РіСЂСѓР·РєР° РїСѓР±Р»РёС‡РЅС‹С… СЃРІРµС‡РµР№")
    else:
        steps.append(
            (
                "Р—Р°РіСЂСѓР·РєР° РїСѓР±Р»РёС‡РЅС‹С… СЃРІРµС‡РµР№",
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
                "РђРЅР°Р»РёР· СЂС‹РЅРєР°",
                ["analyze", "--symbol", args.symbol, "--interval", args.interval],
                True,
            ),
            (
                "Backtest РїРѕ РёСЃС‚РѕСЂРёС‡РµСЃРєРёРј СЃРІРµС‡Р°Рј",
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
            ("РСЃС‚РѕСЂРёСЏ runner-СЃРµСЃСЃРёР№", ["runner-history", "--limit", "5"], True),
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
        print("РќРµ СѓРґР°Р»РѕСЃСЊ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РѕРїСЂРµРґРµР»РёС‚СЊ runner session id.")
        print("Р­С‚Р°РїС‹ runner-ticks Рё performance-session Р±СѓРґСѓС‚ РїСЂРѕРїСѓС‰РµРЅС‹.")
        skipped.append("Runtime ticks")
        skipped.append("Performance session")
    else:
        print()
        print(f"РћРїСЂРµРґРµР»С‘РЅ runner session id: {runner_session_id}")

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
