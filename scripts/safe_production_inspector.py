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
    inspect_postgres_capacity_metadata,
    inspect_postgres_archive_health,
    inspect_postgres_volume_identity,
    inspect_postgres_recovery_metadata,
    inspect_readonly_health_http,
    inspect_tracked_route_counts,
)
from scripts.safe_docker_inspection import (
    SafeDockerInspectionError,
    safe_inspect_container,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "container",
        nargs="*",
        help="Exact container names to inspect through the fixed allowlist.",
    )
    parser.add_argument(
        "--extended-container",
        action="append",
        default=[],
        help=(
            "Inspect one exact container through the secret-safe JSON reducer; "
            "may be repeated."
        ),
    )
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--routes", action="store_true")
    parser.add_argument("--alembic-container")
    parser.add_argument("--postgres-recovery-container")
    parser.add_argument("--postgres-size-container")
    parser.add_argument("--postgres-volume-container")
    parser.add_argument("--postgres-archive-health-container")
    args = parser.parse_args(argv)
    status = 0
    for name in args.extended_container:
        try:
            inspection = safe_inspect_container(name)
        except SafeDockerInspectionError:
            print(f"container_name={name}")
            print("inspection=FAILED")
            print("error_class=SAFE_DOCKER_INSPECTION_FAILED")
            status = 1
            continue
        print(inspection.render())
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
            int(routes.get_routes != 28 or routes.write_routes != 0),
        )
    if args.alembic_container:
        alembic = inspect_alembic_status(args.alembic_container)
        print(alembic.render())
        status = max(status, int(alembic.error_class != "NONE"))
    if args.postgres_recovery_container:
        recovery = inspect_postgres_recovery_metadata(
            args.postgres_recovery_container
        )
        print(recovery.render())
        status = max(status, int(recovery.error_class != "NONE"))
    if args.postgres_size_container:
        capacity = inspect_postgres_capacity_metadata(args.postgres_size_container)
        print(capacity.render())
        status = max(status, int(capacity.error_class != "NONE"))
    if args.postgres_volume_container:
        volume = inspect_postgres_volume_identity(args.postgres_volume_container)
        print(volume.render())
        status = max(status, int(volume.error_class != "NONE"))
    if args.postgres_archive_health_container:
        archive = inspect_postgres_archive_health(args.postgres_archive_health_container)
        print(archive.render())
        status = max(status, int(archive.error_class != "NONE" or archive.unresolved_failure is not False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
