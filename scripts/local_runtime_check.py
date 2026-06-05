from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ALEMBIC_HEAD = "0007_backtest_metrics (head)"

FORBIDDEN_SECRET_ENV_NAMES = (
    "BINANCE_API_KEY",
    "BINANCE_SECRET_KEY",
    "BINANCE_PRIVATE_API_KEY",
    "BINANCE_PRIVATE_SECRET",
)

REQUIRED_PROJECT_PATHS = (
    "app",
    "alembic",
    "tests",
    "reports",
    "scripts",
    ".env.example",
    "alembic.ini",
    "docker-compose.yml",
    "pyproject.toml",
)

REQUIRED_DOTENV_KEYS = (
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
    "POSTGRES_PASSWORD",
)

REQUIRED_DOTENV_EXAMPLE_KEYS = (
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
    "POSTGRES_PASSWORD",
)

REQUIRED_DOCKER_COMPOSE_KEYS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
)

KEY_STAGE_TITLES = (
    "РљРѕРЅС‚РµРєСЃС‚ РїСЂРѕРµРєС‚Р°",
    "Safety guard",
    "РџСЂРѕРІРµСЂРєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё",
    "Docker compose config",
    "Docker compose up postgres",
    "Docker inspect postgres",
    "Python settings",
    "Health",
    "Async health",
    "Alembic upgrade head",
    "Alembic current",
    "Demo pipeline",
    "paper runner control check",
)


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


@dataclass(frozen=True)
class CommandSpec:
    title: str
    command: list[str]
    expected_text: tuple[str, ...] = ()
    destructive: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Р›РѕРєР°Р»СЊРЅР°СЏ production-like РїСЂРѕРІРµСЂРєР° РїСЂРѕРµРєС‚Р° traders РІ paper-only СЂРµР¶РёРјРµ."
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    parser.add_argument("--strategy", default="simple_trend")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument(
        "--fresh-db",
        action="store_true",
        help="РЈРґР°Р»СЏРµС‚ Р»РѕРєР°Р»СЊРЅС‹Р№ Docker volume PostgreSQL Рё РїРѕРґРЅРёРјР°РµС‚ Р‘Р” СЃ РЅСѓР»СЏ.",
    )
    return parser.parse_args()


def build_python_command(args: list[str]) -> list[str]:
    return [sys.executable, *args]


def build_cli_command(args: list[str]) -> list[str]:
    return build_python_command(["-m", "app.cli.commands", *args])


def build_alembic_command(args: list[str]) -> list[str]:
    return build_python_command(["-m", "alembic", *args])


def build_demo_command(args: argparse.Namespace) -> list[str]:
    return build_python_command(
        [
            str(PROJECT_ROOT / "scripts" / "demo_traders_pipeline.py"),
            "--symbol",
            args.symbol,
            "--interval",
            args.interval,
            "--days",
            str(args.days),
            "--ticks",
            str(args.ticks),
            "--sleep-seconds",
            str(args.sleep_seconds),
            "--strategy",
            args.strategy,
            "--initial-cash",
            str(args.initial_cash),
        ]
    )


def build_paper_runner_control_command(args: argparse.Namespace) -> list[str]:
    return build_python_command(
        [
            str(PROJECT_ROOT / "scripts" / "paper_runner_control_check.py"),
            "--symbol",
            args.symbol,
            "--interval",
            args.interval,
            "--ticks",
            str(args.ticks),
            "--initial-cash",
            str(args.initial_cash),
        ]
    )


def build_docker_commands(fresh_db: bool) -> list[CommandSpec]:
    commands = [
        CommandSpec(
            title="Docker compose config",
            command=["docker", "compose", "config"],
            expected_text=("postgres",),
        ),
    ]

    if fresh_db:
        commands.append(
            CommandSpec(
                title="Fresh DB: docker compose down -v",
                command=["docker", "compose", "down", "-v"],
                destructive=True,
            )
        )

    commands.extend(
        [
            CommandSpec(
                title="Docker compose up postgres",
                command=["docker", "compose", "up", "-d", "postgres"],
            ),
            CommandSpec(
                title="Docker compose ps",
                command=["docker", "compose", "ps"],
                expected_text=("postgres",),
            ),
            CommandSpec(
                title="Docker inspect postgres",
                command=[
                    "docker",
                    "inspect",
                    "traders_postgres",
                    "--format",
                    "{{.State.Status}}",
                ],
                expected_text=("running",),
            ),
        ]
    )

    return commands


def build_runtime_command_specs(args: argparse.Namespace) -> list[CommandSpec]:
    return [
        *build_docker_commands(args.fresh_db),
        CommandSpec(
            title="Python settings",
            command=build_python_command(
                [
                    "-c",
                    (
                        "from app.config.settings import get_settings; "
                        "s=get_settings(); "
                        "print('DATABASE_URL=' + s.database_url); "
                        "print('ASYNC_DATABASE_URL=' + str(s.async_database_url))"
                    ),
                ]
            ),
            expected_text=("postgresql+psycopg://", "postgresql+asyncpg://"),
        ),
        CommandSpec(
            title="Health",
            command=build_cli_command(["health"]),
            expected_text=("OK: app loaded", "OK: database connected"),
        ),
        CommandSpec(
            title="Async health",
            command=build_cli_command(["async-health"]),
            expected_text=("OK: async database connected",),
        ),
        CommandSpec(
            title="Alembic upgrade head",
            command=build_alembic_command(["upgrade", "head"]),
        ),
        CommandSpec(
            title="Alembic current",
            command=build_alembic_command(["current"]),
            expected_text=(EXPECTED_ALEMBIC_HEAD,),
        ),
        CommandSpec(
            title="Demo pipeline",
            command=build_demo_command(args),
            expected_text=(
                "Backtest performance: OK",
                "Session compare: OK",
                "Live trading",
            ),
        ),
        CommandSpec(
            title="paper runner control check",
            command=build_paper_runner_control_command(args),
            expected_text=("[OK] paper-runner disabled", "runner session id:"),
        ),
    ]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}

    if not path.exists():
        return values

    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def mask_url(value: str) -> str:
    return re.sub(r"(://[^:/@\s]+:)[^@\s]+(@)", r"\1***\2", value)


def collect_sensitive_values() -> list[str]:
    values: list[str] = []

    for key in (
        *REQUIRED_DOTENV_KEYS,
        *FORBIDDEN_SECRET_ENV_NAMES,
    ):
        value = os.environ.get(key)
        if value:
            values.append(value)

    dotenv_values = read_dotenv_values(PROJECT_ROOT / ".env")
    for key in (
        *REQUIRED_DOTENV_KEYS,
        *FORBIDDEN_SECRET_ENV_NAMES,
    ):
        value = dotenv_values.get(key)
        if value:
            values.append(value)

    return sorted(set(values), key=len, reverse=True)


def mask_sensitive_text(text: str) -> str:
    masked = mask_url(text)

    for value in collect_sensitive_values():
        if value:
            masked = masked.replace(value, "***")

    return masked


def mask_env_status(name: str, dotenv_values: dict[str, str]) -> str:
    if os.environ.get(name):
        return "Р·Р°РґР°РЅ РІ РѕРєСЂСѓР¶РµРЅРёРё"

    if dotenv_values.get(name):
        return "Р·Р°РґР°РЅ РІ .env"

    return "РЅРµ Р·Р°РґР°РЅ"


def print_header(args: argparse.Namespace) -> None:
    dotenv_values = read_dotenv_values(PROJECT_ROOT / ".env")

    print("=" * 80)
    print("STAGE 7 вЂ” LOCAL PRODUCTION-LIKE RUNTIME")
    print("=" * 80)
    print("Р РµР¶РёРј: paper-only")
    print("Р РµР°Р»СЊРЅС‹Рµ РѕСЂРґРµСЂР°: Р·Р°РїСЂРµС‰РµРЅС‹")
    print("Binance private API: РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ")
    print("Server deploy: РЅРµ РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ")
    print("Daemon: РЅРµ Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ")
    print("-" * 80)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print(f"Fresh DB: {'Р”Рђ' if args.fresh_db else 'РќР•Рў'}")
    print("-" * 80)
    print(f"DATABASE_URL: {mask_env_status('DATABASE_URL', dotenv_values)}")
    print(f"ASYNC_DATABASE_URL: {mask_env_status('ASYNC_DATABASE_URL', dotenv_values)}")
    print(f"POSTGRES_PASSWORD: {mask_env_status('POSTGRES_PASSWORD', dotenv_values)}")
    print("=" * 80)


def print_step_header(step_number: int, total_steps: int, title: str) -> None:
    print()
    print(f"[{step_number}/{total_steps}] {title}")


def print_step_result(result: StepResult) -> None:
    if result.command:
        print(f"РљРѕРјР°РЅРґР°: {' '.join(result.command)}")

    if result.stdout:
        print("-" * 80)
        print(mask_sensitive_text(result.stdout.strip()))

    if result.stderr:
        print("-" * 80)
        print("STDERR:")
        print(mask_sensitive_text(result.stderr.strip()))

    status = "OK" if result.ok else "ERROR"
    print("-" * 80)
    print(f"Status: {status}")


def internal_step(
    step_number: int,
    total_steps: int,
    title: str,
    callback: Callable[[], str],
) -> StepResult:
    print_step_header(step_number, total_steps, title)

    try:
        stdout = callback()
        result = StepResult(
            title=title,
            command=[],
            returncode=0,
            stdout=stdout,
            stderr="",
        )
    except Exception as exc:
        result = StepResult(
            title=title,
            command=[],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )

    print_step_result(result)
    return result


def run_command_step(
    step_number: int,
    total_steps: int,
    spec: CommandSpec,
) -> StepResult:
    print_step_header(step_number, total_steps, spec.title)

    try:
        completed = subprocess.run(
            spec.command,
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        returncode = completed.returncode
    except FileNotFoundError as exc:
        stdout = ""
        stderr = f"РљРѕРјР°РЅРґР° РЅРµ РЅР°Р№РґРµРЅР°: {exc}"
        returncode = 127

    combined_output = f"{stdout}\n{stderr}"

    missing_expected = [
        expected for expected in spec.expected_text if expected not in combined_output
    ]

    if returncode == 0 and missing_expected:
        returncode = 1
        expected_message = (
            "РћР¶РёРґР°РµРјС‹Р№ С‚РµРєСЃС‚ РЅРµ РЅР°Р№РґРµРЅ: " + ", ".join(repr(x) for x in missing_expected)
        )
        stderr = f"{stderr}\n{expected_message}".strip()

    result = StepResult(
        title=spec.title,
        command=spec.command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )

    print_step_result(result)
    return result


def detect_forbidden_env() -> list[str]:
    return [name for name in FORBIDDEN_SECRET_ENV_NAMES if os.environ.get(name)]


def check_project_context() -> str:
    lines = [
        f"PROJECT_ROOT: {PROJECT_ROOT}",
        f"РљР°С‚Р°Р»РѕРі РїСЂРѕРµРєС‚Р°: {PROJECT_ROOT.name}",
        f"Python executable: {sys.executable}",
        f"Platform: {platform.platform()}",
    ]

    if PROJECT_ROOT.name.lower() != "traders":
        raise RuntimeError(
            f"РЎРєСЂРёРїС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Р·Р°РїСѓС‰РµРЅ РёР· РїСЂРѕРµРєС‚Р° traders, С‚РµРєСѓС‰РёР№ РєР°С‚Р°Р»РѕРі: {PROJECT_ROOT.name}"
        )

    missing_paths = [
        rel_path for rel_path in REQUIRED_PROJECT_PATHS if not (PROJECT_ROOT / rel_path).exists()
    ]

    if missing_paths:
        raise RuntimeError("РќРµ РЅР°Р№РґРµРЅС‹ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ СЌР»РµРјРµРЅС‚С‹ РїСЂРѕРµРєС‚Р°: " + ", ".join(missing_paths))

    lines.append("РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ СЌР»РµРјРµРЅС‚С‹ РїСЂРѕРµРєС‚Р°: OK")
    return "\n".join(lines)


def check_safety_guard() -> str:
    forbidden = detect_forbidden_env()

    lines = [
        "Р РµР¶РёРј: paper-only",
        "Р РµР°Р»СЊРЅС‹Рµ РѕСЂРґРµСЂР°: Р·Р°РїСЂРµС‰РµРЅС‹",
        "Binance private API: РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ",
        "Server deploy: РЅРµ РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ",
        "Daemon: РЅРµ Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ",
    ]

    if forbidden:
        for name in forbidden:
            lines.append(f"{name}: РЅР°Р№РґРµРЅР° Р·Р°РїСЂРµС‰С‘РЅРЅР°СЏ РїРµСЂРµРјРµРЅРЅР°СЏ")
        raise RuntimeError("\n".join(lines))

    lines.append("Р—Р°РїСЂРµС‰С‘РЅРЅС‹Рµ Binance private env РїРµСЂРµРјРµРЅРЅС‹Рµ: РЅРµ РЅР°Р№РґРµРЅС‹")
    return "\n".join(lines)


def require_keys(source_name: str, text: str, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key not in text]


def check_config_consistency() -> str:
    dotenv_path = PROJECT_ROOT / ".env"
    dotenv_example_path = PROJECT_ROOT / ".env.example"
    docker_compose_path = PROJECT_ROOT / "docker-compose.yml"
    alembic_ini_path = PROJECT_ROOT / "alembic.ini"

    if not dotenv_path.exists():
        raise RuntimeError("Р¤Р°Р№Р» .env РЅРµ РЅР°Р№РґРµРЅ.")

    dotenv_values = read_dotenv_values(dotenv_path)
    dotenv_example_text = read_text(dotenv_example_path)
    docker_compose_text = read_text(docker_compose_path)
    alembic_ini_text = read_text(alembic_ini_path)

    missing_dotenv_keys = [key for key in REQUIRED_DOTENV_KEYS if not dotenv_values.get(key)]
    missing_example_keys = require_keys(
        ".env.example", dotenv_example_text, REQUIRED_DOTENV_EXAMPLE_KEYS
    )
    missing_compose_keys = require_keys(
        "docker-compose.yml", docker_compose_text, REQUIRED_DOCKER_COMPOSE_KEYS
    )

    if missing_dotenv_keys:
        raise RuntimeError(".env РЅРµ СЃРѕРґРµСЂР¶РёС‚ РєР»СЋС‡Рё: " + ", ".join(missing_dotenv_keys))

    if missing_example_keys:
        raise RuntimeError(
            ".env.example РЅРµ СЃРѕРґРµСЂР¶РёС‚ РєР»СЋС‡Рё: " + ", ".join(missing_example_keys)
        )

    if missing_compose_keys:
        raise RuntimeError(
            "docker-compose.yml РЅРµ СЃРѕРґРµСЂР¶РёС‚ РєР»СЋС‡Рё: " + ", ".join(missing_compose_keys)
        )

    if "sqlalchemy.url" not in alembic_ini_text:
        raise RuntimeError("alembic.ini РЅРµ СЃРѕРґРµСЂР¶РёС‚ fallback sqlalchemy.url.")

    if "traders:traders@" in alembic_ini_text:
        raise RuntimeError("alembic.ini СЃРѕРґРµСЂР¶РёС‚ СѓСЃС‚Р°СЂРµРІС€РёР№ fallback traders:traders@.")

    database_url = dotenv_values["DATABASE_URL"]
    async_database_url = dotenv_values["ASYNC_DATABASE_URL"]

    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL РґРѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ postgresql+psycopg://")

    if not async_database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("ASYNC_DATABASE_URL РґРѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ postgresql+asyncpg://")

    return "\n".join(
        [
            ".env: OK",
            ".env.example: OK",
            "docker-compose.yml: OK",
            "alembic.ini: OK",
            f"DATABASE_URL: {mask_url(database_url)}",
            f"ASYNC_DATABASE_URL: {mask_url(async_database_url)}",
            "POSTGRES_PASSWORD: Р·Р°РґР°РЅ",
        ]
    )


def wait_for_postgres_container() -> StepResult:
    command = [
        "docker",
        "inspect",
        "traders_postgres",
        "--format",
        "{{.State.Status}}",
    ]

    last_stdout = ""
    last_stderr = ""

    for _ in range(15):
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
        last_stdout = completed.stdout.strip()
        last_stderr = completed.stderr.strip()

        if completed.returncode == 0 and "running" in last_stdout:
            return StepResult(
                title="РћР¶РёРґР°РЅРёРµ PostgreSQL container",
                command=command,
                returncode=0,
                stdout=last_stdout,
                stderr=last_stderr,
            )

        time.sleep(1)

    return StepResult(
        title="РћР¶РёРґР°РЅРёРµ PostgreSQL container",
        command=command,
        returncode=1,
        stdout=last_stdout,
        stderr=last_stderr or "РљРѕРЅС‚РµР№РЅРµСЂ traders_postgres РЅРµ РїРµСЂРµС€С‘Р» РІ СЃРѕСЃС‚РѕСЏРЅРёРµ running.",
    )


def print_footer(results: list[StepResult]) -> int:
    failed = [result for result in results if not result.ok]

    print()
    print("=" * 80)
    print("RESULT LOCAL PRODUCTION-LIKE RUNTIME")
    print("=" * 80)

    for result in results:
        status = "OK" if result.ok else "ERROR"
        print(f"- {result.title}: {status}")

    print("-" * 80)

    if failed:
        first = failed[0]
        print("STATUS: ERROR")
        print("First failed step:")
        print(first.title)

        if first.command:
            print(f"Command: {' '.join(first.command)}")

        print(f"Exit code: {first.returncode}")

        if first.stdout:
            print("STDOUT:")
            print(mask_sensitive_text(first.stdout))

        if first.stderr:
            print("STDERR:")
            print(mask_sensitive_text(first.stderr))

        print("=" * 80)
        return 1

    print("STATUS: SUCCESS")
    print("Local production-like runtime РїСЂРѕРІРµСЂРµРЅ.")
    print("PostgreSQL СЂР°Р±РѕС‚Р°РµС‚.")
    print("Alembic РЅР° head.")
    print("Health OK.")
    print("Async health OK.")
    print("Demo pipeline OK.")
    print("Live trading РЅРµ РёСЃРїРѕР»СЊР·РѕРІР°Р»СЃСЏ.")
    print("Server deploy РЅРµ РІС‹РїРѕР»РЅСЏР»СЃСЏ.")
    print("Daemon РЅРµ Р·Р°РїСѓСЃРєР°Р»СЃСЏ.")
    print("=" * 80)
    return 0


def main() -> int:
    args = parse_args()
    print_header(args)

    results: list[StepResult] = []

    internal_checks: list[tuple[str, Callable[[], str]]] = [
        ("РљРѕРЅС‚РµРєСЃС‚ РїСЂРѕРµРєС‚Р°", check_project_context),
        ("Safety guard", check_safety_guard),
        ("РџСЂРѕРІРµСЂРєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё", check_config_consistency),
    ]

    total_steps = len(internal_checks) + len(build_runtime_command_specs(args)) + 1

    step_number = 1

    for title, callback in internal_checks:
        result = internal_step(step_number, total_steps, title, callback)
        results.append(result)

        if not result.ok:
            return print_footer(results)

        step_number += 1

    for spec in build_docker_commands(args.fresh_db):
        result = run_command_step(step_number, total_steps, spec)
        results.append(result)

        if not result.ok:
            return print_footer(results)

        step_number += 1

    wait_result = wait_for_postgres_container()
    print_step_header(step_number, total_steps, wait_result.title)
    print_step_result(wait_result)
    results.append(wait_result)

    if not wait_result.ok:
        return print_footer(results)

    step_number += 1

    remaining_specs = [
        spec
        for spec in build_runtime_command_specs(args)
        if spec.title
        not in {
            "Docker compose config",
            "Fresh DB: docker compose down -v",
            "Docker compose up postgres",
            "Docker compose ps",
            "Docker inspect postgres",
        }
    ]

    for spec in remaining_specs:
        result = run_command_step(step_number, total_steps, spec)
        results.append(result)

        if not result.ok:
            return print_footer(results)

        step_number += 1

    return print_footer(results)


if __name__ == "__main__":
    raise SystemExit(main())


