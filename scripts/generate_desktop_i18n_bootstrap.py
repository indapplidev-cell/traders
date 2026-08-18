"""Generate the desktop first-run i18n snapshot from the server catalog.

The output is a generated artifact.  It is never edited by hand.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.i18n import catalog_payload, manifest_payload


def build_snapshot() -> dict[str, object]:
    manifest = manifest_payload()
    return {
        "generated_marker": "DO NOT EDIT - generated from traders-ml app.i18n",
        "manifest": manifest,
        "catalogs": {
            locale: catalog_payload(locale) for locale in manifest["supported_locales"]
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--desktop-help-output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_snapshot(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    if args.desktop_help_output is not None:
        source = Path(__file__).resolve().parents[1] / "app" / "i18n" / "help_source.py"
        args.desktop_help_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.desktop_help_output.with_name(f".{args.desktop_help_output.name}.tmp")
        temporary.write_text(
            '# DO NOT EDIT: generated from traders-ml/app/i18n/help_source.py.\n'
            + source.read_text(encoding="utf-8"),
            encoding="utf-8", newline="\n",
        )
        os.replace(temporary, args.desktop_help_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
