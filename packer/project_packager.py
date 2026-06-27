from __future__ import annotations

import json
import os
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDED_DIR_PARTS = (
    ".git/",
    ".venv/",
    "venv/",
    "env/",
    ".venv_broken/",
    "__pycache__/",
    ".pytest_cache/",
    "htmlcov/",
    "artifacts/",
    "reports/feature_regime_experiments/",
    "reports/label_grid_experiments/",
    "reports/project_archives/",
    "traders_ml.egg-info/",
)

DEFAULT_EXCLUDED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tgz",
    ".gz",
    ".pt",
    ".pth",
    ".onnx",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".log",
    ".jsonl",
)

DEFAULT_EXCLUDED_FILENAMES = (
    ".coverage",
    "training_pipeline.log",
    "training_pipeline_events.jsonl",
)

DEFAULT_EXCLUDED_REPORT_FILE_PATTERNS = (
    "reports/baseline_*.json",
    "reports/calibration_eval_*.json",
    "reports/dataset_summary_*.json",
    "reports/model_comparison_*.json",
    "reports/model_diagnostics_*.json",
    "reports/probability_diagnostics_*.json",
    "reports/profit_eval_v2_*.json",
    "reports/walk_forward_eval_*.json",
    "reports/multi_symbol_feature_regime_analysis.json",
    "reports/multi_symbol_feature_regime_analysis.md",
    "reports/candle_cache_summary.json",
)

ProjectArchiveProgressCallback = Callable[[int, int, str], None]


def normalize_zip_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _matches_excluded_report_file_pattern(relative_path: str) -> bool:
    normalized = normalize_zip_path(relative_path).lower()
    return any(fnmatch(normalized, pattern.lower()) for pattern in DEFAULT_EXCLUDED_REPORT_FILE_PATTERNS)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _relative_zip_path(path: Path, *, project_root: Path) -> str | None:
    try:
        return normalize_zip_path(path.relative_to(project_root).as_posix())
    except ValueError:
        return None


def should_include_project_file(
    path: Path,
    *,
    project_root: Path,
    output_zip: Path | None = None,
) -> bool:
    path = Path(path)
    project_root = Path(project_root)

    if not path.is_file():
        return False

    resolved_path = path.resolve()
    if output_zip is not None and resolved_path == output_zip.resolve():
        return False

    relative_path = _relative_zip_path(path, project_root=project_root)
    if relative_path is None:
        return False

    if output_zip is not None:
        output_parent = output_zip.resolve().parent
        if is_relative_to(resolved_path, output_parent):
            return False

    if path.name in DEFAULT_EXCLUDED_FILENAMES:
        return False

    if _matches_excluded_report_file_pattern(relative_path):
        return False

    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return False

    for excluded in DEFAULT_EXCLUDED_DIR_PARTS:
        excluded = normalize_zip_path(excluded).rstrip("/") + "/"
        if relative_path.startswith(excluded):
            return False

    return True


def iter_project_files(project_root: Path, *, output_zip: Path | None = None) -> list[Path]:
    project_root = Path(project_root).resolve()
    return sorted(
        path
        for path in project_root.rglob("*")
        if should_include_project_file(path, project_root=project_root, output_zip=output_zip)
    )


def build_project_manifest(project_root: Path, files: list[Path]) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    entries = []
    total_size = 0
    for path in files:
        size = path.stat().st_size
        total_size += size
        entries.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "size_bytes": int(size),
            }
        )

    largest_files = sorted(entries, key=lambda item: item["size_bytes"], reverse=True)[:30]
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "file_count": len(entries),
        "total_input_size_bytes": int(total_size),
        "total_input_size_mb": round(total_size / (1024 * 1024), 6),
        "largest_files": largest_files,
        "excluded_dir_parts": list(DEFAULT_EXCLUDED_DIR_PARTS),
        "excluded_suffixes": list(DEFAULT_EXCLUDED_SUFFIXES),
        "excluded_filenames": list(DEFAULT_EXCLUDED_FILENAMES),
        "excluded_report_file_patterns": list(DEFAULT_EXCLUDED_REPORT_FILE_PATTERNS),
        "artifacts_included": any(item["path"].startswith("artifacts/") for item in entries),
        "project_archives_included": any(item["path"].startswith("reports/project_archives/") for item in entries),
        "runtime_reports_included": any(
            item["path"].startswith("reports/feature_regime_experiments/")
            or item["path"].startswith("reports/label_grid_experiments/")
            or _matches_excluded_report_file_pattern(item["path"])
            for item in entries
        ),
        "generated_root_reports_included": any(
            _matches_excluded_report_file_pattern(item["path"]) for item in entries
        ),
        "model_files_included": any(
            item["path"].endswith((".pt", ".pth", ".onnx")) for item in entries
        ),
    }


def _validate_archive_inputs(files: list[Path], *, project_root: Path, output_zip: Path) -> None:
    output_zip_resolved = output_zip.resolve()
    output_parent_resolved = output_zip_resolved.parent
    bad_paths: list[str] = []

    for path in files:
        resolved = path.resolve()
        relative_path = path.relative_to(project_root).as_posix()
        if resolved == output_zip_resolved:
            bad_paths.append(relative_path)
        elif is_relative_to(resolved, output_parent_resolved):
            bad_paths.append(relative_path)
        elif relative_path.startswith("reports/project_archives/"):
            bad_paths.append(relative_path)
        elif relative_path.startswith("artifacts/"):
            bad_paths.append(relative_path)
        elif Path(relative_path).suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
            bad_paths.append(relative_path)

    if bad_paths:
        preview = "\n".join(f"- {path}" for path in bad_paths[:50])
        raise RuntimeError(
            "Unsafe archive input detected. Refusing to build project archive.\n"
            f"First unsafe paths:\n{preview}"
        )


def build_project_zip(
    project_root: Path,
    output_zip: Path,
    *,
    progress_callback: ProjectArchiveProgressCallback | None = None,
    max_archive_size_mb: float = 100.0,
) -> dict[str, Any]:
    """Build lightweight project zip and optionally report per-entry progress."""
    project_root = Path(project_root).resolve()
    output_zip = Path(output_zip).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    files = iter_project_files(project_root, output_zip=output_zip)
    _validate_archive_inputs(files, project_root=project_root, output_zip=output_zip)
    manifest = build_project_manifest(project_root, files)
    manifest["archive_path"] = str(output_zip)
    manifest["max_archive_size_mb"] = max_archive_size_mb

    if output_zip.exists():
        output_zip.unlink()

    total_archive_entries = len(files) + 1

    try:
        with zipfile.ZipFile(
            output_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            for index, path in enumerate(files, start=1):
                archive_name = path.relative_to(project_root).as_posix()
                archive.write(path, archive_name)
                if progress_callback is not None:
                    progress_callback(index, total_archive_entries, archive_name)

            manifest_name = "project_archive_manifest.json"
            archive.writestr(
                manifest_name,
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            )
            if progress_callback is not None:
                progress_callback(total_archive_entries, total_archive_entries, manifest_name)
    except Exception:
        if output_zip.exists():
            output_zip.unlink()
        raise

    archive_size_bytes = output_zip.stat().st_size
    archive_size_mb = archive_size_bytes / (1024 * 1024)
    manifest["archive_size_bytes"] = int(archive_size_bytes)
    manifest["archive_size_mb"] = round(archive_size_mb, 6)
    manifest["compression_ratio"] = round(
        archive_size_bytes / max(1, int(manifest["total_input_size_bytes"])), 6
    )

    if archive_size_mb > max_archive_size_mb:
        output_zip.unlink(missing_ok=True)
        largest = json.dumps(
            manifest.get("largest_files", [])[:20],
            ensure_ascii=False,
            indent=2,
        )
        raise RuntimeError(
            "Project archive is too large and was deleted. "
            f"archive_size_mb={archive_size_mb:.2f}, max_archive_size_mb={max_archive_size_mb:.2f}.\n"
            "Largest input files from manifest:\n"
            f"{largest}"
        )

    return manifest
