from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .observation_models import ResultRecord, RunRecord

ALLOWED_STATUSES = {"PENDING", "RUNNING", "COMPLETED", "SKIPPED_DUPLICATE_WINDOW",
                    "SKIPPED_FRESHNESS_NOT_OK", "SKIPPED_NOT_ENOUGH_DATA", "MODULE_ERROR", "ERROR"}
ALLOWED_FINAL = {None, "PAPER_PLAN_READY", "NO_PLAN", "WAIT", "REJECT", "NO_DECISION", "NO_SETUP", "NO_ACTION", "ERROR"}


def _large_candle_array(value: Any, path: str = "") -> list[str]:
    violations = []
    if isinstance(value, dict):
        for key, child in value.items(): violations.extend(_large_candle_array(child, f"{path}.{key}"))
    elif isinstance(value, list):
        looks_like_candles = len(value) > 5 and all(isinstance(item, dict) for item in value[:5]) and any(
            {"open", "high", "low", "close"}.issubset({str(k).lower() for k in item}) for item in value[:5])
        if looks_like_candles: violations.append(path)
        for index, child in enumerate(value[:20]): violations.extend(_large_candle_array(child, f"{path}[{index}]"))
    return violations


def audit_integrity(runs: list[RunRecord], results: list[ResultRecord], *, reclaim_seconds: int = 300,
                    error_max_length: int = 4000, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    counts = Counter((r.symbol, r.primary_timeframe, r.closed_until_ms) for r in runs)
    duplicate_keys = [key for key, count in counts.items() if count > 1]
    run_ids, result_run_ids = {r.run_id for r in runs}, {r.run_id for r in results}
    orphans = sorted(result_run_ids - run_ids)
    missing_results = sorted(r.run_id for r in runs if r.status == "COMPLETED" and r.run_id not in result_run_ids)
    missing_finished = sorted(r.run_id for r in runs if r.status == "COMPLETED" and r.finished_at is None)
    negative_duration = sorted(r.run_id for r in runs if r.duration_ms is not None and r.duration_ms < 0)
    boundary_mismatch = sorted(r.run_id for r in runs if abs(r.closed_until_utc.timestamp() * 1000 - r.closed_until_ms) >= 1)
    non_utc = sorted(r.run_id for r in runs if any(v is not None and v.utcoffset() != timedelta(0)
                     for v in (r.closed_until_utc, r.started_at, r.finished_at)))
    stale = sorted(r.run_id for r in runs if r.status in {"PENDING", "RUNNING"}
                   and (r.started_at or r.closed_until_utc) <= now - timedelta(seconds=reclaim_seconds))
    invalid_vocabulary = sorted(r.run_id for r in runs if r.status not in ALLOWED_STATUSES or r.final_result not in ALLOWED_FINAL)
    missing_daemon = sorted(r.run_id for r in runs if not r.daemon_instance_id)
    long_errors = sorted(r.run_id for r in runs if len(r.error_message or "") > error_max_length)
    payload_arrays = []
    for result in results:
        for field in ("market_data_payload_json", "analysis_payload_json", "setup_payload_json",
                      "strategy_payload_json", "risk_payload_json", "paper_payload_json"):
            payload_arrays.extend(f"{result.run_id}:{field}{path}" for path in _large_candle_array(getattr(result, field)))
    invalid_transitions = transition_violations(runs, results)
    checks = {
        "duplicate_business_keys": len(duplicate_keys), "orphan_result_rows": len(orphans),
        "completed_without_result": len(missing_results), "completed_without_finished_at": len(missing_finished),
        "negative_duration": len(negative_duration), "boundary_timestamp_mismatch": len(boundary_mismatch),
        "non_utc_timestamps": len(non_utc), "full_candle_history_payloads": len(payload_arrays),
        "oversized_error_messages": len(long_errors), "invalid_vocabulary": len(invalid_vocabulary),
        "missing_daemon_instance_id": len(missing_daemon), "stale_reservations": len(stale),
        "invalid_transitions": len(invalid_transitions),
    }
    return {"checks": checks, "details": {"duplicate_business_keys": duplicate_keys, "orphan_result_rows": orphans,
            "completed_without_result": missing_results, "stale_reservations": stale,
            "invalid_transitions": invalid_transitions, "full_candle_history_payloads": payload_arrays}}


def transition_violations(runs: list[RunRecord], results: list[ResultRecord]) -> list[dict]:
    result_by_run = {r.run_id: r for r in results}
    violations = []
    for run in runs:
        result = result_by_run.get(run.run_id)
        def add(rule): violations.append({"run_id": run.run_id, "rule": rule})
        if run.analysis_status is None and any(v not in {None, "NO_DECISION", "NO_PLAN"} for v in
                                                   (run.setup_status, run.strategy_status, run.risk_status, run.paper_status)):
            add("DOWNSTREAM_SUCCESS_WITHOUT_ANALYSIS")
        if run.setup_status in {"NO_SETUP", "INVALID", "WAITING_CONFIRMATION"} and run.strategy_status == "ALLOW": add("STRATEGY_ALLOW_WITHOUT_CANDIDATE")
        if run.strategy_status == "REJECT" and run.risk_status == "PRE_APPROVED": add("RISK_PRE_APPROVED_AFTER_STRATEGY_REJECT")
        if run.risk_status in {"REJECT", "BLOCKED"} and run.paper_status == "PAPER_PLAN_READY": add("PAPER_READY_AFTER_RISK_REJECT")
        if run.status == "SKIPPED_FRESHNESS_NOT_OK" and any(v is not None for v in
                (run.analysis_status, run.setup_status, run.strategy_status, run.risk_status, run.paper_status)):
            add("MODULES_RAN_AFTER_FRESHNESS_SKIP")
        if run.paper_status == "PAPER_PLAN_READY":
            payload = result.paper_payload_json if result else {}
            text = str(payload).lower()
            if not all(any(token in text for token in group) for group in
                       (("entry",), ("stop", "invalidation"), ("target",), ("planned_rr", "risk_reward"))):
                add("PAPER_READY_MISSING_CAUSAL_PLAN_FIELDS")
    return violations
