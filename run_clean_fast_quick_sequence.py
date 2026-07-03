#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_clean_fast_quick_sequence.py

Запускать из корня traders-ml:

    python run_clean_fast_quick_sequence.py

Что делает:
1. python clean_traders_ml.py --cleanup-commit-only
2. python run_fv3_cached_tuning.py --fast-debug
3. python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT

Команды выполняются строго последовательно.
Если одна команда завершилась с кодом != 0, следующие команды НЕ запускаются.

Скрипт:
- печатает в терминал старт/финиш каждой команды;
- печатает elapsed time во время выполнения;
- пишет общий лог в reports/manual_sequence_runs/<run_id>/sequence_terminal.log;
- пишет итоговый summary в reports/manual_sequence_runs/<run_id>/sequence_summary.txt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable


ELAPSED_PRINT_INTERVAL_SECONDS = 60


COMMANDS: list[tuple[str, list[str]]] = [
    (
        "cleanup_commit_only",
        ["clean_traders_ml.py", "--cleanup-commit-only"],
    ),
    (
        "fast_debug",
        ["run_fv3_cached_tuning.py", "--fast-debug"],
    ),
    (
        "quick_quality_solusdt",
        ["run_fv3_cached_tuning.py", "--quick-quality", "--quick-quality-symbol", "SOLUSDT"],
    ),
]


def now_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def quote_cmd(parts: Iterable[str]) -> str:
    rendered: list[str] = []
    for part in parts:
        if " " in part or "\t" in part:
            rendered.append(f'"{part}"')
        else:
            rendered.append(part)
    return " ".join(rendered)


class TeeLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.log_path.open("a", encoding="utf-8", newline="")
        self._stream_line_open = False

    def write(self, text: str = "") -> None:
        if self._stream_line_open:
            sys.stdout.write("\n")
            self._file.write("\n")
            self._stream_line_open = False
        print(text, flush=True)
        self._file.write(text + "\n")
        self._file.flush()

    def write_stream_chunk(self, text: str, *, is_stderr: bool = False) -> None:
        if not text:
            return
        target = sys.stderr if is_stderr else sys.stdout
        target.write(text)
        target.flush()
        self._file.write(text)
        self._file.flush()
        self._stream_line_open = not text.endswith("\n")

    def close(self) -> None:
        self._file.close()


def reader_thread(
    stream,
    output_queue: "queue.Queue[tuple[bool, str]]",
    is_stderr: bool,
) -> None:
    try:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            output_queue.put((is_stderr, chunk.decode("utf-8", errors="replace")))
    finally:
        try:
            stream.close()
        except Exception:
            pass


def run_command(
    *,
    name: str,
    script_args: list[str],
    repo_root: Path,
    logger: TeeLogger,
    python_executable: str,
    elapsed_interval_seconds: int,
) -> dict[str, object]:
    full_cmd = [python_executable, *script_args]
    display_cmd = ["python", *script_args]

    logger.write("")
    logger.write("=" * 100)
    logger.write(f"[{now_text()}] START: {name}")
    logger.write(f"Working directory: {repo_root}")
    logger.write(f"Command: {quote_cmd(display_cmd)}")
    logger.write(f"Interpreter: {python_executable}")
    logger.write("=" * 100)

    start_monotonic = time.monotonic()
    start_datetime = dt.datetime.now()

    process = subprocess.Popen(
        full_cmd,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        bufsize=0,
    )

    output_queue: "queue.Queue[tuple[bool, str]]" = queue.Queue()

    stdout_thread = threading.Thread(
        target=reader_thread,
        args=(process.stdout, output_queue, False),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=reader_thread,
        args=(process.stderr, output_queue, True),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    last_elapsed_print = start_monotonic

    try:
        while True:
            try:
                is_stderr, chunk = output_queue.get(timeout=1.0)
                logger.write_stream_chunk(chunk, is_stderr=is_stderr)
            except queue.Empty:
                pass

            current = time.monotonic()

            if current - last_elapsed_print >= elapsed_interval_seconds:
                logger.write(
                    f"[{now_text()}] STILL RUNNING: {name} | elapsed {format_duration(current - start_monotonic)}"
                )
                last_elapsed_print = current

            return_code = process.poll()
            if return_code is not None:
                while True:
                    try:
                        is_stderr, chunk = output_queue.get_nowait()
                        logger.write_stream_chunk(chunk, is_stderr=is_stderr)
                    except queue.Empty:
                        break
                break

    except KeyboardInterrupt:
        logger.write("")
        logger.write(f"[{now_text()}] KeyboardInterrupt received. Terminating child process: {name}")
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logger.write(f"[{now_text()}] Child did not terminate in 30s. Killing: {name}")
            process.kill()
            process.wait()
        raise

    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)

    end_monotonic = time.monotonic()
    end_datetime = dt.datetime.now()
    duration_seconds = end_monotonic - start_monotonic
    return_code = int(process.returncode or 0)

    logger.write("-" * 100)
    logger.write(f"[{now_text()}] FINISH: {name}")
    logger.write(f"Return code: {return_code}")
    logger.write(f"Started at: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.write(f"Finished at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.write(f"Duration: {format_duration(duration_seconds)}")
    logger.write("-" * 100)

    return {
        "name": name,
        "command": quote_cmd(display_cmd),
        "return_code": return_code,
        "started_at": start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": duration_seconds,
        "duration_text": format_duration(duration_seconds),
    }


def validate_repo_root(repo_root: Path) -> None:
    missing: list[str] = []
    required_files = {
        "clean_traders_ml.py",
        "run_fv3_cached_tuning.py",
    }
    for filename in required_files:
        if not (repo_root / filename).is_file():
            missing.append(filename)

    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Скрипт нужно запускать из корня traders-ml. Не найдены файлы: {joined}. "
            f"Текущая папка скрипта: {repo_root}"
        )


def write_summary(summary_path: Path, results: list[dict[str, object]], overall_started: dt.datetime) -> None:
    overall_finished = dt.datetime.now()
    total_seconds = (overall_finished - overall_started).total_seconds()

    lines: list[str] = []
    lines.append("Sequential clean/fast/quick run summary")
    lines.append("=" * 80)
    lines.append(f"Started at:  {overall_started.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Finished at: {overall_finished.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total time:  {format_duration(total_seconds)}")
    lines.append("")
    for item in results:
        lines.append(f"- {item['name']}")
        lines.append(f"  command:     {item['command']}")
        lines.append(f"  return_code: {item['return_code']}")
        lines.append(f"  started_at:  {item['started_at']}")
        lines.append(f"  finished_at: {item['finished_at']}")
        lines.append(f"  duration:    {item['duration_text']}")
        lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sequentially run cleanup-commit-only, fast-debug, and quick-quality SOLUSDT "
            "from the traders-ml repository root."
        )
    )
    parser.add_argument(
        "--elapsed-interval-seconds",
        type=int,
        default=ELAPSED_PRINT_INTERVAL_SECONDS,
        help="How often to print elapsed time while a command is running. Default: 60.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with the next command even if the previous command failed. Default: stop on first failure.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parent
    validate_repo_root(repo_root)

    run_id = dt.datetime.now().strftime("sequence_%Y%m%d_%H%M%S")
    output_dir = repo_root / "reports" / "manual_sequence_runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "sequence_terminal.log"
    summary_path = output_dir / "sequence_summary.txt"

    logger = TeeLogger(log_path)
    overall_started = dt.datetime.now()
    results: list[dict[str, object]] = []

    try:
        logger.write("=" * 100)
        logger.write("Sequential traders-ml command runner")
        logger.write("=" * 100)
        logger.write(f"Run ID: {run_id}")
        logger.write(f"Repo root: {repo_root}")
        logger.write(f"Log file: {log_path}")
        logger.write(f"Summary file: {summary_path}")
        logger.write(f"Python executable: {sys.executable}")
        logger.write(f"Elapsed print interval: {args.elapsed_interval_seconds}s")
        logger.write("Commands will run strictly one by one:")
        for index, (name, script_args) in enumerate(COMMANDS, start=1):
            logger.write(f"{index}. {name}: {quote_cmd(['python', *script_args])}")
        logger.write("=" * 100)

        for name, script_args in COMMANDS:
            result = run_command(
                name=name,
                script_args=script_args,
                repo_root=repo_root,
                logger=logger,
                python_executable=sys.executable,
                elapsed_interval_seconds=max(5, int(args.elapsed_interval_seconds)),
            )
            results.append(result)

            if int(result["return_code"]) != 0 and not args.continue_on_error:
                logger.write("")
                logger.write(
                    f"[{now_text()}] STOP: command failed with return code {result['return_code']}: {name}"
                )
                logger.write("Next commands will NOT be started.")
                write_summary(summary_path, results, overall_started)
                logger.write(f"Summary written: {summary_path}")
                return int(result["return_code"])

        write_summary(summary_path, results, overall_started)

        total_duration = (dt.datetime.now() - overall_started).total_seconds()
        logger.write("")
        logger.write("=" * 100)
        logger.write(f"[{now_text()}] ALL COMMANDS FINISHED")
        logger.write(f"Total duration: {format_duration(total_duration)}")
        logger.write(f"Log file: {log_path}")
        logger.write(f"Summary file: {summary_path}")
        logger.write("=" * 100)
        return 0

    finally:
        logger.close()


if __name__ == "__main__":
    raise SystemExit(main())
