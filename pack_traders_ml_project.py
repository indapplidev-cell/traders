#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.reporting.project_packager import build_project_zip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build lightweight traders-ml project zip without artifacts/models and runtime reports."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output zip path. Defaults to reports/project_archives/traders-ml-light.zip",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    output = Path(args.output) if args.output else project_root / "reports" / "project_archives" / "traders-ml-light.zip"
    manifest = build_project_zip(project_root, output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
