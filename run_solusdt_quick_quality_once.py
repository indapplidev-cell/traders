from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from typing import Sequence, TextIO


DISPLAY_COMMAND = (
    "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT"
)
CHILD_ARGUMENTS = (
    "run_fv3_cached_tuning.py",
    "--quick-quality",
    "--quick-quality-symbol",
    "SOLUSDT",
)
REPO_ROOT = Path(__file__).resolve().parent
EXTERNAL_LOG_DIR = Path(r"D:\disk_E\game_projects\traders\traders-ml-run-logs")
PROGRESS_INTERVAL_SECONDS = 20 * 60
ACKNOWLEDGEMENT_FLAG = "--i-understand-this-runs-real-quick-quality"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan, or explicitly execute once, the fixed SOLUSDT quick-quality command."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="request real execution; also requires the acknowledgement flag",
    )
    parser.add_argument(
        ACKNOWLEDGEMENT_FLAG,
        dest="acknowledged",
        action="store_true",
        help="acknowledge that --execute starts real quick-quality",
    )
    return parser


def _path_templates() -> tuple[Path, Path]:
    stamp = "<YYYYMMDD_HHMMSS>"
    return (
        EXTERNAL_LOG_DIR / f"solusdt_quick_quality_{stamp}.log",
        EXTERNAL_LOG_DIR / f"solusdt_quick_quality_{stamp}.completion.json",
    )


def print_dry_run_plan() -> None:
    log_path, marker_path = _path_templates()
    print("Mode: dry-run / plan (default)")
    print(f"Exact command: {DISPLAY_COMMAND}")
    print(f"CWD: {REPO_ROOT}")
    print(f"External log path template: {log_path}")
    print(f"Completion marker path template: {marker_path}")
    print("Safety constraints:")
    print("- SOLUSDT 15m only; BTC, ETH, and multi-symbol are forbidden")
    print("- clean, fast-debug, sequence, cascade/outcome, and custom commands are forbidden")
    print("- execute requires a clean git status and both explicit execution flags")
    print("- logs and completion evidence stay outside reports/")
    print("REAL QUICK-QUALITY WAS NOT RUN")


def _require_clean_git_status() -> tuple[bool, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"git status exited {result.returncode}"
        return False, detail
    if result.stdout.strip():
        return False, "git working tree is not clean"
    return True, ""


def _timestamp_pair() -> dict[str, str]:
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "local": datetime.now().astimezone().isoformat(),
    }


def _reader(stream: TextIO, output: queue.Queue[str]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output.put(line)
    finally:
        stream.close()


def _emit(line: str, log_file: TextIO) -> None:
    print(line, end="" if line.endswith("\n") else "\n", flush=True)
    log_file.write(line)
    if not line.endswith("\n"):
        log_file.write("\n")
    log_file.flush()


def _drain_output(output: queue.Queue[str], log_file: TextIO) -> None:
    while True:
        try:
            _emit(output.get_nowait(), log_file)
        except queue.Empty:
            return


def execute_once() -> int:
    clean, reason = _require_clean_git_status()
    if not clean:
        print(f"Refusing execute: {reason}", file=sys.stderr)
        return 2

    EXTERNAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    log_path = EXTERNAL_LOG_DIR / f"solusdt_quick_quality_{stamp}.log"
    marker_path = EXTERNAL_LOG_DIR / f"solusdt_quick_quality_{stamp}.completion.json"
    started = _timestamp_pair()
    monotonic_start = time.monotonic()
    child_exit_code: int | None = None
    launch_error: str | None = None

    with log_path.open("x", encoding="utf-8", newline="\n") as log_file:
        _emit(f"start_utc: {started['utc']}", log_file)
        _emit(f"start_local: {started['local']}", log_file)
        _emit(f"cwd: {REPO_ROOT}", log_file)
        _emit(f"command: {DISPLAY_COMMAND}", log_file)
        _emit(f"python_executable: {sys.executable}", log_file)

        process: subprocess.Popen[str] | None = None
        reader_thread: threading.Thread | None = None
        output: queue.Queue[str] = queue.Queue()
        try:
            process = subprocess.Popen(
                [sys.executable, *CHILD_ARGUMENTS],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            reader_thread = threading.Thread(
                target=_reader, args=(process.stdout, output), daemon=True
            )
            reader_thread.start()
            next_progress = monotonic_start + PROGRESS_INTERVAL_SECONDS
            while process.poll() is None:
                _drain_output(output, log_file)
                now = time.monotonic()
                if now >= next_progress:
                    elapsed_minutes = int((now - monotonic_start) // 60)
                    _emit(f"elapsed_progress_minutes: {elapsed_minutes}", log_file)
                    next_progress += PROGRESS_INTERVAL_SECONDS
                time.sleep(1)
            child_exit_code = process.wait()
            if reader_thread is not None:
                reader_thread.join()
            _drain_output(output, log_file)
        except KeyboardInterrupt:
            if process is not None and process.poll() is None:
                process.terminate()
                child_exit_code = process.wait()
            if reader_thread is not None:
                reader_thread.join()
            _drain_output(output, log_file)
            launch_error = "KeyboardInterrupt: parent interrupted; child terminated"
            _emit(f"interruption: {launch_error}", log_file)
        except Exception as exc:
            launch_error = f"{type(exc).__name__}: {exc}"
            _emit(f"launch_error: {launch_error}", log_file)
        finally:
            ended = _timestamp_pair()
            elapsed_seconds = time.monotonic() - monotonic_start
            _emit(f"end_utc: {ended['utc']}", log_file)
            _emit(f"end_local: {ended['local']}", log_file)
            _emit(f"elapsed_seconds: {elapsed_seconds:.3f}", log_file)
            _emit(f"child_exit_code: {child_exit_code!r}", log_file)

            marker = {
                "command": DISPLAY_COMMAND,
                "cwd": str(REPO_ROOT),
                "python_executable": sys.executable,
                "start_timestamps": started,
                "end_timestamps": ended,
                "elapsed_seconds": elapsed_seconds,
                "child_exit_code": child_exit_code,
                "exit_code_known": child_exit_code is not None,
                "launch_error": launch_error,
                "log_path": str(log_path),
            }
            marker_path.write_text(
                json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(f"Completion marker: {marker_path}")

    if child_exit_code is None:
        print("Child exit code is unknown; failing closed.", file=sys.stderr)
        return 1
    return child_exit_code


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.execute:
        print_dry_run_plan()
        return 0
    if not args.acknowledged:
        print(
            f"Refusing execute: --execute also requires {ACKNOWLEDGEMENT_FLAG}",
            file=sys.stderr,
        )
        return 2
    return execute_once()


if __name__ == "__main__":
    raise SystemExit(main())
