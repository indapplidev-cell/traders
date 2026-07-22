from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .contracts import AcceptanceImpact, SemanticContract, Severity, WindowState
from .expected_windows import expected_candle_keys
from .models import CandleSnapshot, ExpectedWindow, Finding, ResultSnapshot, RunSnapshot, WindowVerdict


WAITING = {"PENDING", "RESERVED", "CHECKING_FRESHNESS", "WAITING_FOR_REQUIRED_BOUNDARY", "READY_TO_RUN", "RUNNING"}
SKIPPED = {"SKIPPED_DUPLICATE_WINDOW", "SKIPPED_FRESHNESS_NOT_OK", "SKIPPED_FRESHNESS_TIMEOUT", "SKIPPED_NOT_ENOUGH_DATA"}
FAILED = {"MODULE_ERROR", "ERROR"}
RECOVERABLE = {"RECOVERING", "GAP_DETECTED", "PERSISTENT_GAP"}


def _finding(kind: str, *, severity: Severity = Severity.ERROR, impact: AcceptanceImpact = AcceptanceImpact.BLOCKING,
             window: ExpectedWindow | None = None, run: RunSnapshot | None = None, reason: str | None = None,
             sub_key: str | None = None, evidence: dict[str, Any] | None = None) -> Finding:
    return Finding(kind, severity, impact, symbol=(run.symbol if run else window.symbol if window else None),
                   timeframe=(run.primary_timeframe if run else window.timeframe if window else None),
                   closed_until_ms=(run.closed_until_ms if run else window.closed_until_ms if window else None),
                   run_id=run.run_id if run else None, reason_code=reason, stable_sub_key=sub_key, evidence=evidence or {})


def _diagnostic_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _deadline(run: RunSnapshot, contract: SemanticContract) -> datetime:
    if run.freshness_deadline_at is not None:
        return run.freshness_deadline_at.astimezone(timezone.utc)
    return datetime.fromtimestamp(run.closed_until_ms / 1000, timezone.utc) + timedelta(seconds=contract.runtime_freshness_grace_seconds)


def _contains_enum_leakage(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key) in {"_value_", "_name_"} or _contains_enum_leakage(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_enum_leakage(item) for item in value)
    return False


def validate_semantics(*, contract: SemanticContract, database_now: datetime, expected: Iterable[ExpectedWindow],
                       runs: Iterable[RunSnapshot], results: Iterable[ResultSnapshot], candles: Iterable[CandleSnapshot],
                       previous_run_ids: dict[str, str] | None = None,
                       previous_states: dict[str, dict[str, Any]] | None = None) -> tuple[list[WindowVerdict], list[Finding]]:
    run_groups: dict[tuple[str, str, int], list[RunSnapshot]] = defaultdict(list)
    result_groups: dict[str, list[ResultSnapshot]] = defaultdict(list)
    candle_groups: Counter[tuple[str, str, int]] = Counter()
    findings: list[Finding] = []
    verdicts: list[WindowVerdict] = []
    expected_list = list(expected)
    expected_by_key = {item.key: item for item in expected_list}
    for run in runs:
        run_groups[run.window_key].append(run)
        if run.window_key not in expected_by_key:
            findings.append(_finding("UNEXPECTED_RUN", run=run, reason="OUTSIDE_CONTRACT"))
    for result in results:
        result_groups[result.run_id].append(result)
    for candle in candles:
        candle_groups[candle.key] += 1
        durations = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
        duration = durations.get(candle.timeframe)
        if duration is not None:
            if not candle.is_closed or candle.close_time_ms >= int(database_now.astimezone(timezone.utc).timestamp() * 1000):
                findings.append(Finding("FUTURE_OR_NON_CLOSED_CANDLE", Severity.ERROR, AcceptanceImpact.BLOCKING,
                                        candle.symbol, candle.timeframe, stable_sub_key="|".join(map(str, candle.key))))
            if candle.open_time_ms % duration or candle.close_time_ms != candle.open_time_ms + duration - 1:
                findings.append(Finding("CANDLE_BOUNDARY_MISALIGNMENT", Severity.ERROR, AcceptanceImpact.BLOCKING,
                                        candle.symbol, candle.timeframe, stable_sub_key="|".join(map(str, candle.key))))

    known_run_ids = {run.run_id for run in runs}
    for run_id, grouped in result_groups.items():
        if run_id not in known_run_ids:
            findings.append(Finding("ORPHAN_RESULT", Severity.ERROR, AcceptanceImpact.BLOCKING, run_id=run_id,
                                    stable_sub_key=run_id, evidence={"result_count": len(grouped)}))
        if len(grouped) > 1:
            findings.append(Finding("DUPLICATE_RESULT", Severity.ERROR, AcceptanceImpact.BLOCKING, run_id=run_id,
                                    stable_sub_key=run_id, evidence={"result_count": len(grouped)}))

    previous_run_ids = previous_run_ids or {}
    now = database_now.astimezone(timezone.utc)

    def candle_coverage(window: ExpectedWindow, *, run: RunSnapshot | None, deadline: datetime) -> list[Finding]:
        if now < deadline:
            return []
        values: list[Finding] = []
        for candle_key in expected_candle_keys(window, contract.required_timeframes):
            count = candle_groups[candle_key]
            kwargs = {"run": run} if run is not None else {"window": window}
            if count == 0:
                values.append(_finding("MISSING_CANDLE", **kwargs, sub_key="|".join(map(str, candle_key)),
                                       evidence={"candle_key": candle_key}))
                values.append(_finding("PERSISTENT_MARKET_DATA_GAP", **kwargs, sub_key="|".join(map(str, candle_key)),
                                       evidence={"candle_key": candle_key, "deadline_at": deadline.isoformat()}))
            elif count > 1:
                values.append(_finding("DUPLICATE_CANDLE", **kwargs, sub_key="|".join(map(str, candle_key)),
                                       evidence={"candle_key": candle_key, "count": count}))
        return values

    for window in expected_list:
        grouped = run_groups.get(window.key, [])
        if not window.due:
            verdicts.append(WindowVerdict(window.key, WindowState.NOT_DUE, None, _diagnostic_hash("NOT_DUE")))
            continue
        if not grouped:
            findings.append(_finding("MISSING_RUN", window=window, reason="APPEARANCE_GRACE_EXPIRED"))
            fallback_deadline = datetime.fromtimestamp(window.closed_until_ms / 1000, timezone.utc) + timedelta(
                seconds=contract.runtime_freshness_grace_seconds)
            findings.extend(candle_coverage(window, run=None, deadline=fallback_deadline))
            verdicts.append(WindowVerdict(window.key, WindowState.DUE_WAITING_FOR_RUN, None, _diagnostic_hash("MISSING")))
            continue
        if len(grouped) > 1:
            findings.append(_finding("DUPLICATE_RUN", window=window, evidence={"run_ids": sorted(item.run_id for item in grouped)}))
            verdicts.append(WindowVerdict(window.key, WindowState.RUN_DUPLICATE, None, _diagnostic_hash([r.run_id for r in grouped])))
            continue
        run = grouped[0]
        key_text = "|".join(map(str, window.key))
        if key_text in previous_run_ids and previous_run_ids[key_text] != run.run_id:
            findings.append(_finding("RUN_ID_CHANGED_DURING_RETRY", run=run, reason="WINDOW_RUN_ID_REPLACED",
                                     evidence={"previous_run_id": previous_run_ids[key_text], "current_run_id": run.run_id}))
        deadline = _deadline(run, contract)
        result_count = len(result_groups.get(run.run_id, ()))
        if _contains_enum_leakage(run.raw_diagnostics):
            findings.append(_finding("INVALID_ENUM_SERIALIZATION", run=run, reason="PRIVATE_ENUM_FIELD"))
        if run.future_bars_used or run.execution_approved or run.position_opened:
            findings.append(_finding("LIVE_GUARD_VIOLATION", run=run, severity=Severity.CRITICAL,
                                     reason="FORBIDDEN_RUNTIME_SAFETY_FLAG",
                                     evidence={"future_bars_used": run.future_bars_used,
                                               "execution_approved": run.execution_approved,
                                               "position_opened": run.position_opened}))
        if run.status == "WAITING_FOR_REQUIRED_BOUNDARY" and not run.waiting_timeframes:
            findings.append(_finding("INVALID_WAITING_TIMEFRAMES", run=run, reason="EMPTY_FOR_STATUS_BLOCKER"))
        recoverable = (run.market_data_freshness_status or "") in RECOVERABLE or any(
            any(token in reason for token in RECOVERABLE) for reason in run.freshness_reasons
        )
        if run.status in SKIPPED:
            premature = now < deadline or (run.finished_at is not None and run.finished_at.astimezone(timezone.utc) < deadline and recoverable)
            kind = "PREMATURE_FRESHNESS_SKIP" if premature else "FRESHNESS_DEADLINE_SKIP"
            severity = Severity.CRITICAL if premature else Severity.ERROR
            findings.append(_finding(kind, run=run, severity=severity, reason=run.reason_code,
                                     evidence={"deadline_at": deadline.isoformat(), "finished_at": str(run.finished_at)}))
            state = WindowState.RUN_SKIPPED
        elif run.status in FAILED:
            findings.append(_finding("RUN_FAILED", run=run, reason=run.reason_code or run.status))
            state = WindowState.RUN_FAILED
        elif run.status == "COMPLETED":
            if result_count == 0:
                findings.append(_finding("COMPLETED_WITHOUT_RESULT", run=run, reason="RESULT_COUNT_ZERO"))
                state = WindowState.RUN_RESULT_CARDINALITY_ERROR
            elif result_count > 1:
                findings.append(_finding("COMPLETED_WITH_MULTIPLE_RESULTS", run=run, reason="RESULT_COUNT_GT_ONE",
                                         evidence={"result_count": result_count}))
                state = WindowState.RUN_RESULT_CARDINALITY_ERROR
            else:
                state = WindowState.RUN_COMPLETED
        elif run.status in WAITING:
            if now >= deadline:
                findings.append(_finding("WAITING_PAST_DEADLINE", run=run, reason=run.reason_code,
                                         evidence={"deadline_at": deadline.isoformat()}))
                state = WindowState.RUN_STUCK
            else:
                state = WindowState.RUN_WAITING_RETRYABLE
        else:
            findings.append(_finding("RUN_STUCK", run=run, reason="UNKNOWN_STATUS", evidence={"status": run.status}))
            state = WindowState.RUN_STUCK
        if run.status != "COMPLETED" and result_count:
            findings.append(_finding("ORPHAN_RESULT", run=run, reason="RESULT_FOR_NON_COMPLETED_RUN",
                                     evidence={"status": run.status, "result_count": result_count}))
        evidence = {"status": run.status, "result_count": result_count, "attempt_count": run.freshness_attempt_count,
                    "waiting_timeframes": run.waiting_timeframes, "freshness_reasons": run.freshness_reasons}
        verdicts.append(WindowVerdict(window.key, state, run.run_id, _diagnostic_hash(evidence), evidence))

        findings.extend(candle_coverage(window, run=run, deadline=deadline))
    terminal = {item.value for item in (WindowState.RUN_COMPLETED, WindowState.RUN_SKIPPED, WindowState.RUN_FAILED,
                                        WindowState.RUN_RESULT_CARDINALITY_ERROR)}
    previous_states = previous_states or {}
    run_by_key = {item.window_key: item for item in runs}
    for verdict in verdicts:
        key_text = "|".join(map(str, verdict.key))
        prior = previous_states.get(key_text, {})
        if prior.get("state") in terminal and verdict.state.value in terminal and prior.get("state") != verdict.state.value:
            run = run_by_key.get(verdict.key)
            findings.append(_finding("RUN_STUCK", run=run, window=None if run else expected_by_key[verdict.key],
                                     reason="MULTIPLE_TERMINAL_TRANSITIONS",
                                     evidence={"previous_state": prior.get("state"), "current_state": verdict.state.value}))
        previous_attempts = prior.get("attempt_count")
        current_attempts = verdict.evidence.get("attempt_count")
        if previous_attempts is not None and current_attempts is not None and int(current_attempts) < int(previous_attempts):
            run = run_by_key.get(verdict.key)
            findings.append(_finding("RUN_STUCK", run=run, window=None if run else expected_by_key[verdict.key],
                                     reason="FRESHNESS_ATTEMPT_RESET",
                                     evidence={"previous_attempt_count": previous_attempts, "current_attempt_count": current_attempts}))
    return verdicts, findings
