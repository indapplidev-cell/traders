"""No arguments opens the GUI; arguments select the shared-engine CLI."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path


def main() -> None:
    if len(sys.argv) == 1 or "--gui" in sys.argv[1:]:
        from .ui import main as ui_main
        from .cli import DEFAULT_CONFIG, DEFAULT_OUTPUT_ROOT

        parser = argparse.ArgumentParser(description="Scalping v2 parameter sweep GUI")
        parser.add_argument("--gui", action="store_true")
        parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
        parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
        args = parser.parse_args(sys.argv[1:])
        ui_main(args.config, args.output_root)
    else:
        from .cli import main as cli_main

        cli_main()


if __name__ == "__main__":
    main()
