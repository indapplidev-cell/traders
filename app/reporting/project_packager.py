from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDED_DIR_PARTS = (
    ".git/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    "htmlcov/",
    "artifacts/",
    "reports/feature_regime_experiments/",
    "reports/label_grid_experiments/",
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
)

DEFAULT_EXCLUDED_FILENAMES = (
    ".coverage",
)


def normalize_zip_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def should_include_project_file(path: Path, *, project_root: Path) -> bool:
    path = Path(path)
    project_root = Path(project_root)
    if not path.is_file():
        return False

    try:
        relative_path = normalize_zip_path(path.relative_to(project_root).as_posix())
    except ValueError:
        return False

    if path.name in DEFAULT_EXCLUDED_FILENAMES:
        return False

    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return False

    normalized_with_slash = relative_path + ("/" if path.is_dir() else "")
    for excluded in DEFAULT_EXCLUDED_DIR_PARTS:
        if normalized_with_slash.startswith(excluded) or f"/{excluded}" in normalized_with_slash:
            return False

    return True


def iter_project_files(project_root: Path) -> list[Path]:
    project_root = Path(project_root)
    return sorted(
        path
        for path in project_root.rglob("*")
        if should_include_project_file(path, project_root=project_root)
    )


def build_project_manifest(project_root: Path, files: list[Path]) -> dict[str, Any]:
    project_root = Path(project_root)
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

    largest_files = sorted(entries, key=lambda item: item["size_bytes"], reverse=True)[:20]
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "file_count": len(entries),
        "total_size_bytes": int(total_size),
        "total_size_mb": round(total_size / (1024 * 1024), 6),
        "largest_files": largest_files,
        "excluded_dir_parts": list(DEFAULT_EXCLUDED_DIR_PARTS),
        "excluded_suffixes": list(DEFAULT_EXCLUDED_SUFFIXES),
        "artifacts_included": any(item["path"].startswith("artifacts/") for item in entries),
        "runtime_reports_included": any(
            item["path"].startswith("reports/feature_regime_experiments/")
            or item["path"].startswith("reports/label_grid_experiments/")
            for item in entries
        ),
    }


def build_project_zip(project_root: Path, output_zip: Path) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    output_zip = Path(output_zip).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    files = [path for path in iter_project_files(project_root) if path.resolve() != output_zip]
    manifest = build_project_manifest(project_root, files)

    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(project_root).as_posix())
        archive.writestr(
            "project_archive_manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        )

    manifest["archive_path"] = str(output_zip)
    manifest["archive_size_bytes"] = output_zip.stat().st_size
    manifest["archive_size_mb"] = round(output_zip.stat().st_size / (1024 * 1024), 6)
    return manifest
