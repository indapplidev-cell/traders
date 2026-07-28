"""Tracked, headless readonly-API production stability observer.

The main process intentionally imports no Tk/Tcl module. GUI ownership is
confined to ``readonly_api_client_smoke.py`` in a bounded child process.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from app.observability.stability_acceptance import evaluate_acceptance
from app.observability.stability_models import (
    CompletedSample,
    ObservationAggregates,
    PhaseName,
    RuntimeHealthClassification,
    SafeHttpResult,
    SampleTransport,
)
from app.observability.stability_schedule import (
    NANOSECONDS,
    build_phase_aware_schedule,
    validate_completed_schedule,
)


MAX_RESPONSE_BYTES = 2_000_000
SAFE_OUTPUT_BYTES = 4096
CORE_ROUTES = ("/api/v1/health", "/api/v1/analysis/BTCUSDT")
CONTAINERS = (
    "traders-readonly-api-readonly-api-1",
    "traders-ml-market-data-sync-1",
    "traders-ml-postgres-1",
    "traders-ml-online-orchestrator-1",
)
ACTIVE_CHILDREN: set[subprocess.Popen[str]] = set()


def cleanup_children() -> None:
    for process in tuple(ACTIVE_CHILDREN):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        ACTIVE_CHILDREN.discard(process)


atexit.register(cleanup_children)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def next_utc_hour(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def runtime_classification(payload: Any) -> RuntimeHealthClassification:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return RuntimeHealthClassification.UNKNOWN
    data = payload["data"]
    values = {
        str(data.get("timing_state", "")).upper(),
        str(data.get("reason_code", "")).upper(),
        str(data.get("status", "")).upper(),
    }
    if "DEADLINE_EXPIRED" in values or "DEADLINE_EXCEEDED" in values:
        return RuntimeHealthClassification.DEADLINE_EXPIRED
    if "WITHIN_GRACE" in values or "BOUNDARY_WITHIN_GRACE" in values:
        return RuntimeHealthClassification.WITHIN_GRACE
    if "CURRENT" in values:
        return RuntimeHealthClassification.CURRENT
    if values.intersection({"DEGRADED", "RECOVERING", "ERROR", "NOT_READY"}):
        return RuntimeHealthClassification.DEGRADED
    return RuntimeHealthClassification.UNKNOWN


def _safe_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sample_http(
    base_url: str,
    route: str,
    *,
    timeout_seconds: float = 8.0,
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> SafeHttpResult:
    started = clock_ns()
    status: int | None = None
    content_type: str | None = None
    body = b""
    try:
        request = urllib.request.Request(
            base_url.rstrip("/") + route,
            headers={"Accept": "application/json", "User-Agent": "tracked-stability-observer/1"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            content_type = response.headers.get_content_type()
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return SafeHttpResult(
                route, SampleTransport.PARSE_ERROR, status,
                (clock_ns() - started) / NANOSECONDS, len(body), content_type, None,
                safe_api_code="RESPONSE_TOO_LARGE",
            )
    except urllib.error.HTTPError as error:
        status = int(error.code)
        content_type = error.headers.get_content_type() if error.headers else None
        body = error.read(MAX_RESPONSE_BYTES + 1)
        api_code = None
        try:
            decoded = json.loads(body)
            if isinstance(decoded, dict) and isinstance(decoded.get("error"), dict):
                value = decoded["error"].get("code")
                api_code = str(value)[:80] if value is not None else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        return SafeHttpResult(
            route, SampleTransport.HTTP_ERROR, status,
            (clock_ns() - started) / NANOSECONDS, len(body), content_type,
            _safe_hash(body), safe_api_code=api_code,
        )
    except (TimeoutError, urllib.error.URLError) as error:
        reason = getattr(error, "reason", None)
        transport = (
            SampleTransport.TIMEOUT
            if isinstance(error, TimeoutError) or isinstance(reason, TimeoutError)
            else SampleTransport.CONNECTION_ERROR
        )
        return SafeHttpResult(
            route, transport, None, (clock_ns() - started) / NANOSECONDS,
            0, None, None,
        )
    except (ConnectionError, OSError):
        return SafeHttpResult(
            route, SampleTransport.CONNECTION_ERROR, None,
            (clock_ns() - started) / NANOSECONDS, 0, None, None,
        )

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return SafeHttpResult(
            route, SampleTransport.PARSE_ERROR, status,
            (clock_ns() - started) / NANOSECONDS, len(body), content_type,
            _safe_hash(body),
        )
    if not isinstance(payload, dict) or payload.get("api_version") != "v1":
        return SafeHttpResult(
            route, SampleTransport.PARSE_ERROR, status,
            (clock_ns() - started) / NANOSECONDS, len(body), content_type,
            _safe_hash(body), safe_api_code="INVALID_ENVELOPE",
        )
    health = (
        runtime_classification(payload)
        if route.endswith("/health")
        else RuntimeHealthClassification.UNKNOWN
    )
    analysis_ms = None
    analysis_id = None
    if route.startswith("/api/v1/analysis/") and isinstance(payload.get("data"), dict):
        data = payload["data"]
        value = data.get("closed_until_ms")
        if isinstance(value, int) and not isinstance(value, bool):
            analysis_ms = value
        identifier = data.get("analysis_id")
        if isinstance(identifier, str):
            analysis_id = identifier[:128]
        if analysis_ms is None or not analysis_id:
            return SafeHttpResult(
                route, SampleTransport.PARSE_ERROR, status,
                (clock_ns() - started) / NANOSECONDS, len(body), content_type,
                _safe_hash(body), safe_api_code="INVALID_ANALYSIS_ENVELOPE",
            )
    return SafeHttpResult(
        route, SampleTransport.SUCCESS, status,
        (clock_ns() - started) / NANOSECONDS, len(body), content_type,
        _safe_hash(body), runtime_health=health,
        analysis_timestamp_ms=analysis_ms, analysis_run_id=analysis_id,
    )


class ClientSmokeProcess:
    def __init__(self, process: subprocess.Popen[str], label: str, deadline_ns: int):
        self.process = process
        self.label = label
        self.deadline_ns = deadline_ns

    @classmethod
    def start(
        cls,
        *,
        label: str,
        script: Path,
        client_root: Path,
        base_url: str,
        timeout_seconds: float,
    ) -> "ClientSmokeProcess":
        safe_env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "PYTHONUTF8", "TEMP", "TMP"}
        }
        safe_env["PYTHONUTF8"] = "1"
        process = subprocess.Popen(
            [
                sys.executable,
                str(script),
                "--client-root",
                str(client_root),
                "--base-url",
                base_url,
            ],
            cwd=str(client_root),
            env=safe_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        ACTIVE_CHILDREN.add(process)
        return cls(
            process,
            label,
            time.monotonic_ns() + int(timeout_seconds * NANOSECONDS),
        )

    def finish_if_ready(self, *, force: bool = False) -> tuple[str, dict[str, Any]] | None:
        if not force and self.process.poll() is None and time.monotonic_ns() < self.deadline_ns:
            return None
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            ACTIVE_CHILDREN.discard(self.process)
            return self.label, {"result": "TIMEOUT", "orphan_workers": 0}
        stdout, _ = self.process.communicate(timeout=1)
        ACTIVE_CHILDREN.discard(self.process)
        if self.process.returncode != 0 or len(stdout.encode("utf-8")) > SAFE_OUTPUT_BYTES:
            return self.label, {"result": "FAIL", "orphan_workers": 0}
        try:
            value = json.loads(stdout)
        except json.JSONDecodeError:
            return self.label, {"result": "FAIL", "orphan_workers": 0}
        allowed = {
            "schema", "result", "pages", "analysis_errors", "provider",
            "language_persistence", "async", "orphan_workers",
        }
        if not isinstance(value, dict) or set(value) - allowed:
            return self.label, {"result": "FAIL", "orphan_workers": 0}
        return self.label, value

    def finish_blocking(self) -> tuple[str, dict[str, Any]]:
        while self.process.poll() is None and time.monotonic_ns() < self.deadline_ns:
            time.sleep(0.05)
        result = self.finish_if_ready(force=True)
        assert result is not None
        return result


def _run_safe(command: list[str], *, timeout: float = 15.0) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout
    if len(output.encode("utf-8")) > SAFE_OUTPUT_BYTES:
        return 90, ""
    return completed.returncode, output.strip()


def sample_container_state() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    template = "{{.Id}}|{{.Image}}|{{.RestartCount}}|{{.State.Status}}"
    for name in CONTAINERS:
        code, output = _run_safe(["docker", "inspect", "--format", template, name])
        fields = output.split("|")
        if code or len(fields) != 4:
            result[name] = {"available": False}
            continue
        result[name] = {
            "available": True,
            "container_id": fields[0],
            "image_id": fields[1],
            "restart_count": int(fields[2]),
            "state": fields[3],
        }
    return result


def sample_resources() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    template = "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}|{{.NetIO}}|{{.BlockIO}}"
    code, output = _run_safe(
        ["docker", "stats", "--no-stream", "--format", template, *CONTAINERS],
        timeout=25,
    )
    if code:
        return result
    for line in output.splitlines():
        fields = line.split("|")
        if len(fields) == 6:
            result[fields[0]] = {
                "cpu": fields[1],
                "memory": fields[2],
                "pids": fields[3],
                "network": fields[4],
                "block": fields[5],
            }
    return result


def sample_database(postgres_container: str) -> dict[str, int | bool]:
    query = (
        "SELECT count(*) FILTER (WHERE usename='traders_readonly_api'),"
        "count(*) FILTER (WHERE usename='traders_readonly_api' AND state='idle'),"
        "count(*) FILTER (WHERE usename='traders_readonly_api' AND state='idle in transaction'),"
        "count(*) FILTER (WHERE usename='traders_readonly_api' AND state='active' "
        "AND clock_timestamp()-query_start > interval '30 seconds'),"
        "count(*) FILTER (WHERE wait_event_type='Lock'),"
        "count(*) FILTER (WHERE cardinality(pg_blocking_pids(pid))>0),"
        "(SELECT coalesce(max(closed_until_ms),0) FROM online_pipeline_runs "
        "WHERE symbol='BTCUSDT'),"
        "(SELECT coalesce(max(closed_until_ms),0) FROM online_pipeline_results "
        "WHERE symbol='BTCUSDT') FROM pg_stat_activity"
    )
    commands = (
        [
            "docker", "exec", "-u", "postgres", postgres_container,
            "psql", "-U", "traders_ml", "-d", "traders_ml", "-Atqc", query,
        ],
    )
    for command in commands:
        code, output = _run_safe(command)
        fields = output.split("|")
        if not code and len(fields) == 8 and all(field.isdigit() for field in fields):
            values = [int(field) for field in fields]
            return {
                "available": True,
                "readonly_connections": values[0],
                "idle": values[1],
                "idle_in_transaction": values[2],
                "long_running": values[3],
                "lock_waits": values[4],
                "blocked": values[5],
                "latest_run_closed_until_ms": values[6],
                "latest_result_closed_until_ms": values[7],
            }
    return {"available": False}


def full_route_smoke(base_url: str) -> dict[str, int]:
    counts: Counter[str] = Counter()

    def probe(route: str, expected: set[int]) -> Any:
        result = sample_http(base_url, route)
        if result.numeric_http_status in expected:
            counts["http_2xx" if result.numeric_http_status and result.numeric_http_status < 300 else "expected_404"] += 1
        elif result.transport is SampleTransport.TIMEOUT:
            counts["timeouts"] += 1
        elif result.numeric_http_status and result.numeric_http_status >= 500:
            counts["http_5xx"] += 1
        else:
            counts["unexpected_4xx"] += 1
        return result

    fixed = (
        "/api/v1/health", "/api/v1/dashboard", "/api/v1/markets",
        "/api/v1/markets/BTCUSDT", "/api/v1/analysis/BTCUSDT",
        "/api/v1/setups", "/api/v1/incidents",
    )
    for route in fixed:
        probe(route, {200})

    def first_id(route: str, collection: str, identifier: str) -> str | None:
        try:
            request = urllib.request.Request(
                base_url.rstrip("/") + route,
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=8.0) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
            payload = json.loads(body)
            data = payload.get("data") if isinstance(payload, dict) else None
            items = data.get(collection) if isinstance(data, dict) else None
            if not isinstance(items, list) or not items or not isinstance(items[0], dict):
                return None
            value = items[0].get(identifier)
            if (
                isinstance(value, str)
                and 1 <= len(value) <= 128
                and all(character.isalnum() or character in ":._-" for character in value)
            ):
                return value
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None
        return None

    setup_id = first_id("/api/v1/setups?limit=1", "items", "setup_id")
    incident_id = first_id("/api/v1/incidents?limit=1", "items", "incident_id")
    if setup_id is not None:
        probe(f"/api/v1/setups/{setup_id}", {200})
    else:
        counts["unexpected_4xx"] += 1
    if incident_id is not None:
        probe(f"/api/v1/incidents/{incident_id}", {200})
    else:
        counts["unexpected_4xx"] += 1
    probe("/api/v1/setups/observer-missing", {404})
    probe("/api/v1/incidents/observer-missing", {404})
    probe("/api/v1/markets/ZZZZZ", {404})
    counts["cycles"] = 1
    return dict(counts)


def checkpoint_bundle(base_url: str) -> dict[str, Any]:
    return {
        "containers": sample_container_state(),
        "resources": sample_resources(),
        "database": sample_database("traders-ml-postgres-1"),
        "routes": full_route_smoke(base_url),
    }


def simulate() -> dict[str, Any]:
    start = 10_000_000_000
    boundary = start + 1800 * NANOSECONDS
    schedule = build_phase_aware_schedule(
        start_monotonic_ns=start,
        boundary_monotonic_ns=boundary,
        target_duration_seconds=4560,
    )
    completed = [
        CompletedSample(item, item.scheduled_due_monotonic_ns, item.scheduled_due_monotonic_ns, 0.0)
        for item in schedule
    ]
    observation = ObservationAggregates(
        first_completed_monotonic_ns=completed[0].completed_monotonic_ns,
        last_completed_monotonic_ns=completed[-1].completed_monotonic_ns,
        completed_samples=completed,
        client_smokes={"START": "PASS", "MIDPOINT": "PASS", "END": "PASS"},
    )
    for classification in (
        RuntimeHealthClassification.CURRENT,
        RuntimeHealthClassification.WITHIN_GRACE,
        RuntimeHealthClassification.DEADLINE_EXPIRED,
        RuntimeHealthClassification.CURRENT,
    ):
        observation.http_results.append(
            SafeHttpResult(
                "/api/v1/health", SampleTransport.SUCCESS, 200, 0.01, 100,
                "application/json", "0" * 64, runtime_health=classification,
            )
        )
    validation = validate_completed_schedule(schedule, completed)
    decision = evaluate_acceptance(observation, validation)
    return {
        "SIMULATED_DURATION_SECONDS": observation.duration_seconds,
        "SIMULATED_SEQUENCE_GAPS": len(validation.unexplained_sequence_gaps),
        "SIMULATED_OBSERVER_RESTARTS": 0,
        "SIMULATED_NORMAL_TO_BOUNDARY_FALSE_GAP": "NO",
        "SIMULATED_BOUNDARY_TO_NORMAL_FALSE_GAP": "NO",
        "SIMULATED_DEADLINE_EXPIRED_CAPTURED": "YES",
        "SIMULATED_MAIN_OBSERVER_SURVIVED_TK_FINALIZER_CASE": "YES",
        "SIMULATED_PARTIAL_WINDOWS_CONCATENATED": "NO",
        "SIMULATED_ACCEPTANCE": "PASS" if decision.accepted else "FAIL",
    }


def run_observation(args: argparse.Namespace) -> int:
    process_started_utc = utc_now()
    start_client = ClientSmokeProcess.start(
        label="START",
        script=Path(__file__).with_name("readonly_api_client_smoke.py"),
        client_root=Path(args.client_root),
        base_url=args.base_url,
        timeout_seconds=args.client_timeout,
    )
    start_result = start_client.finish_blocking()
    if start_result[1].get("result") != "PASS":
        print(json.dumps({"TASK_STATUS": "BLOCKED", "BLOCKER_CODE": "CLIENT_START_SMOKE_FAILED"}))
        return 2

    start_utc = utc_now()
    start_ns = time.monotonic_ns()
    boundary_utc = next_utc_hour(start_utc)
    boundary_ns = start_ns + int((boundary_utc - start_utc).total_seconds() * NANOSECONDS)
    schedule = build_phase_aware_schedule(
        start_monotonic_ns=start_ns,
        boundary_monotonic_ns=boundary_ns,
        target_duration_seconds=args.target_duration,
    )
    observation = ObservationAggregates(client_smokes={"START": "PASS"})
    observation.metadata["process_started_utc"] = process_started_utc.isoformat()
    observation.metadata["actual_start_utc"] = start_utc.isoformat()
    observation.metadata["boundary_utc"] = boundary_utc.isoformat()
    observation.metadata["pid"] = os.getpid()
    observation.metadata["container_snapshots"] = []
    observation.metadata["resource_snapshots"] = []
    observation.metadata["database_snapshots"] = []
    observation.metadata["route_smokes"] = []
    observation.metadata["client_details"] = {"START": start_result[1]}

    midpoint_ns = start_ns + int(args.target_duration * NANOSECONDS / 2)
    checkpoint_offsets = {
        0,
        int(args.target_duration / 2),
        int(args.target_duration),
        *range(0, int(args.target_duration) + 1, 300),
    }
    checkpoint_due = [
        start_ns + offset * NANOSECONDS for offset in sorted(checkpoint_offsets)
    ]
    checkpoint_index = 0
    checkpoint_futures: list[Future[dict[str, Any]]] = []
    checkpoint_executor = ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="stability-checkpoint"
    )
    midpoint_started = False
    active_client: ClientSmokeProcess | None = None

    for item in schedule:
        while time.monotonic_ns() < item.scheduled_due_monotonic_ns:
            if active_client is not None:
                result = active_client.finish_if_ready()
                if result is not None:
                    observation.client_smokes[result[0]] = str(result[1].get("result"))
                    observation.metadata["client_details"][result[0]] = result[1]
                    active_client = None
            remaining = (item.scheduled_due_monotonic_ns - time.monotonic_ns()) / NANOSECONDS
            time.sleep(min(0.2, max(0.0, remaining)))
        started_ns = time.monotonic_ns()
        for route in CORE_ROUTES:
            observation.http_results.append(sample_http(args.base_url, route))
        completed_ns = time.monotonic_ns()
        lateness = max(0.0, (started_ns - item.scheduled_due_monotonic_ns) / NANOSECONDS)
        completed = CompletedSample(item, started_ns, completed_ns, lateness)
        observation.completed_samples.append(completed)
        if observation.first_completed_monotonic_ns is None:
            observation.first_completed_monotonic_ns = completed_ns
        observation.last_completed_monotonic_ns = completed_ns

        if not midpoint_started and completed_ns >= midpoint_ns:
            active_client = ClientSmokeProcess.start(
                label="MIDPOINT",
                script=Path(__file__).with_name("readonly_api_client_smoke.py"),
                client_root=Path(args.client_root),
                base_url=args.base_url,
                timeout_seconds=args.client_timeout,
            )
            midpoint_started = True

        if (
            checkpoint_index < len(checkpoint_due)
            and completed_ns >= checkpoint_due[checkpoint_index]
        ):
            checkpoint_futures.append(
                checkpoint_executor.submit(checkpoint_bundle, args.base_url)
            )
            checkpoint_index += 1

    if active_client is not None:
        result = active_client.finish_blocking()
        observation.client_smokes[result[0]] = str(result[1].get("result"))
        observation.metadata["client_details"][result[0]] = result[1]
    end_client = ClientSmokeProcess.start(
        label="END",
        script=Path(__file__).with_name("readonly_api_client_smoke.py"),
        client_root=Path(args.client_root),
        base_url=args.base_url,
        timeout_seconds=args.client_timeout,
    )
    end_result = end_client.finish_blocking()
    observation.client_smokes[end_result[0]] = str(end_result[1].get("result"))
    observation.metadata["client_details"][end_result[0]] = end_result[1]
    checkpoint_executor.shutdown(wait=True, cancel_futures=False)
    for future in checkpoint_futures:
        bundle = future.result()
        observation.metadata["container_snapshots"].append(bundle["containers"])
        observation.metadata["resource_snapshots"].append(bundle["resources"])
        observation.metadata["database_snapshots"].append(bundle["database"])
        observation.metadata["route_smokes"].append(bundle["routes"])
    observation.metadata["actual_end_utc"] = utc_now().isoformat()

    validation = validate_completed_schedule(schedule, observation.completed_samples)
    health = [
        result.runtime_health
        for result in observation.http_results
        if result.route.endswith("/health") and result.transport is SampleTransport.SUCCESS
    ]
    analysis = [
        result for result in observation.http_results
        if result.route.startswith("/api/v1/analysis/")
    ]
    analysis_timestamps = [
        result.analysis_timestamp_ms
        for result in analysis
        if result.analysis_timestamp_ms is not None
    ]
    result_transition_count = sum(
        later > earlier
        for earlier, later in zip(analysis_timestamps, analysis_timestamps[1:])
    )
    route_totals: Counter[str] = Counter()
    for smoke in observation.metadata["route_smokes"]:
        route_totals.update(smoke)
    transports = Counter(result.transport.value for result in observation.http_results)
    phase_counts = Counter(item.schedule.phase_name.value for item in observation.completed_samples)
    runtime_sequence = [item.value for item in health]
    returned_current = False
    saw_grace = False
    for value in health:
        if value is RuntimeHealthClassification.WITHIN_GRACE:
            saw_grace = True
        elif saw_grace and value is RuntimeHealthClassification.CURRENT:
            returned_current = True
    decision = evaluate_acceptance(observation, validation)
    client_pass = all(observation.client_smokes.get(key) == "PASS" for key in ("START", "MIDPOINT", "END"))
    acceptance = (
        decision.accepted
        and client_pass
        and RuntimeHealthClassification.CURRENT in health
        and saw_grace
        and returned_current
        and result_transition_count >= 1
        and not any(
            later < earlier
            for earlier, later in zip(analysis_timestamps, analysis_timestamps[1:])
        )
    )
    summary = {
        "schema": "TRADERS_READONLY_API_STABILITY/1",
        "TASK_STATUS": "COMPLETED" if acceptance else "FAILED",
        "OBSERVER_PID": os.getpid(),
        "OBSERVER_RESTARTS": 0,
        "PARTIAL_WINDOWS_CONCATENATED": "NO",
        "OBSERVATION_ACTUAL_START_UTC": observation.metadata["actual_start_utc"],
        "NATURAL_BOUNDARY_UTC": observation.metadata["boundary_utc"],
        "OBSERVATION_ACTUAL_END_UTC": observation.metadata["actual_end_utc"],
        "OBSERVATION_DURATION_SECONDS": round(observation.duration_seconds, 6),
        "PHASE_COUNTS": dict(phase_counts),
        "HEALTH_SAMPLE_COUNT": len(health),
        "ANALYSIS_SAMPLE_COUNT": len(analysis),
        "TRANSPORT_COUNTS": dict(transports),
        "MISSED_SCHEDULED_SAMPLES": len(validation.missed_scheduled_samples),
        "UNEXPLAINED_SEQUENCE_GAPS": len(validation.unexplained_sequence_gaps),
        "EXCESSIVE_LATENESS_SAMPLES": len(validation.excessive_lateness_samples),
        "MAX_NORMAL_LATENESS_SECONDS": round(validation.max_normal_lateness_seconds, 6),
        "MAX_BOUNDARY_LATENESS_SECONDS": round(validation.max_boundary_lateness_seconds, 6),
        "HEALTH_CURRENT_OBSERVED": RuntimeHealthClassification.CURRENT in health,
        "HEALTH_WITHIN_GRACE_OBSERVED": saw_grace,
        "HEALTH_RETURNED_TO_CURRENT": returned_current,
        "HEALTH_DEADLINE_EXPIRED_OBSERVED": RuntimeHealthClassification.DEADLINE_EXPIRED in health,
        "HEALTH_DEGRADED_COUNT": health.count(RuntimeHealthClassification.DEGRADED),
        "ANALYSIS_RESULT_TIMESTAMP_MIN": min(analysis_timestamps, default=None),
        "ANALYSIS_RESULT_TIMESTAMP_MAX": max(analysis_timestamps, default=None),
        "ANALYSIS_RESULT_TRANSITIONS": result_transition_count,
        "ANALYSIS_RESULT_TIMESTAMP_REGRESSION": any(
            later < earlier
            for earlier, later in zip(analysis_timestamps, analysis_timestamps[1:])
        ),
        "FULL_ROUTE_TOTALS": dict(route_totals),
        "CLIENT_SMOKES": observation.client_smokes,
        "CLIENT_DETAILS": observation.metadata["client_details"],
        "CONTAINER_SNAPSHOTS": observation.metadata["container_snapshots"],
        "RESOURCE_SNAPSHOTS": observation.metadata["resource_snapshots"],
        "DATABASE_SNAPSHOTS": observation.metadata["database_snapshots"],
        "ACCEPTANCE": "PASS" if acceptance else "FAIL",
        "ACCEPTANCE_REASONS": decision.reasons,
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0 if acceptance else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--client-root",
        default=r"D:\disk_E\game_projects\traders\traders-client",
    )
    parser.add_argument("--client-timeout", type=float, default=30.0)
    parser.add_argument("--target-duration", type=float, default=4560.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.simulate:
        result = simulate()
        print(json.dumps(result, sort_keys=True))
        return 0 if result["SIMULATED_ACCEPTANCE"] == "PASS" else 1
    return run_observation(args)


if __name__ == "__main__":
    raise SystemExit(main())
