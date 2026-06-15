#!/usr/bin/env python
"""Generic fresh FV3 tuning wrapper for traders-ml.

Place this file in the root of traders-ml:

    D:\disk_E\game_projects\traders\traders-ml\run_fv3_fresh_tuning.py

Default behavior:
- always runs fresh training results, never reuses old experiment summaries;
- runs BTCUSDT / ETHUSDT / SOLUSDT on 15m from 2025-01-01 to 2026-06-15;
- prints stage statuses to the terminal;
- shows a lightweight progress/status indicator while symbol runs are processing;
- creates a wrapper-owned archive under reports/feature_regime_experiments/;
- writes archive_manifest.json with generic, reusable metadata;
- keeps manual_archive_assembly_used = false.

Run:

    python run_fv3_fresh_tuning.py

Sequential run:

    python run_fv3_fresh_tuning.py --sequential

Strict validation:

    python run_fv3_fresh_tuning.py --strict-validation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STAGE_NAME = "FV3_FRESH_TUNING"
DEFAULT_STAGE_CONTEXT = "Fresh FV3 tuning rerun after gap semantics and runtime stability fixes"
FEATURE_VERSION = "fv3_candle_ta_context"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_INTERVAL = "15m"
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2026-06-15"
EXPECTED_CANDIDATE_COUNT = 24


@dataclass(frozen=True)
class SymbolRunResult:
    symbol: str
    mode: str
    experiment_id: str
    output_dir: str | None
    summary_json_path: str | None
    summary_markdown_path: str | None
    candidate_count: int | None
    accepted_candidate_count: int | None
    rejected_candidate_count: int | None
    failed_candidate_count: int | None
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    stdout_path: str
    stderr_path: str


class WrapperError(RuntimeError):
    """Wrapper-level error."""


class TerminalProgress:
    """Small terminal progress helper without external dependencies."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled and sys.stdout.isatty()
        self._last_len = 0

    def update(self, message: str) -> None:
        if not self.enabled:
            return

        clean = message[:180]
        text = "\r" + clean
        padding = " " * max(0, self._last_len - len(clean))
        print(text + padding, end="", flush=True)
        self._last_len = len(clean)

    def done(self) -> None:
        if not self.enabled:
            return

        print("\r" + " " * self._last_len + "\r", end="", flush=True)
        self._last_len = 0


class FreshFv3TuningWrapper:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parent
        self.python_exe = self._resolve_python_exe()
        self.symbols = tuple(part.strip().upper() for part in args.symbols.split(",") if part.strip())
        self.interval = args.interval
        self.start_date = args.start_date
        self.end_date = args.end_date
        self.stage_name = args.stage_name
        self.stage_context = args.stage_context
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.output_root = self.repo_root / "reports" / "feature_regime_experiments"

        symbols_part = "_".join(symbol.lower() for symbol in self.symbols)
        self.archive_base_name = f"fv3_fresh_tuning_{symbols_part}_{self.interval}_{self.timestamp}"
        self.archive_stage_dir = self.output_root / self.archive_base_name
        self.archive_path = self.output_root / f"{self.archive_base_name}.zip"
        self.raw_output_dir = self.archive_stage_dir / "raw_outputs"
        self.per_symbol_stage_dir = self.archive_stage_dir / "per_symbol_experiments"
        self.log_path = self.archive_stage_dir / "fresh_grid_run.log"
        self.manifest_path = self.archive_stage_dir / "archive_manifest.json"
        self.analysis_json_path = self.repo_root / "reports" / "multi_symbol_feature_regime_analysis.json"
        self.analysis_markdown_path = self.repo_root / "reports" / "multi_symbol_feature_regime_analysis.md"
        self.stage_report_path = Path(args.stage_report_path).resolve() if args.stage_report_path else None
        self.script_path = Path(__file__).resolve()
        self.progress = TerminalProgress(enabled=not args.no_progress)

        self.stage_initialized = False
        self.current_branch: str | None = None
        self.run_results: list[SymbolRunResult] = []
        self.failed_symbols: list[str] = []
        self.multi_symbol_result: dict[str, Any] | None = None

    def run(self) -> dict[str, Any]:
        self._print_banner()
        self._preflight()
        self._ensure_stage_dirs()

        try:
            self._run_health_checks()

            run_in_parallel = not self.args.sequential
            self._start_fresh_symbol_runs(run_in_parallel=run_in_parallel)
            self._stage_selected_runs()

            self.multi_symbol_result = self._run_multi_symbol_analysis()
            archive_item = self._finalize_archive(wrapper_completed_end_to_end=True)

            result = self._build_final_result(
                status="ok",
                wrapper_completed_end_to_end=True,
                archive_size_bytes=archive_item.stat().st_size,
            )

            self._status("DONE", f"Fresh archive path: {self.archive_path}")
            self._status("DONE", f"Fresh archive size bytes: {archive_item.stat().st_size}")

            if self.args.strict_validation and not result["validation"]["strict_validation_ok"]:
                raise WrapperError(
                    "Strict validation failed. Archive was created, but validation flags are not all OK."
                )

            return result
        except Exception as exc:
            self._status("ERROR", str(exc))
            if self.stage_initialized:
                try:
                    self._stage_selected_runs()
                    self._finalize_archive(wrapper_completed_end_to_end=False)
                    self._status("ERROR", f"Failure debug archive path: {self.archive_path}")
                except Exception as secondary:
                    self._status("ERROR", f"Secondary failure while finalizing failed-debug archive: {secondary}")

            raise

    def _print_banner(self) -> None:
        print("=" * 88)
        print(f"Fresh FV3 tuning wrapper")
        print(f"Stage name: {self.stage_name}")
        print(f"Context: {self.stage_context}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Interval: {self.interval}")
        print(f"Date range: {self.start_date} -> {self.end_date}")
        print(f"Mode: {'sequential' if self.args.sequential else 'parallel'}")
        print("=" * 88)

    def _resolve_python_exe(self) -> Path:
        candidate = self.repo_root / ".venv" / "Scripts" / "python.exe"
        if candidate.exists():
            return candidate
        return Path(sys.executable)

    def _preflight(self) -> None:
        if not self.repo_root.exists():
            raise WrapperError(f"Repository root not found: {self.repo_root}")

        if not self.python_exe.exists():
            raise WrapperError(f"Python executable not found: {self.python_exe}")

        os.chdir(self.repo_root)
        self._status("PREFLIGHT", f"Repository root: {self.repo_root}")
        self._status("PREFLIGHT", f"Python executable: {self.python_exe}")

        self.current_branch = self._run_command_capture(["git", "branch", "--show-current"], "git branch --show-current").strip()
        self._status("PREFLIGHT", f"Git branch: {self.current_branch}")

        git_status = self._run_command_capture(["git", "status", "--short"], "git status --short").strip()
        filtered_status = self._filter_git_status(git_status)

        if filtered_status:
            raise WrapperError(
                "Repository must be clean before wrapper start.\n"
                "Commit code changes and clean runtime artifacts first.\n\n"
                f"{filtered_status}"
            )

        self._status("PREFLIGHT", "Git working tree is clean enough for wrapper start.")

    def _filter_git_status(self, raw_status: str) -> str:
        if not raw_status:
            return ""

        filtered: list[str] = []
        for line in raw_status.splitlines():
            normalized = line.strip()
            if not normalized:
                continue

            path = self._status_path(normalized)
            if self.args.allow_runtime_dirty and self._is_runtime_artifact(path):
                continue

            if self.args.allow_self_untracked and self._is_self_status_path(path):
                continue

            filtered.append(line)

        return "\n".join(filtered).strip()

    def _status_path(self, status_line: str) -> str:
        path = re.sub(r"^[ MARC\?D!U]{1,3}\s+", "", status_line).strip()
        return path.replace("\\", "/")

    def _is_self_status_path(self, status_path: str) -> bool:
        try:
            self_rel = self.script_path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return False

        return status_path == self_rel

    def _is_runtime_artifact(self, status_path: str) -> bool:
        patterns = (
            r"^reports/feature_regime_experiments/",
            r"^reports/label_grid_experiments/",
            r"^reports/baseline_.*\.json$",
            r"^reports/dataset_summary_.*\.json$",
            r"^reports/model_comparison_.*\.json$",
            r"^reports/model_diagnostics_.*\.json$",
            r"^reports/probability_diagnostics_.*\.json$",
            r"^reports/profit_eval_v2_.*\.json$",
            r"^reports/calibration_eval_.*\.json$",
            r"^reports/walk_forward_eval_.*\.json$",
            r"^reports/multi_symbol_feature_regime_analysis\.(json|md)$",
        )
        return any(re.match(pattern, status_path) for pattern in patterns)

    def _ensure_stage_dirs(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)

        if self.archive_stage_dir.exists():
            shutil.rmtree(self.archive_stage_dir)

        if self.archive_path.exists():
            self.archive_path.unlink()

        self.raw_output_dir.mkdir(parents=True, exist_ok=True)
        self.per_symbol_stage_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("", encoding="utf-8")
        self.stage_initialized = True

        self._status("SETUP", f"Archive stage dir: {self.archive_stage_dir}")
        self._status("SETUP", f"Archive path: {self.archive_path}")

    def _run_health_checks(self) -> None:
        self._status("HEALTH", "Running service health check...")
        self._run_command_capture(
            [str(self.python_exe), "-m", "app.cli.commands", "health"],
            "python -m app.cli.commands health",
        )
        self._status("HEALTH", "Running DB check...")
        self._run_command_capture(
            [str(self.python_exe), "-m", "app.cli.commands", "db-check"],
            "python -m app.cli.commands db-check",
        )
        self._status("HEALTH", "Health and DB checks passed.")

    def _start_fresh_symbol_runs(self, *, run_in_parallel: bool) -> None:
        if run_in_parallel:
            self._start_parallel_symbol_runs()
            return

        for index, symbol in enumerate(self.symbols, start=1):
            self._status("SYMBOL", f"[{index}/{len(self.symbols)}] Starting {symbol}")
            self._run_single_symbol(symbol, index=index, total=len(self.symbols))

    def _symbol_command(self, symbol: str, experiment_id: str) -> list[str]:
        command = [
            str(self.python_exe),
            "-m",
            "app.cli.commands",
            "ml38-2-fv3-tuning-run",
            "--symbol",
            symbol,
            "--interval",
            self.interval,
            "--start-date",
            self.start_date,
            "--end-date",
            self.end_date,
            "--experiment-id",
            experiment_id,
        ]

        if self.args.max_configs is not None:
            command.extend(["--max-configs", str(self.args.max_configs)])

        if self.args.dry_run:
            command.append("--dry-run")

        if self.args.sample_mode:
            command.append("--sample-mode")

        return command

    def _experiment_id(self, symbol: str) -> str:
        return f"fv3_fresh_tuning_{symbol.lower()}_{self.interval}_{self.timestamp}"

    def _run_single_symbol(self, symbol: str, *, index: int, total: int) -> None:
        experiment_id = self._experiment_id(symbol)
        stdout_path = self.raw_output_dir / f"{symbol}-run.stdout.json"
        stderr_path = self.raw_output_dir / f"{symbol}-run.stderr.log"
        command = self._symbol_command(symbol, experiment_id)

        started_at = datetime.now(timezone.utc)
        self._status("SYMBOL", f"[{index}/{total}] {symbol}: fresh training started. experiment_id={experiment_id}")

        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                check=False,
            )

        finished_at = datetime.now(timezone.utc)
        duration_seconds = round((finished_at - started_at).total_seconds(), 3)

        if completed.returncode != 0:
            self.failed_symbols.append(symbol)
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
            raise WrapperError(f"Symbol run failed for {symbol} with exit code {completed.returncode}\n{stderr_text}")

        payload = self._read_json(stdout_path)
        self.run_results.append(
            self._symbol_result_from_payload(
                symbol=symbol,
                experiment_id=experiment_id,
                payload=payload,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration_seconds,
                exit_code=completed.returncode,
            )
        )

        self._status(
            "SYMBOL",
            f"[{index}/{total}] {symbol}: completed in {duration_seconds:.1f}s. "
            f"candidates={payload.get('candidate_count')} accepted={payload.get('accepted_candidate_count')} "
            f"rejected={payload.get('rejected_candidate_count')} failed={payload.get('failed_candidate_count')}",
        )

    def _start_parallel_symbol_runs(self) -> None:
        started_runs: list[dict[str, Any]] = []

        self._status("SYMBOL", f"Starting {len(self.symbols)} parallel symbol runs...")

        for index, symbol in enumerate(self.symbols, start=1):
            experiment_id = self._experiment_id(symbol)
            stdout_path = self.raw_output_dir / f"{symbol}-run.stdout.json"
            stderr_path = self.raw_output_dir / f"{symbol}-run.stderr.log"
            command = self._symbol_command(symbol, experiment_id)
            started_at = datetime.now(timezone.utc)

            self._status("SYMBOL", f"[{index}/{len(self.symbols)}] Launching {symbol}. experiment_id={experiment_id}")

            stdout_file = stdout_path.open("w", encoding="utf-8")
            stderr_file = stderr_path.open("w", encoding="utf-8")

            process = subprocess.Popen(
                command,
                cwd=self.repo_root,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )

            started_runs.append(
                {
                    "index": index,
                    "symbol": symbol,
                    "experiment_id": experiment_id,
                    "stdout_path": stdout_path,
                    "stderr_path": stderr_path,
                    "started_at": started_at,
                    "process": process,
                    "stdout_file": stdout_file,
                    "stderr_file": stderr_file,
                }
            )

        pending = {run["symbol"]: run for run in started_runs}
        completed_count = 0
        spinner = "|/-\\"
        spinner_index = 0

        while pending:
            done_symbols: list[str] = []
            elapsed_parts: list[str] = []

            for symbol, run in pending.items():
                elapsed = int((datetime.now(timezone.utc) - run["started_at"]).total_seconds())
                elapsed_parts.append(f"{symbol}:{elapsed}s")

                process = run["process"]
                exit_code = process.poll()
                if exit_code is None:
                    continue

                run["exit_code"] = int(exit_code)
                run["finished_at"] = datetime.now(timezone.utc)
                done_symbols.append(symbol)

            self.progress.update(
                f"{spinner[spinner_index % len(spinner)]} Processing symbols "
                f"{completed_count}/{len(self.symbols)} done | " + " ".join(elapsed_parts)
            )
            spinner_index += 1

            for symbol in done_symbols:
                run = pending.pop(symbol)
                run["stdout_file"].close()
                run["stderr_file"].close()

                exit_code = int(run["exit_code"])
                finished_at = run["finished_at"]
                duration_seconds = round((finished_at - run["started_at"]).total_seconds(), 3)
                completed_count += 1

                if exit_code != 0:
                    self.progress.done()
                    self.failed_symbols.append(symbol)
                    stderr_path = run["stderr_path"]
                    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
                    raise WrapperError(f"Symbol run failed for {symbol} with exit code {exit_code}\n{stderr_text}")

                payload = self._read_json(run["stdout_path"])
                self.run_results.append(
                    self._symbol_result_from_payload(
                        symbol=symbol,
                        experiment_id=run["experiment_id"],
                        payload=payload,
                        stdout_path=run["stdout_path"],
                        stderr_path=run["stderr_path"],
                        started_at=run["started_at"],
                        finished_at=finished_at,
                        duration_seconds=duration_seconds,
                        exit_code=exit_code,
                    )
                )

                self.progress.done()
                self._status(
                    "SYMBOL",
                    f"[{completed_count}/{len(self.symbols)}] {symbol}: completed in {duration_seconds:.1f}s. "
                    f"candidates={payload.get('candidate_count')} accepted={payload.get('accepted_candidate_count')} "
                    f"rejected={payload.get('rejected_candidate_count')} failed={payload.get('failed_candidate_count')}",
                )

            if pending:
                time.sleep(max(0.5, float(self.args.progress_interval_seconds)))

        self.progress.done()
        self._status("SYMBOL", "All symbol runs completed.")

    def _symbol_result_from_payload(
        self,
        *,
        symbol: str,
        experiment_id: str,
        payload: dict[str, Any],
        stdout_path: Path,
        stderr_path: Path,
        started_at: datetime,
        finished_at: datetime,
        duration_seconds: float,
        exit_code: int,
    ) -> SymbolRunResult:
        return SymbolRunResult(
            symbol=symbol,
            mode="fresh_training_runs",
            experiment_id=experiment_id,
            output_dir=self._as_optional_str(payload.get("output_dir")),
            summary_json_path=self._as_optional_str(payload.get("summary_json_path")),
            summary_markdown_path=self._as_optional_str(payload.get("summary_markdown_path")),
            candidate_count=self._as_optional_int(payload.get("candidate_count")),
            accepted_candidate_count=self._as_optional_int(payload.get("accepted_candidate_count")),
            rejected_candidate_count=self._as_optional_int(payload.get("rejected_candidate_count")),
            failed_candidate_count=self._as_optional_int(payload.get("failed_candidate_count")),
            exit_code=exit_code,
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
            duration_seconds=duration_seconds,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )

    def _stage_selected_runs(self) -> None:
        self._status("ARCHIVE", "Staging per-symbol experiment outputs...")

        for run in self.run_results:
            if not run.output_dir:
                self._status("ARCHIVE", f"{run.symbol}: no output_dir in payload; skipping stage copy.")
                continue

            source = Path(run.output_dir)
            if not source.exists():
                self._status("ARCHIVE", f"Warning: symbol output_dir does not exist and was not staged: {source}")
                continue

            destination = self.per_symbol_stage_dir / source.name
            if destination.exists():
                shutil.rmtree(destination)

            shutil.copytree(source, destination)
            self._status("ARCHIVE", f"{run.symbol}: staged {source.name}")

    def _run_multi_symbol_analysis(self) -> dict[str, Any]:
        stdout_path = self.raw_output_dir / "multi-symbol-analysis.stdout.json"
        stderr_path = self.raw_output_dir / "multi-symbol-analysis.stderr.log"

        command = [
            str(self.python_exe),
            "-m",
            "app.cli.commands",
            "multi-symbol-feature-regime-analyze",
            "--experiments-root",
            str(self.per_symbol_stage_dir),
            "--symbols",
            ",".join(self.symbols),
            "--latest-per-symbol",
        ]

        self._status("ANALYZE", "Running multi-symbol feature regime analysis...")

        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                check=False,
            )

        if completed.returncode != 0:
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
            raise WrapperError(f"Multi-symbol analysis failed\n{stderr_text}")

        payload = self._read_json(stdout_path)
        self._status(
            "ANALYZE",
            f"Analysis completed. candidates={payload.get('candidate_count')} "
            f"accepted={payload.get('accepted_candidate_count')} rejected={payload.get('rejected_candidate_count')} "
            f"failed={payload.get('failed_candidate_count')} best={payload.get('best_symbol')}:{payload.get('best_candidate_config_id')}",
        )
        return payload

    def _finalize_archive(self, *, wrapper_completed_end_to_end: bool) -> Path:
        self._status("ARCHIVE", "Finalizing archive manifest and zip...")

        self._copy_if_exists(self.analysis_json_path, self.archive_stage_dir / "multi_symbol_feature_regime_analysis.json")
        self._copy_if_exists(self.analysis_markdown_path, self.archive_stage_dir / "multi_symbol_feature_regime_analysis.md")
        if self.stage_report_path:
            self._copy_if_exists(self.stage_report_path, self.archive_stage_dir / self.stage_report_path.name)
        self._copy_if_exists(self.script_path, self.archive_stage_dir / self.script_path.name)

        manifest = self._build_manifest(wrapper_completed_end_to_end=wrapper_completed_end_to_end)
        self._write_json(self.manifest_path, manifest)

        included_files = self._included_files()
        manifest["included_files"] = included_files
        self._write_json(self.manifest_path, manifest)

        if self.archive_path.exists():
            self.archive_path.unlink()

        with zipfile.ZipFile(self.archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in self.archive_stage_dir.rglob("*"):
                if item.is_file():
                    archive.write(item, item.relative_to(self.archive_stage_dir).as_posix())

        if not self.archive_path.exists():
            raise WrapperError(f"Archive was not created: {self.archive_path}")

        if self.archive_path.stat().st_size <= 0:
            raise WrapperError(f"Archive is empty: {self.archive_path}")

        self._status("ARCHIVE", f"Archive created: {self.archive_path}")
        return self.archive_path

    def _build_manifest(self, *, wrapper_completed_end_to_end: bool) -> dict[str, Any]:
        multi = self.multi_symbol_result or {}
        failed_candidate_count = self._as_optional_int(multi.get("failed_candidate_count"))
        candidate_count = self._as_optional_int(multi.get("candidate_count"))
        accepted_candidate_count = self._as_optional_int(multi.get("accepted_candidate_count"))
        rejected_candidate_count = self._as_optional_int(multi.get("rejected_candidate_count"))

        validation = self._validation_summary(
            wrapper_completed_end_to_end=wrapper_completed_end_to_end,
            candidate_count=candidate_count,
            failed_candidate_count=failed_candidate_count,
            multi=multi,
        )

        return {
            "stage": self.stage_name,
            "stage_context": self.stage_context,
            "branch": self.current_branch,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "feature_version": FEATURE_VERSION,
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols": list(self.symbols),
            "symbols_completed": [run.symbol for run in self.run_results if run.exit_code == 0],
            "failed_symbols": sorted(set(self.failed_symbols)),
            "source_mode": "fresh_training_runs",
            "wrapper_completed_end_to_end": wrapper_completed_end_to_end,
            "manual_archive_assembly_used": False,
            "fresh_grid_archive_created_by_wrapper": True,
            "archive_path": str(self.archive_path),
            "archive_stage_dir": str(self.archive_stage_dir),
            "manifest_path": str(self.manifest_path),
            "script_path": str(self.script_path),
            "stage_report_path": str(self.stage_report_path) if self.stage_report_path else None,
            "analysis_json_path": str(self.analysis_json_path),
            "analysis_markdown_path": str(self.analysis_markdown_path),
            "candidate_count": candidate_count,
            "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
            "accepted_candidate_count": accepted_candidate_count,
            "rejected_candidate_count": rejected_candidate_count,
            "failed_candidate_count": failed_candidate_count,
            "all_gap_training_safe": multi.get("all_gap_training_safe"),
            "effective_gap_count_by_symbol": multi.get("effective_gap_count_by_symbol"),
            "gap_severity_by_symbol": multi.get("gap_severity_by_symbol"),
            "best_symbol": multi.get("best_symbol"),
            "best_candidate_config_id": multi.get("best_candidate_config_id"),
            "best_candidate_score": multi.get("best_candidate_score"),
            "validation": validation,
            "run_results": [asdict(run) for run in self.run_results],
            "multi_symbol_result": self.multi_symbol_result,
            "included_files": [],
        }

    def _validation_summary(
        self,
        *,
        wrapper_completed_end_to_end: bool,
        candidate_count: int | None,
        failed_candidate_count: int | None,
        multi: dict[str, Any],
    ) -> dict[str, Any]:
        expected_count = self._expected_candidate_count()
        candidate_count_ok = candidate_count == expected_count
        failed_candidate_count_ok = failed_candidate_count == 0
        source_mode_ok = True
        manual_archive_assembly_ok = True
        gap_training_safe_ok = multi.get("all_gap_training_safe") is True
        expected_symbols_ok = sorted([run.symbol for run in self.run_results]) == sorted(self.symbols)

        strict_validation_ok = all(
            [
                wrapper_completed_end_to_end,
                candidate_count_ok,
                failed_candidate_count_ok,
                source_mode_ok,
                manual_archive_assembly_ok,
                expected_symbols_ok,
            ]
        )

        return {
            "wrapper_completed_end_to_end_ok": wrapper_completed_end_to_end,
            "source_mode_ok": source_mode_ok,
            "source_mode_expected": "fresh_training_runs",
            "manual_archive_assembly_ok": manual_archive_assembly_ok,
            "manual_archive_assembly_expected": False,
            "candidate_count_ok": candidate_count_ok,
            "candidate_count_expected": expected_count,
            "failed_candidate_count_ok": failed_candidate_count_ok,
            "failed_candidate_count_expected": 0,
            "expected_symbols_ok": expected_symbols_ok,
            "gap_training_safe_ok": gap_training_safe_ok,
            "strict_validation_ok": strict_validation_ok,
        }

    def _expected_candidate_count(self) -> int:
        if self.args.max_configs is not None:
            return int(self.args.max_configs) * len(self.symbols)
        return EXPECTED_CANDIDATE_COUNT

    def _build_final_result(self, *, status: str, wrapper_completed_end_to_end: bool, archive_size_bytes: int) -> dict[str, Any]:
        multi = self.multi_symbol_result or {}
        candidate_count = self._as_optional_int(multi.get("candidate_count"))
        failed_candidate_count = self._as_optional_int(multi.get("failed_candidate_count"))
        validation = self._validation_summary(
            wrapper_completed_end_to_end=wrapper_completed_end_to_end,
            candidate_count=candidate_count,
            failed_candidate_count=failed_candidate_count,
            multi=multi,
        )

        return {
            "status": status,
            "stage": self.stage_name,
            "stage_context": self.stage_context,
            "branch": self.current_branch,
            "source_mode": "fresh_training_runs",
            "wrapper_completed_end_to_end": wrapper_completed_end_to_end,
            "manual_archive_assembly_used": False,
            "fresh_grid_archive_created_by_wrapper": True,
            "archive_path": str(self.archive_path),
            "manifest_path": str(self.manifest_path),
            "archive_size_bytes": archive_size_bytes,
            "symbols": list(self.symbols),
            "symbols_completed": [run.symbol for run in self.run_results],
            "failed_symbols": sorted(set(self.failed_symbols)),
            "candidate_count": candidate_count,
            "accepted_candidate_count": self._as_optional_int(multi.get("accepted_candidate_count")),
            "rejected_candidate_count": self._as_optional_int(multi.get("rejected_candidate_count")),
            "failed_candidate_count": failed_candidate_count,
            "all_gap_training_safe": multi.get("all_gap_training_safe"),
            "best_symbol": multi.get("best_symbol"),
            "best_candidate_config_id": multi.get("best_candidate_config_id"),
            "best_candidate_score": multi.get("best_candidate_score"),
            "validation": validation,
            "experiments": [asdict(run) for run in self.run_results],
            "multi_symbol_result": self.multi_symbol_result,
        }

    def _included_files(self) -> list[str]:
        if not self.archive_stage_dir.exists():
            return []

        return sorted(
            item.relative_to(self.archive_stage_dir).as_posix()
            for item in self.archive_stage_dir.rglob("*")
            if item.is_file()
        )

    def _copy_if_exists(self, source: Path, destination: Path) -> bool:
        if not source.exists():
            self._status("ARCHIVE", f"Optional file not found, skip copy: {source}")
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
            return True

        shutil.copy2(source, destination)
        return True

    def _run_command_capture(self, command: list[str], label: str) -> str:
        self._status("COMMAND", label)
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        output = completed.stdout.strip()
        error = completed.stderr.strip()

        if output:
            self._status("OUTPUT", output)

        if error:
            self._status("STDERR", error)

        if completed.returncode != 0:
            raise WrapperError(f"Command failed: {label}\n{output}\n{error}".strip())

        return completed.stdout

    def _read_json(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            raise WrapperError(f"JSON file is empty: {path}")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < start:
                raise
            payload = json.loads(text[start : end + 1])

        if not isinstance(payload, dict):
            raise WrapperError(f"Expected JSON object in {path}, got {type(payload).__name__}")

        return payload

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _status(self, stage: str, message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] [{stage}] {message}"
        self.progress.done()
        print(line, flush=True)

        if self.stage_initialized:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _as_optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generic fresh FV3 tuning wrapper for traders-ml.",
    )
    parser.add_argument("--repo-root", default=None, help="Path to traders-ml root. Defaults to script directory.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="Comma-separated symbols.")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--stage-name", default=DEFAULT_STAGE_NAME)
    parser.add_argument("--stage-context", default=DEFAULT_STAGE_CONTEXT)
    parser.add_argument("--stage-report-path", default=None, help="Optional stage report file to include in archive.")
    parser.add_argument("--sequential", action="store_true", help="Run symbols sequentially instead of parallel.")
    parser.add_argument("--max-configs", type=int, default=None, help="Optional max configs per symbol for debugging only.")
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to symbol tuning command.")
    parser.add_argument("--sample-mode", action="store_true", help="Pass --sample-mode to symbol tuning command.")
    parser.add_argument("--no-progress", action="store_true", help="Disable live terminal progress indicator.")
    parser.add_argument("--progress-interval-seconds", type=float, default=5.0, help="Progress refresh interval.")
    parser.add_argument(
        "--allow-runtime-dirty",
        action="store_true",
        help="Allow existing runtime artifacts under reports/ during git preflight.",
    )
    parser.add_argument(
        "--no-allow-self-untracked",
        dest="allow_self_untracked",
        action="store_false",
        help="Do not ignore this wrapper file if it is untracked.",
    )
    parser.set_defaults(allow_self_untracked=True)
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Exit with error if final validation flags are not all OK.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    wrapper = FreshFv3TuningWrapper(args)

    try:
        result = wrapper.run()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
