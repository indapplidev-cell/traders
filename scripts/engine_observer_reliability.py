"""CLI for the crash-safe online orchestrator soak observer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_observation.observer_reliability import (
    CommandCollector,
    JsonFileCollector,
    LockMetadataMismatch,
    ObserverAlreadyRunning,
    ObserverConfig,
    ReadOnlyDatabaseCollector,
    ReliableObserver,
    atomic_write_text,
    audit_jsonl,
    redact,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single-owner, crash-safe production soak observer")
    parser.add_argument("--soak-directory", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--sampling-interval-seconds", type=float, default=60.0)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=10.0)
    parser.add_argument("--allowed-jitter-seconds", type=float, default=15.0)
    parser.add_argument("--gap-threshold-seconds", type=float)
    parser.add_argument("--command-timeout-seconds", type=float, default=15.0)
    parser.add_argument("--db-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--db-dsn-env", default="OBSERVER_READ_ONLY_DSN")
    parser.add_argument("--semantic-contract", type=Path)
    parser.add_argument("--maximum-samples", type=int)
    parser.add_argument("--maximum-runtime-seconds", type=float)
    parser.add_argument("--no-docker", action="store_true")
    parser.add_argument("--request-stop", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    soak = args.soak_directory.resolve()
    if args.request_stop:
        atomic_write_text(soak / "observer.stop.request", "CONTROLLED_STOP_REQUESTED\n")
        print(json.dumps({"status": "STOP_REQUESTED", "soak_directory": str(soak)}))
        return 0
    if args.audit_only:
        print(json.dumps(audit_jsonl(soak), indent=2, sort_keys=True))
        return 0
    collectors = []
    if not args.no_docker:
        collectors.extend([
            CommandCollector("docker_ps", ["docker", "ps", "--no-trunc", "--format", "{{json .}}"], cwd=args.repository, timeout_seconds=args.command_timeout_seconds),
            CommandCollector("docker_stats", ["docker", "stats", "--no-stream", "--format", "{{json .}}"], cwd=args.repository, timeout_seconds=args.command_timeout_seconds),
        ])
    health_paths = {
        "market_data_sync": args.repository / "reports" / "engine_market_data" / "continuous_sync" / "latest_health.json",
        "online_orchestrator": args.repository / "reports" / "engine_orchestrator" / "latest_health.json",
    }
    collectors.append(JsonFileCollector("service_health", health_paths))
    dsn = os.environ.get(args.db_dsn_env)
    if dsn:
        collectors.append(ReadOnlyDatabaseCollector(dsn, timeout_seconds=args.db_timeout_seconds))
    config = ObserverConfig(
        soak_directory=soak,
        sampling_interval_seconds=args.sampling_interval_seconds,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        allowed_jitter_seconds=args.allowed_jitter_seconds,
        gap_threshold_seconds=args.gap_threshold_seconds,
        command_timeout_seconds=args.command_timeout_seconds,
        db_timeout_seconds=args.db_timeout_seconds,
    )
    semantic_monitor = None
    if args.semantic_contract:
        if not dsn:
            parser.error("--semantic-contract requires the configured read-only DSN environment variable")
        from app.engine_observation.semantic import PostgreSQLSemanticRepository, SemanticMonitor, load_semantic_contract
        contract = load_semantic_contract(args.semantic_contract.resolve())
        if contract.soak_directory.resolve() != soak:
            parser.error("semantic contract SOAK_DIRECTORY must match --soak-directory")
        repository = PostgreSQLSemanticRepository(dsn, contract, timeout_seconds=args.db_timeout_seconds)
        # Instance identity is injected after the observer is constructed.
        observer = ReliableObserver(config, collectors, argv=sys.argv)
        semantic_monitor = SemanticMonitor(contract=contract, repository=repository, observer_instance_id=observer.instance_id,
                                           artifact_directory=soak)
        observer.semantic_monitor = semantic_monitor
    else:
        observer = ReliableObserver(config, collectors, argv=sys.argv)
    try:
        return observer.run(maximum_samples=args.maximum_samples, maximum_runtime_seconds=args.maximum_runtime_seconds)
    except ObserverAlreadyRunning as exc:
        print(json.dumps({"status": "REJECTED", "reason_code": exc.reason_code, "error": str(redact(exc))}), file=sys.stderr)
        return 4
    except LockMetadataMismatch as exc:
        print(json.dumps({"status": "FAILED_CLOSED", "reason_code": exc.reason_code, "error": str(redact(exc))}), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
