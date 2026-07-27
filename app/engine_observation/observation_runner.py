from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .integrity_auditor import audit_integrity
from .latency_analyzer import analyze_latency
from .observation_config import ObservationConfig
from .observation_models import RunRecord, jsonable
from .observation_report import write_artifacts
from .observation_repository import ObservationRepository
from .observation_status import ObservationVerdict, evaluate_verdict
from .pipeline_funnel_analyzer import analyze_funnel
from .reason_code_analyzer import analyze_reasons
from .safety_auditor import audit_safety
from .window_coverage_auditor import audit_coverage


def _read_health(path: Path, now: datetime) -> dict:
    if not path.exists(): return {"path": str(path), "available": False, "current": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        generated = payload.get("generated_at") or payload.get("updated_at")
        parsed = datetime.fromisoformat(generated.replace("Z", "+00:00")) if generated else None
        return {"path": str(path), "available": True, "current": bool(parsed and now - parsed <= timedelta(minutes=5)),
                "generated_at": generated, "overall_status": payload.get("overall_status") or payload.get("status"),
                "operational": payload.get("operational"),
                "ready": payload.get("ready"),
                "acceptance_blocking": payload.get("acceptance_blocking"),
                "reason_code": payload.get("reason_code"),
                "within_grace_count": payload.get("within_grace_count"),
                "deadline_expired_count": payload.get("deadline_expired_count"),
                "daemon_instance_id": payload.get("daemon_instance_id")}
    except Exception as exc:
        return {"path": str(path), "available": True, "current": False, "parse_error": str(exc)}


def summarize_sync_state(rows: list[dict], expected_rows: int = 18) -> dict:
    statuses = Counter(str(row.get("status")) for row in rows)
    lags = [int(row.get("freshness_lag_candles") or 0) for row in rows]
    missing = [int(row.get("missing_count") or 0) for row in rows]
    updated = [row.get("updated_at") for row in rows if row.get("updated_at")]
    severe = sum(status in {"ERROR", "DISCONNECTED"} for status in statuses.elements())
    return {"expected_rows": expected_rows, "actual_rows": len(rows), "status_distribution": dict(statuses),
            "non_ok_rows": sum(count for status, count in statuses.items() if status != "OK") + max(0, expected_rows - len(rows)),
            "severe_rows": severe, "freshness_lag_candles_sum": sum(lags), "freshness_lag_candles_max": max(lags, default=0),
            "missing_count_sum": sum(missing), "missing_count_max": max(missing, default=0),
            "rows_with_last_error_code": sum(bool(row.get("last_error_code")) for row in rows),
            "oldest_updated_at": min(updated).isoformat() if updated else None,
            "historical_limit": "current state only; OK does not prove absence of past transient failures"}


def freshness_events(runs: list[RunRecord]) -> list[dict]:
    successes: dict[str, list[RunRecord]] = {}
    for symbol in {r.symbol for r in runs}:
        successes[symbol] = sorted([r for r in runs if r.symbol == symbol and r.status == "COMPLETED"], key=lambda r: r.closed_until_ms)
    events = []
    for run in runs:
        if run.status != "SKIPPED_FRESHNESS_NOT_OK": continue
        next_run = next((r for r in successes[run.symbol] if r.closed_until_ms > run.closed_until_ms), None)
        events.append({"symbol": run.symbol, "closed_until_utc": run.closed_until_utc,
            "market_data_freshness_status": run.market_data_freshness_status, "affected_timeframes": [],
            "reason": run.final_reason, "duration_until_next_success_ms":
                (next_run.closed_until_ms - run.closed_until_ms) if next_run else None})
    return jsonable(events)


class ObservationRunner:
    def __init__(self, config: ObservationConfig, repository: ObservationRepository) -> None:
        self.config, self.repository = config, repository

    def run(self, *, dry_run: bool = False, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        start, end = self.config.interval(now)
        database = self.repository.check_connection_and_schema()
        availability = self.repository.availability(self.config.symbols, self.config.primary_timeframe)
        first, latest = availability.get("first_utc"), availability.get("latest_utc")
        available_hours = ((latest - first).total_seconds() / 3600 + .25) if first and latest else 0.0
        base = {"database": database, "start_utc": start, "end_utc": end, "availability": {
            "first_available_run_utc": first, "latest_available_run_utc": latest,
            "available_duration_hours": available_hours,
            "earliest_24h_report_utc": first + timedelta(hours=self.config.minimum_window_hours) if first else None}}
        if dry_run:
            return {"dry_run": True, **jsonable(base), "artifacts_written": False}
        runs = self.repository.load_runs(self.config.symbols, self.config.primary_timeframe, start, end)
        results = self.repository.load_results(self.config.symbols, self.config.primary_timeframe,
                                               int(start.timestamp() * 1000), int(end.timestamp() * 1000))
        sync_rows = self.repository.load_sync_state()
        coverage = audit_coverage(runs, self.config.symbols, self.config.primary_timeframe, start, end,
                                  self.config.thresholds.reclaim_interval_seconds, now)
        funnel = analyze_funnel(runs, coverage["aggregate"]["expected_windows"])
        reasons = analyze_reasons(runs, results)
        latency = analyze_latency(runs)
        integrity = audit_integrity(runs, results, reclaim_seconds=self.config.thresholds.reclaim_interval_seconds,
                                    error_max_length=self.config.thresholds.error_message_max_length, now=now)
        safety = audit_safety(runs, results)
        sync_state = summarize_sync_state(sync_rows, len(self.config.symbols) * 6)
        freshness = freshness_events(runs)
        errors = sum(r.status in {"MODULE_ERROR", "ERROR"} for r in runs)
        runtime = {"database": database,
            "market_data_sync_health": _read_health(Path("reports/engine_market_data/continuous_sync/latest_health.json"), now),
            "online_orchestrator_health": _read_health(Path("reports/engine_orchestrator/latest_health.json"), now),
            "independence_evidence": {"distinct_daemon_instances": len({r.daemon_instance_id for r in runs if r.daemon_instance_id}),
                                      "historical_pipeline_records": len(runs), "current_sync_rows": len(sync_rows)}}
        if available_hours < self.config.minimum_window_hours:
            verdict, failures, warnings = ObservationVerdict.BLOCKED_INSUFFICIENT_WINDOW.value, [
                f"available duration {available_hours:.2f}h is below minimum {self.config.minimum_window_hours:.2f}h"], []
        else:
            verdict, failures, warnings = evaluate_verdict(coverage=coverage, integrity=integrity, safety=safety,
                latency=latency, freshness_skip_count=len(freshness), error_count=errors, sync_state=sync_state,
                thresholds=self.config.thresholds, fail_on_warning=self.config.fail_on_warning)
        recommendation = ("D. Fix operational blockers before selecting the next stage." if verdict != ObservationVerdict.PASSED.value
                          else "B. ENGINE-JOURNAL-01 is the default recommendation for a stable online audit trail; choose A or C only when reason/result evidence supports it.")
        summary = {"stage": "ONLINE-PIPELINE-OBSERVATION-01", "verdict": verdict,
            "start_utc": start, "end_utc": end, **base["availability"], **coverage["aggregate"],
            "error_count": errors, "freshness_skip_count": len(freshness),
            "stale_reservation_count": integrity["checks"]["stale_reservations"],
            "failures": failures, "warnings": warnings, "recommended_next_stage": recommendation,
            "runtime_database_writes": False, "pipeline_reruns": False}
        trace = {"freshness_skips": freshness,
                 "errors": [{"run_id": r.run_id, "symbol": r.symbol, "closed_until_utc": r.closed_until_utc,
                             "status": r.status, "error_code": r.error_code, "error_message": (r.error_message or "")[:500]}
                            for r in runs if r.status in {"MODULE_ERROR", "ERROR"}]}
        report = {"summary": summary, "coverage": coverage, "funnel": funnel, "reasons": reasons,
                  "latency": latency, "integrity": integrity, "safety": safety, "trace": trace,
                  "sync_state": sync_state, "runtime": runtime}
        report["artifact_paths"] = write_artifacts(self.config.output_dir, report, self.config.report_md, self.config.report_json)
        return jsonable(report)
