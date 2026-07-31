"""CLI for allowlisted production identity inspection.

Only fixed container metadata fields are printed.  Environment, command,
mount, and full inspection objects are outside this tool's contract.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_retry_controls import (
    inspect_alembic_status,
    inspect_container_identity,
    inspect_readonly_health_http,
    inspect_tracked_route_counts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "container",
        nargs="*",
        help="Exact container names to inspect through the fixed allowlist.",
    )
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--routes", action="store_true")
    parser.add_argument("--alembic-container")
    args = parser.parse_args(argv)
    status = 0
    for name in args.container:
        identity = inspect_container_identity(name)
        if identity is None:
            print(f"container_name={name}")
            print("inspection=FAILED")
            status = 1
            continue
        print(identity.render())
    if args.health:
        health = inspect_readonly_health_http()
        print(health.render())
        status = max(status, int(health.status != 200))
    if args.routes:
        routes = inspect_tracked_route_counts()
        print(routes.render())
        status = max(
            status,
            int(routes.get_routes != 9 or routes.write_routes != 0),
        )
    if args.alembic_container:
        alembic = inspect_alembic_status(args.alembic_container)
        print(alembic.render())
        status = max(status, int(alembic.error_class != "NONE"))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
