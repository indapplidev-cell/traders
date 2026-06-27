from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


COMPACT_REPORT_PROFILE = "compact"
STANDARD_REPORT_PROFILE = "standard"
DEBUG_REPORT_PROFILE = "debug"
REPORT_PROFILES = (
    COMPACT_REPORT_PROFILE,
    STANDARD_REPORT_PROFILE,
    DEBUG_REPORT_PROFILE,
)

HEAVY_KEY_PATTERNS = (
    "raw_predictions",
    "predictions",
    "prediction_rows",
    "rows",
    "dataset_rows_payload",
    "raw_feature_values",
    "feature_rows",
    "label_rows",
    "tensors",
    "train_features",
    "validation_features",
    "test_features",
    "per_row",
    "per_candle",
    "debug_rows",
    "candidate_board_rows",
    "best_failed_total_r_by_fold",
    "best_failed_gate_candidates",
    "gate_probes",
    "passed_gates",
    "fold_snapshots",
    "low_signal_folds",
    "directional_side_recovery_rows",
    "validation_candidate_rows",
    "validation_gate_candidates",
    "full_candidate_payload",
    "full_payload",
    "runtime_payload",
    "raw_stdout",
    "raw_stderr",
)

ALWAYS_KEEP_KEYS = (
    "run_id",
    "status",
    "symbol",
    "interval",
    "config_id",
    "model_version",
    "training_run_id",
    "score",
    "final_research_decision",
    "primary_failure",
    "failed_gates",
    "quality_status",
    "profit_factor",
    "total_r",
    "profit_total_r",
    "walk_forward_profit_factor",
    "walk_forward_total_r",
    "opportunity_precision",
    "opportunity_recall",
    "opportunity_f1",
    "opportunity_false_positive_rate",
    "predicted_trade_rate",
    "actual_trade_rate",
    "predicted_to_actual_trade_rate_ratio",
    "two_stage_quality_gate",
    "anti_undertrading_gate",
    "profit_exit_root_cause_audit",
    "walk_forward_profit_exit_root_cause_summary",
    "entry_path_quality_filter_enabled",
    "entry_path_quality_min_threshold",
    "stop_pressure_max_risk_score",
    "entry_path_quality_masked_row_count",
    "entry_path_quality_forced_no_trade_count",
    "entry_path_quality_mask_trade_prediction_removed_count",
    "entry_path_quality_mask_false_positive_removed_count",
    "entry_path_quality_filter_summary",
    "entry_path_quality_filter_diagnostics",
    "entry_path_prediction_filter_summary",
    "stop_pressure_effectiveness_audit",
    "entry_path_final_signal_original_count",
    "entry_path_final_signal_filtered_count",
    "entry_path_final_signal_blocked_count",
    "entry_path_stream_consistency_ok",
    "entry_path_audit_by_symbol",
    "trap_invalidation_feature_impact_audit",
    "schwager_robustness_decision_board",
    "collapse_diagnostics_v2",
)

MODEL_ARTIFACT_SUFFIXES = (
    ".pt",
    ".pth",
    ".onnx",
    ".ckpt",
)

HEAVY_FILE_PATTERNS = (
    "raw_predictions",
    "prediction_rows",
    "raw_feature_values",
    "debug_rows",
    "per_row",
    "per_candle",
    "tensors",
    "full_payload",
    "full_candidate_payload",
    "runtime_payload",
    "raw_stdout",
    "raw_stderr",
)

# ML38.10.13.2: strict compact pruning.
# These files are useful for deep runtime debugging, but they dominate ZIP size.
# Compact archives must keep decision summaries, not raw process streams.
STRICT_COMPACT_ARCHIVE_PATTERNS = (
    "raw_outputs/*.stdout.json",
    "raw_outputs/*-run.stdout.json",
    "raw_outputs/*-analysis.stdout.json",
    "raw_outputs/*.stderr.log",
    "raw_outputs/*-run.stderr.log",
    "raw_outputs/*-analysis.stderr.log",
    "*/raw_outputs/*.stdout.json",
    "*/raw_outputs/*-run.stdout.json",
    "*/raw_outputs/*-analysis.stdout.json",
    "*/raw_outputs/*.stderr.log",
    "*/raw_outputs/*-run.stderr.log",
    "*/raw_outputs/*-analysis.stderr.log",
    "*/training_pipeline.log",
    "*/training_pipeline_events.jsonl",
    "*/label_grid_experiment.log",
    "*/label_grid_experiment_events.jsonl",
    "*/feature_regime_experiment.log",
    "*/feature_regime_experiment_events.jsonl",
    "*.full.json",
    "*full_payload*.json",
    "*runtime_payload*.json",
    "*prediction_rows*.json",
    "*raw_predictions*.json",
)

STRICT_COMPACT_EXCLUSION_REASON = "strict_compact_runtime_stream"

EXCLUDED_ARCHIVE_PATH_PARTS = (
    "artifacts/models/",
    "/artifacts/models/",
    "artifacts/",
    "/artifacts/",
    "models/",
    "/models/",
    "model_artifacts/",
    "/model_artifacts/",
    "__pycache__/",
    "/__pycache__/",
    ".pytest_cache/",
    "/.pytest_cache/",
)

EXCLUDED_ARCHIVE_SUFFIXES = (
    ".pt",
    ".pth",
    ".onnx",
    ".ckpt",
    ".pkl",
    ".pickle",
    ".joblib",
    ".npy",
    ".npz",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".pyc",
    ".pyo",
)

COMPACT_JSON_MAX_LIST_ITEMS = 50
COMPACT_JSON_MAX_STRING_CHARS = 5000
STANDARD_JSON_MAX_LIST_ITEMS = 200
STANDARD_JSON_MAX_STRING_CHARS = 20000


class CompactReportBuilder:
    """Build lightweight JSON-safe payloads for runtime/training reports.

    The compact profile is designed for `--fast-debug` and `--quick-quality`
    runtime archives: keep decision-critical summaries, but omit/truncate raw
    rows, raw predictions, tensors and other large diagnostic payloads.
    """

    def __init__(
        self,
        *,
        heavy_key_patterns: tuple[str, ...] = HEAVY_KEY_PATTERNS,
        always_keep_keys: tuple[str, ...] = ALWAYS_KEEP_KEYS,
    ) -> None:
        self.heavy_key_patterns = tuple(pattern.lower() for pattern in heavy_key_patterns)
        self.always_keep_keys = frozenset(always_keep_keys)

    def compact_payload(
        self,
        payload: Any,
        *,
        profile: str = COMPACT_REPORT_PROFILE,
        max_list_items: int = 50,
        max_string_chars: int = 5000,
    ) -> Any:
        """Return a compact, JSON-safe copy of `payload`.

        `debug` keeps data shape almost unchanged, but still normalizes values to
        JSON-safe primitives. `standard` truncates very large lists/strings but
        does not omit heavy keys. `compact` omits heavy nested payloads and
        truncates long lists/strings.
        """

        normalized_profile = self._normalize_profile(profile)
        return self._compact_value(
            payload,
            key=None,
            profile=normalized_profile,
            max_list_items=max_list_items,
            max_string_chars=max_string_chars,
        )

    def _compact_value(
        self,
        value: Any,
        *,
        key: str | None,
        profile: str,
        max_list_items: int,
        max_string_chars: int,
    ) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            value = asdict(value)

        if isinstance(value, Path):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, tuple):
            value = list(value)
        if isinstance(value, set):
            value = sorted(value, key=lambda item: str(item))

        if isinstance(value, dict):
            return self._compact_dict(
                value,
                key=key,
                profile=profile,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
            )
        if isinstance(value, list):
            return self._compact_list(
                value,
                key=key,
                profile=profile,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
            )
        if isinstance(value, str):
            return self._compact_string(
                value,
                profile=profile,
                max_string_chars=max_string_chars,
            )
        if isinstance(value, (int, float, bool)) or value is None:
            return value

        return str(value)

    def _compact_dict(
        self,
        payload: dict[Any, Any],
        *,
        key: str | None,
        profile: str,
        max_list_items: int,
        max_string_chars: int,
    ) -> dict[str, Any]:
        if self._should_omit_heavy_value(
            key=key,
            value=payload,
            profile=profile,
        ):
            return self._omitted_marker(payload)

        compact: dict[str, Any] = {}
        for raw_key, raw_value in payload.items():
            child_key = str(raw_key)
            if self._should_omit_heavy_value(
                key=child_key,
                value=raw_value,
                profile=profile,
            ):
                compact[child_key] = self._omitted_marker(raw_value)
                continue
            compact[child_key] = self._compact_value(
                raw_value,
                key=child_key,
                profile=profile,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
            )
        return compact

    def _compact_list(
        self,
        payload: list[Any],
        *,
        key: str | None,
        profile: str,
        max_list_items: int,
        max_string_chars: int,
    ) -> list[Any] | dict[str, Any]:
        if self._should_omit_heavy_value(
            key=key,
            value=payload,
            profile=profile,
        ):
            return self._omitted_marker(payload)

        if profile == DEBUG_REPORT_PROFILE:
            kept_items = payload
            truncated = False
        else:
            kept_items = payload[:max_list_items]
            truncated = len(payload) > max_list_items

        compact_items = [
            self._compact_value(
                item,
                key=key,
                profile=profile,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
            )
            for item in kept_items
        ]
        if truncated:
            compact_items.append(
                {
                    "truncated": True,
                    "reason": "compact_report_profile_list_limit",
                    "original_count": len(payload),
                    "kept_count": max_list_items,
                }
            )
        return compact_items

    def _compact_string(
        self,
        payload: str,
        *,
        profile: str,
        max_string_chars: int,
    ) -> str:
        if profile == DEBUG_REPORT_PROFILE or len(payload) <= max_string_chars:
            return payload
        return payload[:max_string_chars] + "...[truncated by compact report]"

    def _should_omit_heavy_value(
        self,
        *,
        key: str | None,
        value: Any,
        profile: str,
    ) -> bool:
        if profile != COMPACT_REPORT_PROFILE:
            return False
        if not key or key in self.always_keep_keys:
            return False
        if not self._is_heavy_key(key):
            return False
        return isinstance(value, (dict, list, tuple, set, str))

    def _is_heavy_key(self, key: str) -> bool:
        normalized = key.lower()
        return any(pattern in normalized for pattern in self.heavy_key_patterns)

    @staticmethod
    def _normalize_profile(profile: str) -> str:
        normalized = str(profile or COMPACT_REPORT_PROFILE).strip().lower()
        if normalized not in REPORT_PROFILES:
            raise ValueError(
                f"unknown report profile: {profile!r}; expected one of {REPORT_PROFILES}"
            )
        return normalized

    @staticmethod
    def _omitted_marker(value: Any) -> dict[str, Any]:
        return {
            "omitted": True,
            "reason": "compact_report_profile_heavy_payload",
            "original_type": CompactReportBuilder._json_type_name(value),
            "original_count": CompactReportBuilder._safe_count(value),
        }

    @staticmethod
    def _json_type_name(value: Any) -> str:
        if isinstance(value, dict):
            return "dict"
        if isinstance(value, list):
            return "list"
        if isinstance(value, tuple):
            return "tuple"
        if isinstance(value, set):
            return "set"
        if isinstance(value, str):
            return "str"
        if value is None:
            return "null"
        return type(value).__name__

    @staticmethod
    def _safe_count(value: Any) -> int | None:
        if isinstance(value, (dict, list, tuple, set, str)):
            return len(value)
        return None


def build_compact_summary(
    payload: dict[str, Any],
    *,
    profile: str = COMPACT_REPORT_PROFILE,
) -> dict[str, Any]:
    """Build a compact report payload with small metadata header."""

    compact = CompactReportBuilder().compact_payload(payload, profile=profile)
    if not isinstance(compact, dict):
        return {
            "report_profile": profile,
            "compact_report_created_at_utc": _utc_now_iso(),
            "payload": compact,
        }
    compact.setdefault("report_profile", profile)
    compact.setdefault("compact_report_created_at_utc", _utc_now_iso())
    if profile in {COMPACT_REPORT_PROFILE, STANDARD_REPORT_PROFILE}:
        compact.setdefault("heavy_payloads_included", False)
    return compact


def build_archive_manifest(
    root_dir: Path,
    *,
    report_profile: str,
    excluded_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Build a size manifest for files that will be included in report ZIP.

    Before ML38.10.13.2 this manifest counted every file in the stage directory.
    That was misleading for compact archives because the ZIP writer skips excluded
    files. Now `file_count` and `total_size_*` describe included files, while
    `stage_*` and `pruned_*` describe what was left out.
    """

    root = Path(root_dir)
    normalized_profile = CompactReportBuilder._normalize_profile(report_profile)

    included_entries: list[dict[str, Any]] = []
    pruned_entries: list[dict[str, Any]] = []
    model_artifacts_included = False
    model_artifacts_present_in_stage = False
    heavy_payload_files_included = False
    pruned_reason_counts: dict[str, int] = {}
    strict_compact_pruned_stdout_json_count = 0
    strict_compact_pruned_log_file_count = 0
    strict_compact_pruned_events_file_count = 0

    if root.exists():
        for path in root.rglob("*"):
            if not path.is_file():
                continue

            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0

            relative_path = _safe_relative_path(path, root)
            normalized_relative_path = _normalize_path(relative_path)
            suffix = path.suffix.lower()
            exclusion_reason = report_file_exclusion_reason(
                path,
                archive_root=root,
                report_profile=normalized_profile,
            )
            entry = {
                "path": relative_path,
                "size_bytes": int(size_bytes),
                "size_mb": _bytes_to_mb(size_bytes),
            }

            if _is_model_artifact_path(normalized_relative_path, suffix=suffix):
                model_artifacts_present_in_stage = True

            if exclusion_reason is None:
                if _is_model_artifact_path(normalized_relative_path, suffix=suffix):
                    model_artifacts_included = True
                if _is_heavy_payload_path(normalized_relative_path):
                    heavy_payload_files_included = True
                included_entries.append(entry)
                continue

            entry["excluded_reason"] = exclusion_reason
            pruned_entries.append(entry)
            pruned_reason_counts[exclusion_reason] = pruned_reason_counts.get(exclusion_reason, 0) + 1

            if exclusion_reason == STRICT_COMPACT_EXCLUSION_REASON:
                if normalized_relative_path.endswith(".stdout.json"):
                    strict_compact_pruned_stdout_json_count += 1
                elif normalized_relative_path.endswith(".events.jsonl") or normalized_relative_path.endswith("_events.jsonl"):
                    strict_compact_pruned_events_file_count += 1
                elif normalized_relative_path.endswith(".log"):
                    strict_compact_pruned_log_file_count += 1

    included_total_size_bytes = sum(int(item["size_bytes"]) for item in included_entries)
    pruned_total_size_bytes = sum(int(item["size_bytes"]) for item in pruned_entries)
    stage_total_size_bytes = included_total_size_bytes + pruned_total_size_bytes

    largest_files = sorted(
        included_entries,
        key=lambda item: int(item["size_bytes"]),
        reverse=True,
    )[:20]
    largest_pruned_files = sorted(
        pruned_entries,
        key=lambda item: int(item["size_bytes"]),
        reverse=True,
    )[:20]

    if normalized_profile in {COMPACT_REPORT_PROFILE, STANDARD_REPORT_PROFILE}:
        heavy_payloads_included = False
    else:
        heavy_payloads_included = heavy_payload_files_included

    strict_compact_pruned_entries = [
        item for item in pruned_entries if item.get("excluded_reason") == STRICT_COMPACT_EXCLUSION_REASON
    ]
    strict_compact_pruned_size_bytes = sum(
        int(item["size_bytes"]) for item in strict_compact_pruned_entries
    )

    return {
        "report_profile": normalized_profile,
        "created_at_utc": _utc_now_iso(),
        "root_dir": str(root),
        "file_count": len(included_entries),
        "total_size_bytes": int(included_total_size_bytes),
        "total_size_mb": _bytes_to_mb(included_total_size_bytes),
        "stage_file_count": len(included_entries) + len(pruned_entries),
        "stage_total_size_bytes": int(stage_total_size_bytes),
        "stage_total_size_mb": _bytes_to_mb(stage_total_size_bytes),
        "pruned_file_count": len(pruned_entries),
        "pruned_total_size_bytes": int(pruned_total_size_bytes),
        "pruned_total_size_mb": _bytes_to_mb(pruned_total_size_bytes),
        "pruned_reason_counts": pruned_reason_counts,
        "strict_compact_pruned_file_count": len(strict_compact_pruned_entries),
        "strict_compact_pruned_size_bytes": int(strict_compact_pruned_size_bytes),
        "strict_compact_pruned_size_mb": _bytes_to_mb(strict_compact_pruned_size_bytes),
        "strict_compact_pruned_stdout_json_count": strict_compact_pruned_stdout_json_count,
        "strict_compact_pruned_log_file_count": strict_compact_pruned_log_file_count,
        "strict_compact_pruned_events_file_count": strict_compact_pruned_events_file_count,
        "largest_files": largest_files,
        "largest_pruned_files": largest_pruned_files,
        "heavy_payloads_included": bool(heavy_payloads_included),
        "model_artifacts_included": bool(model_artifacts_included),
        "model_artifacts_present_in_stage": bool(model_artifacts_present_in_stage),
        "excluded_paths": list(excluded_paths or []),
    }


def _safe_relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").lower().lstrip("./")


def _is_model_artifact_path(normalized_relative_path: str, *, suffix: str) -> bool:
    return (
        normalized_relative_path.startswith("artifacts/models/")
        or "/artifacts/models/" in normalized_relative_path
        or suffix in MODEL_ARTIFACT_SUFFIXES
    )


def _is_heavy_payload_path(normalized_relative_path: str) -> bool:
    return any(pattern in normalized_relative_path for pattern in HEAVY_FILE_PATTERNS)


def _is_strict_compact_pruned_path(normalized_relative_path: str) -> bool:
    return any(
        fnmatch(normalized_relative_path, pattern)
        for pattern in STRICT_COMPACT_ARCHIVE_PATTERNS
    )


def _bytes_to_mb(size_bytes: int | float) -> float:
    return round(float(size_bytes) / (1024.0 * 1024.0), 6)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")

def report_file_exclusion_reason(
    path: Path,
    *,
    archive_root: Path,
    report_profile: str = COMPACT_REPORT_PROFILE,
) -> str | None:
    """Return exclusion reason for report archive file, or None if included."""

    normalized_profile = CompactReportBuilder._normalize_profile(report_profile)
    relative_path = _normalize_path(_safe_relative_path(Path(path), Path(archive_root)))
    suffix = Path(path).suffix.lower()

    if suffix in EXCLUDED_ARCHIVE_SUFFIXES:
        return "excluded_suffix"

    if any(part in relative_path for part in EXCLUDED_ARCHIVE_PATH_PARTS):
        return "excluded_path_part"

    if _is_model_artifact_path(relative_path, suffix=suffix):
        return "model_artifact"

    if normalized_profile == COMPACT_REPORT_PROFILE:
        if _is_strict_compact_pruned_path(relative_path):
            return STRICT_COMPACT_EXCLUSION_REASON

    if normalized_profile in {COMPACT_REPORT_PROFILE, STANDARD_REPORT_PROFILE}:
        if _is_heavy_payload_path(relative_path):
            return "heavy_payload_path"

    return None


def should_include_report_file(
    path: Path,
    *,
    archive_root: Path,
    report_profile: str = COMPACT_REPORT_PROFILE,
) -> bool:
    """Return False for files that must not be included in report archives.

    Even `debug` profile must not include model binaries or Python cache files.
    Compact additionally skips runtime stdout/log/event streams.
    Compact/standard additionally skip known heavy raw payload files.
    """

    return report_file_exclusion_reason(
        path,
        archive_root=archive_root,
        report_profile=report_profile,
    ) is None


def compact_json_file(
    source: Path,
    destination: Path,
    *,
    report_profile: str = COMPACT_REPORT_PROFILE,
) -> bool:
    """Copy JSON as compact JSON when possible.

    Safe for source != destination and also safe for in-place compaction when
    caller passes a temp destination and replaces the original after success.
    """

    source = Path(source)
    destination = Path(destination)
    if not source.exists() or not source.is_file():
        return False

    try:
        payload = json.loads(source.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return False

    normalized_profile = CompactReportBuilder._normalize_profile(report_profile)
    if normalized_profile == COMPACT_REPORT_PROFILE:
        max_list_items = COMPACT_JSON_MAX_LIST_ITEMS
        max_string_chars = COMPACT_JSON_MAX_STRING_CHARS
    elif normalized_profile == STANDARD_REPORT_PROFILE:
        max_list_items = STANDARD_JSON_MAX_LIST_ITEMS
        max_string_chars = STANDARD_JSON_MAX_STRING_CHARS
    else:
        max_list_items = 1_000_000
        max_string_chars = 50_000_000

    compact_payload = CompactReportBuilder().compact_payload(
        payload,
        profile=normalized_profile,
        max_list_items=max_list_items,
        max_string_chars=max_string_chars,
    )
    if isinstance(compact_payload, dict):
        compact_payload.setdefault("report_profile", normalized_profile)
        compact_payload.setdefault("compact_report_created_at_utc", _utc_now_iso())
        if normalized_profile == COMPACT_REPORT_PROFILE:
            compact_payload.setdefault("summary_payload_mode", "compact_capped_runtime_archive_ml38_10_26_2")
            compact_payload.setdefault("summary_payload_compacted", True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(compact_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return True


def copy_report_file(
    source: Path,
    destination: Path,
    *,
    archive_root: Path,
    report_profile: str = COMPACT_REPORT_PROFILE,
) -> bool:
    """Copy one report file into archive stage directory safely.

    JSON files are compacted for compact/standard profiles. Model artifacts and
    heavy raw payloads are refused by should_include_report_file.
    """

    source = Path(source)
    destination = Path(destination)
    if not source.exists() or not source.is_file():
        return False

    if not should_include_report_file(
        destination,
        archive_root=archive_root,
        report_profile=report_profile,
    ):
        return False

    if source.suffix.lower() == ".json" and report_profile != DEBUG_REPORT_PROFILE:
        if compact_json_file(source, destination, report_profile=report_profile):
            return True

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def prune_and_compact_report_tree(
    directory: Path,
    *,
    archive_root: Path,
    report_profile: str = COMPACT_REPORT_PROFILE,
) -> dict[str, Any]:
    """Prune and compact a report tree in place.

    Used by wrapper when per-symbol output is already written inside the final
    archive stage directory. In that self-copy case we must not delete the whole
    directory, but we still must apply the same compact archive rules that the
    normal copy path applies.
    """

    root = Path(directory)
    archive_root = Path(archive_root)

    before_files = 0
    before_size = 0
    after_files = 0
    after_size = 0
    pruned_files = 0
    pruned_size = 0
    compacted_json_files = 0
    compacted_json_before_size = 0
    compacted_json_after_size = 0
    kept_files = 0
    errors: list[dict[str, Any]] = []
    pruned_reason_counts: dict[str, int] = {}

    if not root.exists():
        return {
            "directory": str(root),
            "exists": False,
            "before_files": 0,
            "before_size_bytes": 0,
            "after_files": 0,
            "after_size_bytes": 0,
            "pruned_files": 0,
            "pruned_size_bytes": 0,
            "compacted_json_files": 0,
            "errors": [],
        }

    files = [path for path in root.rglob("*") if path.is_file()]
    before_files = len(files)
    for path in files:
        try:
            before_size += path.stat().st_size
        except OSError:
            pass

    for path in files:
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = 0

        reason = report_file_exclusion_reason(
            path,
            archive_root=archive_root,
            report_profile=report_profile,
        )
        if reason is not None:
            try:
                path.unlink(missing_ok=True)
                pruned_files += 1
                pruned_size += file_size
                pruned_reason_counts[reason] = pruned_reason_counts.get(reason, 0) + 1
            except Exception as exc:
                errors.append(
                    {
                        "path": _safe_relative_path(path, archive_root),
                        "operation": "unlink",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            continue

        if path.suffix.lower() == ".json" and report_profile != DEBUG_REPORT_PROFILE:
            tmp_path = path.with_name(f"{path.name}.compact_tmp")
            try:
                original_size = file_size
                if compact_json_file(path, tmp_path, report_profile=report_profile):
                    os.replace(tmp_path, path)
                    new_size = path.stat().st_size
                    compacted_json_files += 1
                    compacted_json_before_size += original_size
                    compacted_json_after_size += new_size
                else:
                    tmp_path.unlink(missing_ok=True)
                    kept_files += 1
            except Exception as exc:
                tmp_path.unlink(missing_ok=True)
                errors.append(
                    {
                        "path": _safe_relative_path(path, archive_root),
                        "operation": "compact_json",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                kept_files += 1
        else:
            kept_files += 1

    for subdir in sorted(
        [item for item in root.rglob("*") if item.is_dir()],
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        try:
            if not any(subdir.iterdir()):
                subdir.rmdir()
        except OSError:
            pass

    after_entries: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        after_files += 1
        after_size += size
        after_entries.append(
            {
                "path": _safe_relative_path(path, archive_root),
                "size_bytes": int(size),
                "size_mb": _bytes_to_mb(size),
            }
        )

    largest_files = sorted(after_entries, key=lambda item: int(item["size_bytes"]), reverse=True)[:20]

    return {
        "directory": str(root),
        "exists": True,
        "report_profile": report_profile,
        "before_files": int(before_files),
        "before_size_bytes": int(before_size),
        "before_size_mb": _bytes_to_mb(before_size),
        "after_files": int(after_files),
        "after_size_bytes": int(after_size),
        "after_size_mb": _bytes_to_mb(after_size),
        "pruned_files": int(pruned_files),
        "pruned_size_bytes": int(pruned_size),
        "pruned_size_mb": _bytes_to_mb(pruned_size),
        "pruned_reason_counts": pruned_reason_counts,
        "compacted_json_files": int(compacted_json_files),
        "compacted_json_before_size_bytes": int(compacted_json_before_size),
        "compacted_json_after_size_bytes": int(compacted_json_after_size),
        "compacted_json_saved_size_bytes": int(max(0, compacted_json_before_size - compacted_json_after_size)),
        "compacted_json_saved_size_mb": _bytes_to_mb(max(0, compacted_json_before_size - compacted_json_after_size)),
        "kept_files": int(kept_files),
        "largest_files": largest_files,
        "errors": errors,
    }
