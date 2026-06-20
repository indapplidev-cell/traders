#!/usr/bin/env python
r"""Fresh FV3 tuning with DB candle cache for traders-ml.

File name without stage/version binding:

    run_fv3_cached_tuning.py

Place it in traders-ml root:

    D:\disk_E\game_projects\traders\traders-ml\run_fv3_cached_tuning.py

What it does:

1. Checks that candles for each symbol/interval/date range are already in PostgreSQL.
2. If cache is incomplete, runs existing CLI `load-candles`.
3. Re-checks candle gaps after loading.
4. Runs fresh FV3 tuning from the DB-backed dataset pipeline.
5. Runs multi-symbol analysis.
6. Creates a wrapper-owned archive with:
   - archive_manifest.json
   - fresh_grid_run.log
   - per-symbol experiment outputs
   - raw stdout/stderr logs
   - multi_symbol_feature_regime_analysis.json/md when available

Default range:

    BTCUSDT, ETHUSDT, SOLUSDT
    15m
    2025-01-01 -> 2026-06-15

Recommended first run:

    python run_fv3_cached_tuning.py --ensure-candles-only

Then training run:

    python run_fv3_cached_tuning.py

If you want to rerun without checking/downloading candles:

    python run_fv3_cached_tuning.py --skip-candle-cache

Sequential mode:

    python run_fv3_cached_tuning.py --sequential

START MODULE
    1. python run_fv3_cached_tuning.py --fast-debug
    Ожидание:
        runtime_profile = fast_debug
        wrapper_completed_end_to_end = true
        strict_validation_ok = true
        failed_candidate_count = 0
        selected_config_ids = [
            "lv17_h08_tts_thr060",
            "lv16_h08_trade_two_stage",
        ]
        symbols = ["BTCUSDT", "SOLUSDT"]
        candidate_count = 4
    Этот режим не говорит о качестве модели. Он только проверяет, что pipeline живой
    и что smoke реально покрывает Prompt 4-6.

    2. python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT
    Ожидание:
        runtime_profile = quick_quality
        symbols = ["SOLUSDT"]
        selected_config_ids = [
            "lv17_h08_tts_thr060",
            "lv17_h08_tts_thr065",
            "lv17_h12_tts_thr065",
        ]
        start_date = 2026-04-01
        end_date = 2026-06-15
        candidate_count = 3
        failed_candidate_count = 0
        wrapper_completed_end_to_end = true
        strict_validation_ok = true

        Если result/candidate reports показывают:
            accepted_candidate_count = 0
        тогда полный запуск не делать. Анализировать Schwager board, opportunity diagnostics,
        baseline edge, collapse, separability и class-margin guard.

        Если:
            accepted_candidate_count >= 1
        модель всё равно не активировать автоматически. Сначала прислать архив на анализ.

    3. python run_fv3_cached_tuning.py --single-symbol-full --single-symbol-full-symbol SOLUSDT
        Ожидание:
            runtime_profile = single_symbol_full
            symbols = ["SOLUSDT"]
            start_date = 2025-01-01
            end_date = 2026-06-15
            candidate_count = 3
            failed_candidate_count = 0
            wrapper_completed_end_to_end = true
            strict_validation_ok = true

        Запускать только после отдельного разрешения.

    4. python run_fv3_cached_tuning.py
        Ожидание:
            runtime_profile = full
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            full_quality_run = true
            quality_decision_allowed = true
            failed_candidate_count = 0
            wrapper_completed_end_to_end = true
            strict_validation_ok = true

        Не запускать без отдельного разрешения.
        Даже если появится ACCEPTED, модель не активировать. Сначала прислать архив на анализ.

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


DEFAULT_STAGE_NAME = "FV3_CACHED_FRESH_TUNING"
DEFAULT_STAGE_CONTEXT = "Fresh FV3 tuning using PostgreSQL candle cache"
FEATURE_VERSION = "fv4_book_setup_context"
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2026-06-15"
DEFAULT_INTERVAL = "15m"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_TUNING_COMMAND = "ml38-2-fv3-tuning-run"


def _infer_default_full_grid_config_count() -> int:
    try:
        from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix

        payload = ML382FV3TuningMatrix().build()
        return int(payload.get("config_count") or len(payload.get("configs", [])))
    except Exception:
        return 0


def _infer_default_expected_candidate_count() -> int:
    try:
        from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix

        payload = ML382FV3TuningMatrix().build()
        config_count = int(payload.get("config_count") or len(payload.get("configs", [])))
        return config_count * len(DEFAULT_SYMBOLS)
    except Exception:
        return 0


DEFAULT_FULL_GRID_CONFIG_COUNT = _infer_default_full_grid_config_count()
DEFAULT_EXPECTED_CANDIDATE_COUNT = _infer_default_expected_candidate_count()

# Runtime smoke: Prompt 4-6 plus ML38.10.7 setup-quality filtering coverage, two symbols, short period.
# Covers:
# - ML38.10.7 setup-quality filtered two-stage via lv18_h08_tts_thr065_sq060
# - ML38.10.6 threshold-control comparison via lv17_h12_tts_thr065
# - ML38.10.2 Schwager robustness board through candidate report payloads
FAST_DEBUG_CONFIGS = (
    "lv18_h08_tts_thr065_sq060",
    "lv17_h12_tts_thr065",
)
FAST_DEBUG_SYMBOLS = ("BTCUSDT", "SOLUSDT")
FAST_DEBUG_START_DATE = "2026-05-01"
FAST_DEBUG_END_DATE = DEFAULT_END_DATE

# Intermediate quality: one symbol, short period, Prompt 4-6 smoke shortlist.
# Keep this small: it is not final validation and must not replace full research review.
QUICK_QUALITY_CONFIGS = (
    "lv18_h08_tts_thr065_sq060",
    "lv18_h12_tts_thr065_sq060",
    "lv18_h12_tts_thr070_sq065",
)
QUICK_QUALITY_SYMBOL = "SOLUSDT"
QUICK_QUALITY_START_DATE = "2026-04-01"
QUICK_QUALITY_END_DATE = DEFAULT_END_DATE

# Intermediate heavy check: one symbol, full period, ML38.9.5 shortlist.
SINGLE_SYMBOL_FULL_CONFIGS = (
    "lv10_h08_thr052_tp10_sl10_dp",
    "lv10_h12_thr06_tp12_sl12_dp",
    "lv10_h16_thr065_tp15_sl15_dp",
)
SINGLE_SYMBOL_FULL_SYMBOL = "SOLUSDT"
SINGLE_SYMBOL_FULL_START_DATE = DEFAULT_START_DATE
SINGLE_SYMBOL_FULL_END_DATE = DEFAULT_END_DATE


@dataclass(frozen=True)
class CandleCacheResult:
    symbol: str
    interval: str
    start_date: str
    end_date: str
    cache_complete_before: bool | None
    cache_complete_after: bool | None
    download_performed: bool
    load_exit_code: int | None
    pre_check_json: dict[str, Any] | None
    post_check_json: dict[str, Any] | None
    pre_check_stdout_path: str
    pre_check_stderr_path: str
    post_check_stdout_path: str | None
    post_check_stderr_path: str | None
    load_stdout_path: str | None
    load_stderr_path: str | None
    status: str
    reason: str | None


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
        padding = " " * max(0, self._last_len - len(clean))
        print("\r" + clean + padding, end="", flush=True)
        self._last_len = len(clean)

    def done(self) -> None:
        if not self.enabled:
            return

        print("\r" + " " * self._last_len + "\r", end="", flush=True)
        self._last_len = 0

def _split_csv(value: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(str(part).strip() for part in value if str(part).strip())
    return tuple(part.strip() for part in str(value or "").split(",") if part.strip())


class Fv3CachedTuningWrapper:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parent
        self.python_exe = self._resolve_python_exe()

        self.fast_debug = bool(args.fast_debug)
        self.quick_quality = bool(args.quick_quality)
        self.single_symbol_full = bool(args.single_symbol_full)
        self.runtime_profile = self._runtime_profile()

        if self.fast_debug:
            raw_symbols = args.debug_symbols
            raw_start_date = args.debug_start_date
            raw_end_date = args.debug_end_date
            selected_config_ids = tuple(_split_csv(args.debug_configs))
        elif self.quick_quality:
            raw_symbols = args.quick_quality_symbol
            raw_start_date = args.quick_quality_start_date
            raw_end_date = args.quick_quality_end_date
            selected_config_ids = tuple(_split_csv(args.quick_quality_configs))
        elif self.single_symbol_full:
            raw_symbols = args.single_symbol_full_symbol
            raw_start_date = args.single_symbol_full_start_date
            raw_end_date = args.single_symbol_full_end_date
            selected_config_ids = tuple(_split_csv(args.single_symbol_full_configs))
        else:
            raw_symbols = args.symbols
            raw_start_date = args.start_date
            raw_end_date = args.end_date
            selected_config_ids = ()

        self.symbols = tuple(part.upper() for part in _split_csv(raw_symbols))
        self.debug_config_ids = tuple(_split_csv(args.debug_configs)) if self.fast_debug else ()
        self.quick_quality_config_ids = tuple(_split_csv(args.quick_quality_configs)) if self.quick_quality else ()
        self.single_symbol_full_config_ids = (
            tuple(_split_csv(args.single_symbol_full_configs)) if self.single_symbol_full else ()
        )
        self.selected_config_ids = selected_config_ids
        self.interval = args.interval
        self.start_date = raw_start_date
        self.end_date = raw_end_date
        self.stage_name = args.stage_name
        self.stage_context = self._stage_context(args.stage_context)
        self.tuning_command = args.tuning_command
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.output_root = self.repo_root / "reports" / "feature_regime_experiments"

        symbols_part = "_".join(symbol.lower() for symbol in self.symbols)
        mode_prefix = self._runtime_mode_prefix()
        self.archive_base_name = f"{mode_prefix}fv3_cached_fresh_tuning_{symbols_part}_{self.interval}_{self.timestamp}"
        self.archive_stage_dir = self.output_root / self.archive_base_name
        self.archive_path = self.output_root / f"{self.archive_base_name}.zip"
        self.raw_output_dir = self.archive_stage_dir / "raw_outputs"
        self.per_symbol_stage_dir = self.archive_stage_dir / "per_symbol_experiments"
        self.cache_output_dir = self.archive_stage_dir / "candle_cache"
        self.log_path = self.archive_stage_dir / "fresh_grid_run.log"
        self.manifest_path = self.archive_stage_dir / "archive_manifest.json"
        self.analysis_json_path = self.repo_root / "reports" / "multi_symbol_feature_regime_analysis.json"
        self.analysis_markdown_path = self.repo_root / "reports" / "multi_symbol_feature_regime_analysis.md"
        self.stage_report_path = Path(args.stage_report_path).resolve() if args.stage_report_path else None
        self.script_path = Path(__file__).resolve()
        self.progress = TerminalProgress(enabled=not args.no_progress)

        self.stage_initialized = False
        self.current_branch: str | None = None
        self.candle_cache_results: list[CandleCacheResult] = []
        self.run_results: list[SymbolRunResult] = []
        self.failed_symbols: list[str] = []
        self.multi_symbol_result: dict[str, Any] | None = None

    def run(self) -> dict[str, Any]:
        self._print_banner()
        if self.runtime_profile != "full":
            self._status(
                "PROFILE",
                f"{self.runtime_profile} mode enabled: "
                f"symbols={list(self.symbols)} configs={list(self.selected_config_ids)} "
                f"range={self.start_date}->{self.end_date}. "
                "This is not a final full multi-symbol quality decision.",
            )
        self._preflight()
        self._ensure_stage_dirs()

        try:
            self._run_health_checks()

            if not self.args.skip_candle_cache:
                self._ensure_candle_cache()
            else:
                self._status("CACHE", "Skipping candle cache checks by user request.")

            if self.args.ensure_candles_only:
                self._status("DONE", "Candle cache ensure-only mode completed. Training was not started.")
                archive_item = self._finalize_archive(wrapper_completed_end_to_end=True)
                return self._build_final_result(
                    status="ok",
                    wrapper_completed_end_to_end=True,
                    archive_size_bytes=archive_item.stat().st_size,
                    training_skipped=True,
                )

            run_in_parallel = not self.args.sequential
            self._start_fresh_symbol_runs(run_in_parallel=run_in_parallel)
            self._stage_selected_runs()

            self.multi_symbol_result = self._run_multi_symbol_analysis()
            archive_item = self._finalize_archive(wrapper_completed_end_to_end=True)

            result = self._build_final_result(
                status="ok",
                wrapper_completed_end_to_end=True,
                archive_size_bytes=archive_item.stat().st_size,
                training_skipped=False,
            )

            self._status("DONE", f"Archive path: {self.archive_path}")
            self._status("DONE", f"Archive size bytes: {archive_item.stat().st_size}")

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
        print("=" * 92)
        print("FV3 cached fresh tuning wrapper")
        print(f"Stage name: {self.stage_name}")
        print(f"Context: {self.stage_context}")
        print(f"Runtime profile: {self.runtime_profile}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Interval: {self.interval}")
        print(f"Date range: {self.start_date} -> {self.end_date}")
        print(f"Candle source: PostgreSQL DB cache, with CLI load only when cache is incomplete")
        print(f"Training mode: {'skipped: ensure-candles-only' if self.args.ensure_candles_only else ('sequential' if self.args.sequential else 'parallel')}")
        print("=" * 92)

    def _resolve_python_exe(self) -> Path:
        candidate = self.repo_root / ".venv" / "Scripts" / "python.exe"
        if candidate.exists():
            return candidate
        return Path(sys.executable)

    def _runtime_profile(self) -> str:
        if self.fast_debug:
            return "fast_debug"
        if self.quick_quality:
            return "quick_quality"
        if self.single_symbol_full:
            return "single_symbol_full"
        return "full"

    def _runtime_mode_prefix(self) -> str:
        if self.fast_debug:
            return "fast_debug_"
        if self.quick_quality:
            return "quick_quality_"
        if self.single_symbol_full:
            return "single_symbol_full_"
        return ""

    def _stage_context(self, base_context: str) -> str:
        if self.fast_debug:
            return f"{base_context}; FAST DEBUG runtime-only validation"
        if self.quick_quality:
            return f"{base_context}; QUICK QUALITY single-symbol intermediate validation"
        if self.single_symbol_full:
            return f"{base_context}; SINGLE SYMBOL FULL-PERIOD intermediate validation"
        return base_context

    def _full_quality_run(self) -> bool:
        return self.runtime_profile == "full"

    def _quality_decision_allowed(self) -> bool:
        # Только полный 3-symbol run может считаться финальным quality decision.
        # Fast/quick/single-symbol режимы дают только промежуточный сигнал.
        return self.runtime_profile == "full"

    def _accepted_candidate_count(self) -> int:
        multi = self.multi_symbol_result or {}
        return self._as_optional_int(multi.get("accepted_candidate_count")) or 0

    def _next_recommended_action(self) -> str:
        accepted = self._accepted_candidate_count()

        if self.fast_debug:
            if accepted > 0:
                return "Fast-debug completed; still run quick-quality because fast-debug is runtime-only."
            return "Run quick-quality for one symbol; do not run full multi-symbol validation yet."

        if self.quick_quality:
            if accepted > 0:
                symbol = self.symbols[0] if self.symbols else SINGLE_SYMBOL_FULL_SYMBOL
                return f"Run single-symbol-full for {symbol}; do not auto-activate the model."
            return "Do not run full multi-symbol validation; continue improving labels/features/model."

        if self.single_symbol_full:
            if accepted > 0:
                return "Run full BTCUSDT/ETHUSDT/SOLUSDT validation; do not auto-activate the model."
            return "Do not run full multi-symbol validation; one-symbol full-period did not produce ACCEPTED."

        if accepted > 0:
            return "Full validation found ACCEPTED candidate; review stability/walk-forward/per-symbol consistency manually."
        return "Full validation finished with no ACCEPTED candidates; continue ML38 improvements."

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
        self.cache_output_dir.mkdir(parents=True, exist_ok=True)
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

    def _ensure_candle_cache(self) -> None:
        self._status("CACHE", "Checking PostgreSQL candle cache before training...")

        for index, symbol in enumerate(self.symbols, start=1):
            self._status("CACHE", f"[{index}/{len(self.symbols)}] Checking cache for {symbol} {self.interval}")
            result = self._ensure_symbol_candle_cache(symbol=symbol, index=index)
            self.candle_cache_results.append(result)

            if result.status != "ok":
                message = f"{symbol}: candle cache status={result.status}. reason={result.reason}"
                if self.args.strict_cache:
                    raise WrapperError(message)
                self._status("CACHE", "WARNING: " + message)
            else:
                source = "cache hit" if not result.download_performed else "downloaded/rechecked"
                self._status("CACHE", f"{symbol}: cache OK ({source}).")

        self._write_json(
            self.archive_stage_dir / "candle_cache_summary.json",
            {
                "stage": self.stage_name,
                "symbols": list(self.symbols),
                "interval": self.interval,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "results": [asdict(item) for item in self.candle_cache_results],
            },
        )

    def _ensure_symbol_candle_cache(self, *, symbol: str, index: int) -> CandleCacheResult:
        pre_stdout = self.cache_output_dir / f"{symbol}-pre-check.stdout.json"
        pre_stderr = self.cache_output_dir / f"{symbol}-pre-check.stderr.log"
        pre_json, pre_complete, pre_reason = self._check_candle_gaps(
            symbol=symbol,
            stdout_path=pre_stdout,
            stderr_path=pre_stderr,
            label=f"{symbol} pre-cache gap check",
        )

        if pre_complete is True and not self.args.force_redownload:
            return CandleCacheResult(
                symbol=symbol,
                interval=self.interval,
                start_date=self.start_date,
                end_date=self.end_date,
                cache_complete_before=True,
                cache_complete_after=True,
                download_performed=False,
                load_exit_code=None,
                pre_check_json=pre_json,
                post_check_json=None,
                pre_check_stdout_path=str(pre_stdout),
                pre_check_stderr_path=str(pre_stderr),
                post_check_stdout_path=None,
                post_check_stderr_path=None,
                load_stdout_path=None,
                load_stderr_path=None,
                status="ok",
                reason=pre_reason,
            )

        if pre_complete is None and self.args.no_load_on_unknown_cache:
            return CandleCacheResult(
                symbol=symbol,
                interval=self.interval,
                start_date=self.start_date,
                end_date=self.end_date,
                cache_complete_before=None,
                cache_complete_after=None,
                download_performed=False,
                load_exit_code=None,
                pre_check_json=pre_json,
                post_check_json=None,
                pre_check_stdout_path=str(pre_stdout),
                pre_check_stderr_path=str(pre_stderr),
                post_check_stdout_path=None,
                post_check_stderr_path=None,
                load_stdout_path=None,
                load_stderr_path=None,
                status="unknown",
                reason="Could not infer cache completeness from check-candle-gaps output.",
            )

        load_stdout = self.cache_output_dir / f"{symbol}-load-candles.stdout.log"
        load_stderr = self.cache_output_dir / f"{symbol}-load-candles.stderr.log"
        self._status(
            "CACHE",
            f"[{index}/{len(self.symbols)}] {symbol}: "
            f"cache incomplete/unknown or force_redownload={self.args.force_redownload}. Running load-candles...",
        )
        load_exit_code = self._load_candles(symbol=symbol, stdout_path=load_stdout, stderr_path=load_stderr)

        post_stdout = self.cache_output_dir / f"{symbol}-post-check.stdout.json"
        post_stderr = self.cache_output_dir / f"{symbol}-post-check.stderr.log"
        post_json, post_complete, post_reason = self._check_candle_gaps(
            symbol=symbol,
            stdout_path=post_stdout,
            stderr_path=post_stderr,
            label=f"{symbol} post-load gap check",
        )

        if post_complete is True:
            status = "ok"
        elif post_complete is None:
            status = "unknown"
        else:
            status = "incomplete"

        return CandleCacheResult(
            symbol=symbol,
            interval=self.interval,
            start_date=self.start_date,
            end_date=self.end_date,
            cache_complete_before=pre_complete,
            cache_complete_after=post_complete,
            download_performed=True,
            load_exit_code=load_exit_code,
            pre_check_json=pre_json,
            post_check_json=post_json,
            pre_check_stdout_path=str(pre_stdout),
            pre_check_stderr_path=str(pre_stderr),
            post_check_stdout_path=str(post_stdout),
            post_check_stderr_path=str(post_stderr),
            load_stdout_path=str(load_stdout),
            load_stderr_path=str(load_stderr),
            status=status,
            reason=post_reason,
        )

    def _check_candle_gaps(
        self,
        *,
        symbol: str,
        stdout_path: Path,
        stderr_path: Path,
        label: str,
    ) -> tuple[dict[str, Any] | None, bool | None, str | None]:
        command = [
            str(self.python_exe),
            "-m",
            "app.cli.commands",
            "check-candle-gaps",
            "--symbol",
            symbol,
            "--interval",
            self.interval,
            "--start-date",
            self.start_date,
            "--end-date",
            self.end_date,
        ]

        completed = self._run_to_files(command, stdout_path=stdout_path, stderr_path=stderr_path, label=label)
        if completed.returncode != 0:
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
            raise WrapperError(f"check-candle-gaps failed for {symbol}\n{stderr_text}")

        text = stdout_path.read_text(encoding="utf-8", errors="replace")
        payload = self._json_from_text(text)
        if payload is None:
            return None, None, "check-candle-gaps output is not JSON; cache completeness is unknown."

        complete, reason = self._infer_cache_complete(payload)
        return payload, complete, reason

    def _load_candles(self, *, symbol: str, stdout_path: Path, stderr_path: Path) -> int:
        command = [
            str(self.python_exe),
            "-m",
            "app.cli.commands",
            "load-candles",
            "--symbol",
            symbol,
            "--interval",
            self.interval,
            "--start-date",
            self.start_date,
            "--end-date",
            self.end_date,
        ]

        completed = self._run_to_files(command, stdout_path=stdout_path, stderr_path=stderr_path, label=f"{symbol} load-candles")
        if completed.returncode != 0:
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
            stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
            raise WrapperError(f"load-candles failed for {symbol}\nSTDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}")

        return int(completed.returncode)

    def _infer_cache_complete(self, payload: dict[str, Any]) -> tuple[bool | None, str]:
        """Infer whether PostgreSQL candle cache is complete enough for training.

        ML38.4.1 gap semantics:
        - `gap_count`, `missing_open_times` and `is_valid=false` may include the unfinished
          tail of the current end date.
        - `trailing_incomplete_range_detected=true` is not a cache blocker.
        - Real blockers are internal/real gaps, duplicates, misaligned candles, or empty cache.
        """

        if not isinstance(payload, dict):
            return None, "check-candle-gaps output is not a JSON object."

        unique_open_times = self._first_int(payload, "unique_open_times", "checked")
        if unique_open_times is None or unique_open_times <= 0:
            return False, "no candles found in DB cache."

        duplicate_count = self._first_int(payload, "duplicate_count") or 0
        if duplicate_count > 0:
            return False, f"duplicate_count is {duplicate_count}."

        misaligned_count = self._first_int(payload, "misaligned_count") or 0
        if misaligned_count > 0:
            return False, f"misaligned_count is {misaligned_count}."

        # Prefer the new explicit real-gap fields when available. These fields exclude the
        # trailing incomplete current-day tail and are therefore the source of truth.
        if "real_gap_count" in payload or "real_missing_open_times" in payload:
            real_gap_count = self._first_int(payload, "real_gap_count") or 0
            real_missing_open_times = payload.get("real_missing_open_times") or []

            if real_gap_count > 0:
                return False, f"real_gap_count is {real_gap_count}."

            if isinstance(real_missing_open_times, list) and real_missing_open_times:
                return False, f"real_missing_open_times contains {len(real_missing_open_times)} missing candles."

            if real_missing_open_times and not isinstance(real_missing_open_times, list):
                return False, "real_missing_open_times is present but is not a list."

            trailing_detected = bool(payload.get("trailing_incomplete_range_detected") or False)
            trailing_count = self._first_int(payload, "trailing_incomplete_count") or 0

            if trailing_detected:
                return (
                    True,
                    "real_gap_count=0 and real_missing_open_times=[]; "
                    f"ignored trailing incomplete range: {trailing_count}.",
                )

            return True, "real_gap_count=0 and real_missing_open_times=[]."

        # Compatibility with older gap-check payloads that already expose effective/training-safe
        # gap semantics.
        effective_gap_count = self._first_int(
            payload,
            "effective_gap_count_for_training",
            "effective_gap_count",
            "internal_missing_candle_count",
            "real_missing_candle_count",
            "missing_internal_count",
        )

        safe_flag = self._first_bool(
            payload,
            "dataset_safe_for_training",
            "training_safe",
            "candle_cache_complete",
            "safe_for_training",
        )

        severity = str(
            payload.get("gap_severity_for_training")
            or payload.get("gap_severity")
            or payload.get("status")
            or ""
        ).upper()

        if effective_gap_count == 0 and safe_flag is True:
            return True, "effective gaps are zero and training-safe flag is true."

        if effective_gap_count == 0 and severity in {"OK", "SAFE", "COMPLETE", "NO_GAPS"}:
            return True, f"effective gaps are zero and severity/status is {severity}."

        if effective_gap_count == 0 and safe_flag is None:
            return True, "effective gaps are zero."

        if effective_gap_count is not None and effective_gap_count > 0:
            return False, f"effective/internal gap count is {effective_gap_count}."

        # Legacy fallback: when the CLI has no real/effective semantics, raw gap_count and
        # missing_open_times are treated as blockers.
        legacy_gap_count = self._first_int(payload, "gap_count", "missing_count")
        if legacy_gap_count is not None and legacy_gap_count > 0:
            return False, f"legacy gap_count is {legacy_gap_count}."

        for key in ("internal_missing_open_times", "missing_open_times"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                return False, f"{key} contains {len(value)} missing candles."

        if safe_flag is True:
            return True, "training-safe flag is true."

        if safe_flag is False:
            return False, "training-safe flag is false."

        return None, "Could not infer cache completeness from known fields."

    def _first_int(self, payload: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            if key not in payload:
                continue
            value = payload.get(key)
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    def _first_bool(self, payload: dict[str, Any], *keys: str) -> bool | None:
        for key in keys:
            if key not in payload:
                continue
            value = payload.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "yes", "ok", "safe", "complete"}:
                    return True
                if lowered in {"false", "no", "unsafe", "incomplete"}:
                    return False
        return None

    def _start_fresh_symbol_runs(self, *, run_in_parallel: bool) -> None:
        if run_in_parallel:
            self._start_parallel_symbol_runs()
            return

        for index, symbol in enumerate(self.symbols, start=1):
            self._run_single_symbol(symbol, index=index, total=len(self.symbols))

    def _symbol_command(self, symbol: str, experiment_id: str) -> list[str]:
        command = [
            str(self.python_exe),
            "-m",
            "app.cli.commands",
            self.tuning_command,
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

        if self.tuning_command == DEFAULT_TUNING_COMMAND:
            command.append("--skip-candle-load")

        for config_id in self.selected_config_ids:
            command.extend(["--base-label-config-id", config_id])

        if self.args.max_configs is not None:
            command.extend(["--max-configs", str(self.args.max_configs)])

        if self.args.dry_run:
            command.append("--dry-run")

        if self.args.sample_mode:
            command.append("--sample-mode")

        return command

    def _experiment_id(self, symbol: str) -> str:
        return f"fv3_cached_fresh_tuning_{symbol.lower()}_{self.interval}_{self.timestamp}"

    def _run_single_symbol(self, symbol: str, *, index: int, total: int) -> None:
        experiment_id = self._experiment_id(symbol)
        stdout_path = self.raw_output_dir / f"{symbol}-run.stdout.json"
        stderr_path = self.raw_output_dir / f"{symbol}-run.stderr.log"
        command = self._symbol_command(symbol, experiment_id)

        started_at = datetime.now(timezone.utc)
        self._status("SYMBOL", f"[{index}/{total}] {symbol}: fresh training started. experiment_id={experiment_id}")

        completed = self._run_to_files(command, stdout_path=stdout_path, stderr_path=stderr_path, label=f"{symbol} fresh tuning")
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
                f"{spinner[spinner_index % len(spinner)]} Training symbols "
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
            mode="fresh_training_runs_from_db_cache",
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

        completed = self._run_to_files(command, stdout_path=stdout_path, stderr_path=stderr_path, label="multi-symbol analysis")
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
            "runtime_profile": self.runtime_profile,
            "fast_debug": self.fast_debug,
            "quick_quality": self.quick_quality,
            "single_symbol_full": self.single_symbol_full,
            "debug_config_ids": list(self.debug_config_ids),
            "quick_quality_config_ids": list(self.quick_quality_config_ids),
            "single_symbol_full_config_ids": list(self.single_symbol_full_config_ids),
            "selected_config_ids": list(self.selected_config_ids),
            "full_quality_run": self._full_quality_run(),
            "quality_decision_allowed": self._quality_decision_allowed(),
            "intermediate_quality_run": self.quick_quality or self.single_symbol_full,
            "debug_start_date": self.start_date if self.fast_debug else None,
            "debug_end_date": self.end_date if self.fast_debug else None,
            "debug_date_range_expected_to_limit_builders": self.fast_debug,
            "next_recommended_action": self._next_recommended_action(),
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols": list(self.symbols),
            "symbols_completed": [run.symbol for run in self.run_results if run.exit_code == 0],
            "failed_symbols": sorted(set(self.failed_symbols)),
            "candle_source": "postgresql_db_cache",
            "candle_cache_strategy": "check_db_cache_then_load_missing_or_full_requested_range_then_recheck",
            "candle_cache_results": [asdict(item) for item in self.candle_cache_results],
            "candle_download_performed": any(item.download_performed for item in self.candle_cache_results),
            "candle_download_performed_by_symbol": {
                item.symbol: item.download_performed for item in self.candle_cache_results
            },
            "candle_cache_complete_after_by_symbol": {
                item.symbol: item.cache_complete_after for item in self.candle_cache_results
            },
            "source_mode": "fresh_training_runs_from_db_cache",
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
            "expected_candidate_count": self._expected_candidate_count(),
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
        training_skipped = self.args.ensure_candles_only

        candidate_count_ok = True if training_skipped else candidate_count == expected_count
        failed_candidate_count_ok = True if training_skipped else failed_candidate_count == 0
        source_mode_ok = True
        manual_archive_assembly_ok = True
        expected_symbols_ok = True if training_skipped else sorted([run.symbol for run in self.run_results]) == sorted(self.symbols)

        cache_known_results = [item for item in self.candle_cache_results if item.cache_complete_after is not None]
        cache_complete_ok = (
            True
            if self.args.skip_candle_cache
            else bool(cache_known_results) and all(item.cache_complete_after is True for item in cache_known_results)
        )

        gap_training_safe_ok = True if training_skipped else multi.get("all_gap_training_safe") is True

        strict_validation_ok = all(
            [
                wrapper_completed_end_to_end,
                candidate_count_ok,
                failed_candidate_count_ok,
                source_mode_ok,
                manual_archive_assembly_ok,
                expected_symbols_ok,
                cache_complete_ok,
                gap_training_safe_ok,
            ]
        )

        return {
            "wrapper_completed_end_to_end_ok": wrapper_completed_end_to_end,
            "source_mode_ok": source_mode_ok,
            "source_mode_expected": "fresh_training_runs_from_db_cache",
            "manual_archive_assembly_ok": manual_archive_assembly_ok,
            "manual_archive_assembly_expected": False,
            "candidate_count_ok": candidate_count_ok,
            "candidate_count_expected": expected_count,
            "failed_candidate_count_ok": failed_candidate_count_ok,
            "failed_candidate_count_expected": 0,
            "expected_symbols_ok": expected_symbols_ok,
            "cache_complete_ok": cache_complete_ok,
            "gap_training_safe_ok": gap_training_safe_ok,
            "strict_validation_ok": strict_validation_ok,
        }

    def _expected_candidate_count(self) -> int:
        if self.selected_config_ids:
            return len(self.symbols) * len(self.selected_config_ids)
        if self.args.max_configs is not None:
            return int(self.args.max_configs) * len(self.symbols)
        return DEFAULT_EXPECTED_CANDIDATE_COUNT

    def _build_final_result(
        self,
        *,
        status: str,
        wrapper_completed_end_to_end: bool,
        archive_size_bytes: int,
        training_skipped: bool,
    ) -> dict[str, Any]:
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
            "runtime_profile": self.runtime_profile,
            "fast_debug": self.fast_debug,
            "quick_quality": self.quick_quality,
            "single_symbol_full": self.single_symbol_full,
            "debug_config_ids": list(self.debug_config_ids),
            "quick_quality_config_ids": list(self.quick_quality_config_ids),
            "single_symbol_full_config_ids": list(self.single_symbol_full_config_ids),
            "selected_config_ids": list(self.selected_config_ids),
            "full_quality_run": self._full_quality_run(),
            "quality_decision_allowed": self._quality_decision_allowed(),
            "intermediate_quality_run": self.quick_quality or self.single_symbol_full,
            "debug_start_date": self.start_date if self.fast_debug else None,
            "debug_end_date": self.end_date if self.fast_debug else None,
            "debug_date_range_expected_to_limit_builders": self.fast_debug,
            "next_recommended_action": self._next_recommended_action(),
            "branch": self.current_branch,
            "training_skipped": training_skipped,
            "candle_source": "postgresql_db_cache",
            "candle_cache_strategy": "check_db_cache_then_load_missing_or_full_requested_range_then_recheck",
            "candle_download_performed": any(item.download_performed for item in self.candle_cache_results),
            "candle_cache_results": [asdict(item) for item in self.candle_cache_results],
            "source_mode": "fresh_training_runs_from_db_cache",
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

    def _run_to_files(self, command: list[str], *, stdout_path: Path, stderr_path: Path, label: str) -> subprocess.CompletedProcess[str]:
        self._status("COMMAND", label)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)

        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            return subprocess.run(
                command,
                cwd=self.repo_root,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                check=False,
            )

    def _read_json(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            raise WrapperError(f"JSON file is empty: {path}")

        payload = self._json_from_text(text)
        if payload is None:
            raise WrapperError(f"Expected JSON object in {path}")

        return payload

    def _json_from_text(self, text: str) -> dict[str, Any] | None:
        text = text.strip()
        if not text:
            return None

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < start:
                return None
            try:
                payload = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None

        if not isinstance(payload, dict):
            return None

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
        description="Fresh FV3 tuning using PostgreSQL candle cache.",
    )
    parser.add_argument("--repo-root", default=None, help="Path to traders-ml root. Defaults to script directory.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="Comma-separated symbols.")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--stage-name", default=DEFAULT_STAGE_NAME)
    parser.add_argument("--stage-context", default=DEFAULT_STAGE_CONTEXT)
    parser.add_argument("--stage-report-path", default=None, help="Optional stage report file to include in archive.")
    parser.add_argument("--tuning-command", default=DEFAULT_TUNING_COMMAND, help="Existing CLI command for one-symbol FV3 tuning.")
    parser.add_argument("--ensure-candles-only", action="store_true", help="Only check/load candles and create archive; do not train.")
    parser.add_argument("--skip-candle-cache", action="store_true", help="Do not check or load candles before training.")
    parser.add_argument("--strict-cache", action="store_true", help="Fail if post-load candle cache status is incomplete or unknown.")
    parser.add_argument("--force-redownload", action="store_true", default=False, help="Run load-candles even if cache check says data is complete.")
    parser.add_argument("--no-load-on-unknown-cache", action="store_true", help="Do not run load-candles when check-candle-gaps output is unknown.")
    parser.add_argument("--sequential", action="store_true", help="Run symbols sequentially instead of parallel.")
    parser.add_argument("--max-configs", type=int, default=None, help="Optional max configs per symbol for debugging only.")
    profile_group = parser.add_mutually_exclusive_group()
    profile_group.add_argument(
        "--fast-debug",
        action="store_true",
        help="Run a short runtime-only debug pass: BTCUSDT/SOLUSDT and one config by default.",
    )
    profile_group.add_argument(
        "--quick-quality",
        action="store_true",
        help="Run one-symbol short-range intermediate quality validation. Not a final approval.",
    )
    profile_group.add_argument(
        "--single-symbol-full",
        action="store_true",
        help="Run one-symbol full-period intermediate validation. Use only after quick-quality improves.",
    )
    parser.add_argument(
        "--debug-symbols",
        default=FAST_DEBUG_SYMBOLS,
        help="Comma-separated symbols used only when --fast-debug is set.",
    )
    parser.add_argument(
        "--debug-configs",
        default=FAST_DEBUG_CONFIGS,
        help="Comma-separated label config ids used only when --fast-debug is set.",
    )
    parser.add_argument(
        "--debug-start-date",
        default=FAST_DEBUG_START_DATE,
        help="Start date used only when --fast-debug is set.",
    )
    parser.add_argument(
        "--debug-end-date",
        default=FAST_DEBUG_END_DATE,
        help="End date used only when --fast-debug is set.",
    )
    parser.add_argument(
        "--quick-quality-symbol",
        "--symbol",
        default=QUICK_QUALITY_SYMBOL,
        help="Symbol used only when --quick-quality is set.",
    )
    parser.add_argument(
        "--quick-quality-configs",
        default=QUICK_QUALITY_CONFIGS,
        help="Comma-separated label config ids used only when --quick-quality is set.",
    )
    parser.add_argument(
        "--quick-quality-start-date",
        default=QUICK_QUALITY_START_DATE,
        help="Start date used only when --quick-quality is set.",
    )
    parser.add_argument(
        "--quick-quality-end-date",
        default=QUICK_QUALITY_END_DATE,
        help="End date used only when --quick-quality is set.",
    )
    parser.add_argument(
        "--single-symbol-full-symbol",
        default=SINGLE_SYMBOL_FULL_SYMBOL,
        help="Symbol used only when --single-symbol-full is set.",
    )
    parser.add_argument(
        "--single-symbol-full-configs",
        default=SINGLE_SYMBOL_FULL_CONFIGS,
        help="Comma-separated label config ids used only when --single-symbol-full is set.",
    )
    parser.add_argument(
        "--single-symbol-full-start-date",
        default=SINGLE_SYMBOL_FULL_START_DATE,
        help="Start date used only when --single-symbol-full is set.",
    )
    parser.add_argument(
        "--single-symbol-full-end-date",
        default=SINGLE_SYMBOL_FULL_END_DATE,
        help="End date used only when --single-symbol-full is set.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to symbol tuning command.")
    parser.add_argument("--sample-mode", action="store_true", help="Pass --sample-mode to symbol tuning command.")
    parser.add_argument("--no-progress", action="store_true", help="Disable live terminal progress indicator.")
    parser.add_argument("--progress-interval-seconds", type=float, default=5.0, help="Progress refresh interval.")
    parser.add_argument(
        "--allow-runtime-dirty",
        action="store_true",
        default=True,
        help="Allow existing runtime artifacts under reports/ during git preflight. Enabled by default.",
    )
    parser.add_argument(
        "--no-allow-runtime-dirty",
        dest="allow_runtime_dirty",
        action="store_false",
        help="Do not ignore runtime artifacts under reports/ during git preflight.",
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
    wrapper = Fv3CachedTuningWrapper(args)

    try:
        result = wrapper.run()
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
