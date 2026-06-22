#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packer.project_packager import build_project_zip  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build lightweight traders-ml project zip without artifacts/models/runtime archives."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output zip path. Defaults to reports/project_archives/traders-ml-light.zip",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Do not print packing progress.",
    )
    parser.add_argument(
        "--max-archive-size-mb",
        type=float,
        default=100.0,
        help="Safety guard. Delete output and fail if archive is larger than this value.",
    )
    parser.add_argument(
        "--manifest-output",
        default=None,
        help="Optional external manifest/log JSON path. Defaults to <archive_stem>_manifest.json near output zip.",
    )
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print full manifest JSON to stdout. Disabled by default to keep terminal output compact.",
    )
    return parser.parse_args()


def _print_archive_progress(index: int, total: int, archive_name: str) -> None:
    del archive_name  # File names go to manifest/log, not to terminal.
    percent = 100.0 if total <= 0 else (index / total) * 100.0
    sys.stderr.write(f"\rPACK_PROGRESS {index:>5}/{total:<5} {percent:6.2f}%")
    sys.stderr.flush()
    if index >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


def _default_manifest_output(output: Path) -> Path:
    return output.with_name(f"{output.stem}_manifest.json")


def _write_manifest_log(manifest: dict, manifest_output: Path) -> None:
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    output = (
        Path(args.output)
        if args.output
        else PROJECT_ROOT / "reports" / "project_archives" / "traders-ml-light.zip"
    )
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    manifest_output = Path(args.manifest_output) if args.manifest_output else _default_manifest_output(output)
    if not manifest_output.is_absolute():
        manifest_output = PROJECT_ROOT / manifest_output

    progress_callback = None if args.no_progress else _print_archive_progress

    try:
        print("Идет подготовка к архивации проекта...", file=sys.stderr, flush=True)
        manifest = build_project_zip(
            PROJECT_ROOT,
            output,
            progress_callback=progress_callback,
            max_archive_size_mb=args.max_archive_size_mb,
        )
        manifest["manifest_log_path"] = str(manifest_output)
        _write_manifest_log(manifest, manifest_output)

        if args.print_manifest:
            print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))

        print("Архивация прошла успешно", file=sys.stderr, flush=True)
        print(f"Архив: {output}", file=sys.stderr, flush=True)
        print(f"Лог архивации: {manifest_output}", file=sys.stderr, flush=True)
        return 0
    except Exception as exc:
        if not args.no_progress:
            # Ensure an interrupted carriage-return progress line does not corrupt the error message.
            sys.stderr.write("\n")
            sys.stderr.flush()
        print(f"Ошибка архивации: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
