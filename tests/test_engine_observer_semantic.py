from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.engine_observation.observer_reliability import CollectorStatus, ObserverConfig, ReliableObserver, audit_jsonl
from app.engine_observation.semantic.contracts import AcceptanceImpact, SemanticContract, Severity, WindowState, load_semantic_contract
from app.engine_observation.semantic.expected_windows import expected_candle_keys, generate_expected_windows
from app.engine_observation.semantic.incident_engine import IncidentEngine, incident_id
from app.engine_observation.semantic.models import CandleSnapshot, Finding, ResultSnapshot, RunSnapshot, SemanticCollection
from app.engine_observation.semantic.monitor import SemanticMonitor
from app.engine_observation.semantic.state_store import SemanticStateError, SemanticStateStore
from app.engine_observation.semantic.validators import validate_semantics


UTC = timezone.utc
ANCHOR = 1_800_000_000_000
NOW = datetime.fromtimestamp((ANCHOR + 3_600_000) / 1000, UTC)


def contract(path: Path, *, symbols=("BTCUSDT",), boundaries=4, grace=60) -> SemanticContract:
    return SemanticContract(
        soak_id="SOAK-TEST", soak_directory=path, symbols=symbols, primary_timeframe="15m",
        anchor_closed_until_ms=ANCHOR, anchor_excluded=True, first_measured_boundary_ms=ANCHOR + 900_000,
        last_measured_boundary_ms=ANCHOR + boundaries * 900_000, settlement_end_ms=ANCHOR + boundaries * 900_000 + 600_000,
        expected_boundaries_per_symbol=boundaries, expected_total_windows=boundaries * len(symbols),
        freshness_deadline_policy="PERSISTED_OR_RUNTIME_GRACE", missing_run_grace_seconds=grace,
        required_timeframes=("1m", "5m", "15m", "1h", "4h", "1d"), strict_freshness_mode=True,
        higher_timeframe_policy="STRICT", sample_interval_seconds=60, semantic_lookback_windows=8,
        runtime_freshness_grace_seconds=180,
    )


def run_for(c: SemanticContract, index=1, **changes) -> RunSnapshot:
    boundary = c.anchor_closed_until_ms + index * 900_000
    base = RunSnapshot("run-1", c.symbols[0], "15m", boundary, "COMPLETED",
                       freshness_deadline_at=datetime.fromtimestamp((boundary + 180_000) / 1000, UTC),
                       created_at=datetime.fromtimestamp(boundary / 1000, UTC), updated_at=NOW)
    return replace(base, **changes)


def result_for(run: RunSnapshot, suffix="1") -> ResultSnapshot:
    return ResultSnapshot("result-" + suffix, run.run_id, NOW, "NO_ACTION", "a" * 64)


def candles_for(c: SemanticContract, window_index=1):
    window = generate_expected_windows(c, NOW)[(window_index - 1) * len(c.symbols)]
    durations = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
    return tuple(CandleSnapshot(symbol, timeframe, opened, opened + durations[timeframe] - 1, True)
                 for symbol, timeframe, opened in expected_candle_keys(window, c.required_timeframes))


def validate(c, runs=(), results=(), candles=(), now=NOW, previous=None):
    expected = generate_expected_windows(c, now)
    return validate_semantics(contract=c, database_now=now, expected=expected, runs=runs, results=results,
                              candles=candles, previous_run_ids=previous)


def kinds(findings):
    return {item.incident_type for item in findings}


def test_expected_windows_anchor_excluded_counts_arbitrary_symbols_and_db_clock(tmp_path):
    c = contract(tmp_path, symbols=("X", "Y", "Z"), boundaries=288)
    windows = generate_expected_windows(c, datetime.fromtimestamp((ANCHOR + 900_000) / 1000, UTC))
    assert windows[0].closed_until_ms == ANCHOR + 900_000
    assert windows[-1].closed_until_ms == ANCHOR + 72 * 3_600_000
    assert len(windows) == 864
    assert sum(item.due for item in windows) == 0  # appearance grace is controlled by DB clock
    later = generate_expected_windows(c, datetime.fromtimestamp((ANCHOR + 900_000 + 60_000) / 1000, UTC))
    assert sum(item.due for item in later) == 3


@pytest.mark.parametrize("change", [
    {"anchor_excluded": False}, {"first_measured_boundary_ms": ANCHOR}, {"expected_total_windows": 99},
    {"freshness_deadline_policy": "SILENT_FALLBACK"},
])
def test_invalid_contract_rejected(tmp_path, change):
    with pytest.raises(ValueError):
        replace(contract(tmp_path), **change)


def test_markdown_contract_parser_requires_semantic_policy(tmp_path):
    path = tmp_path / "SOAK_CONTRACT.md"
    path.write_text(f"""SOAK_ID = S\nSOAK_DIRECTORY = {tmp_path}\nSYMBOLS = BTCUSDT, ETHUSDT\nPRIMARY_TIMEFRAME = 15m
ANCHOR_CLOSED_UNTIL_MS = {ANCHOR}\nANCHOR_EXCLUDED = YES\nFIRST_MEASURED_BOUNDARY_MS = {ANCHOR+900000}
LAST_MEASURED_BOUNDARY_MS = {ANCHOR+1800000}\nSETTLEMENT_END_MS = {ANCHOR+2400000}
EXPECTED_BOUNDARIES_PER_SYMBOL = 2\nEXPECTED_TOTAL_WINDOWS = 4\nFRESHNESS_DEADLINE_POLICY = PERSISTED_OR_RUNTIME_GRACE
MISSING_RUN_GRACE_SECONDS = 60\nREQUIRED_TIMEFRAMES = 1m,5m,15m,1h,4h,1d\nSTRICT_FRESHNESS_MODE = YES
HIGHER_TIMEFRAME_POLICY = STRICT\nSEMANTIC_LOOKBACK_WINDOWS = 8\nFRESHNESS_GRACE_SECONDS = 180\nOBSERVER_SAMPLE_INTERVAL_SECONDS = 60\n""", encoding="utf-8")
    parsed = load_semantic_contract(path)
    assert parsed.symbols == ("BTCUSDT", "ETHUSDT") and parsed.expected_total_windows == 4


def test_missing_run_only_after_grace(tmp_path):
    c = contract(tmp_path)
    before = datetime.fromtimestamp((ANCHOR + 900_000 + 59_000) / 1000, UTC)
    assert "MISSING_RUN" not in kinds(validate(c, now=before)[1])
    after = datetime.fromtimestamp((ANCHOR + 900_000 + 60_000) / 1000, UTC)
    assert "MISSING_RUN" in kinds(validate(c, now=after)[1])


def test_completed_exactly_once_and_result_cardinality(tmp_path):
    c = contract(tmp_path)
    run = run_for(c)
    verdicts, findings = validate(c, (run,), (result_for(run),), candles_for(c))
    assert next(item for item in verdicts if item.key == run.window_key).state == WindowState.RUN_COMPLETED
    assert "COMPLETED_WITHOUT_RESULT" not in kinds(findings)
    assert "COMPLETED_WITHOUT_RESULT" in kinds(validate(c, (run,), (), candles_for(c))[1])
    assert {"COMPLETED_WITH_MULTIPLE_RESULTS", "DUPLICATE_RESULT"}.issubset(kinds(validate(c, (run,), (result_for(run), result_for(run, "2")), candles_for(c))[1]))


def test_skipped_zero_result_valid_cardinality_but_acceptance_incident(tmp_path):
    c = contract(tmp_path)
    run = run_for(c, status="SKIPPED_FRESHNESS_TIMEOUT", finished_at=NOW - timedelta(minutes=1))
    found = kinds(validate(c, (run,), (), candles_for(c))[1])
    assert "COMPLETED_WITHOUT_RESULT" not in found
    assert "FRESHNESS_DEADLINE_SKIP" in found


def test_waiting_before_and_past_deadline(tmp_path):
    c = contract(tmp_path)
    waiting = run_for(c, status="WAITING_FOR_REQUIRED_BOUNDARY", waiting_timeframes=("1h",),
                      freshness_deadline_at=NOW + timedelta(minutes=1), market_data_freshness_status="RECOVERING")
    verdicts, findings = validate(c, (waiting,), (), ())
    assert next(item for item in verdicts if item.key == waiting.window_key).state == WindowState.RUN_WAITING_RETRYABLE
    assert "WAITING_PAST_DEADLINE" not in kinds(findings)
    past = replace(waiting, freshness_deadline_at=NOW - timedelta(seconds=1))
    assert "WAITING_PAST_DEADLINE" in kinds(validate(c, (past,), (), ())[1])


@pytest.mark.parametrize("health", ["RECOVERING", "GAP_DETECTED", "PERSISTENT_GAP"])
def test_recoverable_status_before_deadline_is_retryable_regardless_attempt_count(tmp_path, health):
    c = contract(tmp_path)
    run = run_for(c, status="WAITING_FOR_REQUIRED_BOUNDARY", waiting_timeframes=("1h",),
                  freshness_deadline_at=NOW + timedelta(minutes=1), market_data_freshness_status=health,
                  freshness_attempt_count=10_000)
    verdicts, findings = validate(c, (run,), (), ())
    assert next(item for item in verdicts if item.key == run.window_key).state == WindowState.RUN_WAITING_RETRYABLE
    assert "PREMATURE_FRESHNESS_SKIP" not in kinds(findings)


def test_premature_skip_empty_waiting_enum_leakage_failed_and_run_change(tmp_path):
    c = contract(tmp_path)
    premature = run_for(c, status="SKIPPED_FRESHNESS_TIMEOUT", finished_at=NOW,
                        freshness_deadline_at=NOW + timedelta(minutes=1), market_data_freshness_status="RECOVERING",
                        raw_diagnostics={"status": {"_value_": "RECOVERING"}})
    found = kinds(validate(c, (premature,), (), (), previous={"|".join(map(str, premature.window_key)): "old-run"})[1])
    assert {"PREMATURE_FRESHNESS_SKIP", "INVALID_ENUM_SERIALIZATION", "RUN_ID_CHANGED_DURING_RETRY"}.issubset(found)
    empty = replace(premature, status="WAITING_FOR_REQUIRED_BOUNDARY", waiting_timeframes=(), freshness_deadline_at=NOW + timedelta(minutes=1))
    assert "INVALID_WAITING_TIMEFRAMES" in kinds(validate(c, (empty,), (), ())[1])
    assert "RUN_FAILED" in kinds(validate(c, (replace(premature, status="ERROR"),), (), ())[1])


def test_attempt_reset_and_multiple_terminal_transition_are_detected(tmp_path):
    c = contract(tmp_path)
    run = run_for(c, freshness_attempt_count=2)
    key = "|".join(map(str, run.window_key))
    _, findings = validate_semantics(contract=c, database_now=NOW, expected=generate_expected_windows(c, NOW),
                                     runs=(run,), results=(result_for(run),), candles=candles_for(c),
                                     previous_states={key: {"state": "RUN_SKIPPED", "attempt_count": 3}})
    stuck = [item for item in findings if item.incident_type == "RUN_STUCK"]
    assert {item.reason_code for item in stuck} == {"MULTIPLE_TERMINAL_TRANSITIONS", "FRESHNESS_ATTEMPT_RESET"}


def test_duplicate_unexpected_runs_orphan_result(tmp_path):
    c = contract(tmp_path)
    run = run_for(c)
    duplicate = replace(run, run_id="run-2")
    outside = replace(run, run_id="outside", closed_until_ms=c.last_measured_boundary_ms + 900_000)
    orphan = ResultSnapshot("r", "unknown", NOW, None, "x")
    found = kinds(validate(c, (run, duplicate, outside), (orphan,), ())[1])
    assert {"DUPLICATE_RUN", "UNEXPECTED_RUN", "ORPHAN_RESULT"}.issubset(found)


def test_candle_coverage_counts_boundaries_and_anomalies(tmp_path):
    c = contract(tmp_path)
    window = generate_expected_windows(c, NOW)[0]
    keys = expected_candle_keys(window, c.required_timeframes)
    assert sum(key[1] == "1m" for key in keys) == 15
    assert sum(key[1] == "5m" for key in keys) == 3
    assert sum(key[1] == "15m" for key in keys) == 1
    run = run_for(c)
    def current_kinds(findings):
        return {item.incident_type for item in findings if item.closed_until_ms == run.closed_until_ms}
    candles = list(candles_for(c))
    assert "PERSISTENT_MARKET_DATA_GAP" not in current_kinds(validate(c, (run,), (result_for(run),), candles)[1])
    candles.pop()
    found = current_kinds(validate(c, (run,), (result_for(run),), candles)[1])
    assert {"MISSING_CANDLE", "PERSISTENT_MARKET_DATA_GAP"}.issubset(found)
    duplicate = candles + [candles[0]]
    assert "DUPLICATE_CANDLE" in current_kinds(validate(c, (run,), (result_for(run),), duplicate)[1])
    bad = [replace(candles[0], is_closed=False, open_time_ms=candles[0].open_time_ms + 1)] + candles[1:]
    found = kinds(validate(c, (run,), (result_for(run),), bad)[1])
    assert "FUTURE_OR_NON_CLOSED_CANDLE" in found or "CANDLE_BOUNDARY_MISALIGNMENT" in found


def test_candle_absence_is_temporary_before_deadline_and_persistent_without_run_after(tmp_path):
    c = contract(tmp_path, grace=0)
    boundary = c.first_measured_boundary_ms
    before = datetime.fromtimestamp((boundary + 179_000) / 1000, UTC)
    assert "PERSISTENT_MARKET_DATA_GAP" not in kinds(validate(c, (), (), (), now=before)[1])
    after = datetime.fromtimestamp((boundary + 180_000) / 1000, UTC)
    found = kinds(validate(c, (), (), (), now=after)[1])
    assert {"MISSING_RUN", "MISSING_CANDLE", "PERSISTENT_MARKET_DATA_GAP"}.issubset(found)


def test_higher_timeframe_candles_only_on_aligned_closed_boundary(tmp_path):
    c = contract(tmp_path)
    windows = generate_expected_windows(c, NOW)
    assert not any(key[1] == "1h" for key in expected_candle_keys(windows[0], c.required_timeframes))
    assert sum(key[1] == "1h" for key in expected_candle_keys(windows[3], c.required_timeframes)) == 1


def test_incident_determinism_update_resolution_and_partial_safety(tmp_path):
    finding = Finding("MISSING_RUN", Severity.ERROR, AcceptanceImpact.BLOCKING, "BTCUSDT", "15m", ANCHOR + 900_000)
    assert incident_id("S", finding) == incident_id("S", finding)
    engine = IncidentEngine(tmp_path / "incident_log.jsonl", soak_id="S", observer_instance_id="one")
    state = {"incidents": {}}
    first = engine.reconcile([finding], state, NOW, complete_snapshot=True)
    second = engine.reconcile([finding], state, NOW + timedelta(minutes=1), complete_snapshot=True)
    assert first[0]["state"] == "OPEN" and second[0]["state"] == "UPDATED" and second[0]["occurrence_count"] == 2
    assert engine.reconcile([], state, NOW + timedelta(minutes=2), complete_snapshot=False) == []
    resolved = engine.reconcile([], state, NOW + timedelta(minutes=3), complete_snapshot=True)
    assert len(resolved) == 1 and resolved[0]["state"] == "RESOLVED"
    assert engine.reconcile([], state, NOW + timedelta(minutes=4), complete_snapshot=True) == []
    assert all(json.loads(line) for line in (tmp_path / "incident_log.jsonl").read_text().splitlines())


def test_incident_ids_differ_by_symbol_and_window(tmp_path):
    one = Finding("MISSING_RUN", Severity.ERROR, AcceptanceImpact.BLOCKING, "BTCUSDT", "15m", 1)
    two = replace(one, symbol="ETHUSDT")
    three = replace(one, closed_until_ms=2)
    assert len({incident_id("S", one), incident_id("S", two), incident_id("S", three)}) == 3


def test_state_atomic_reload_contract_mismatch_and_corruption(tmp_path):
    store = SemanticStateStore(tmp_path / "semantic_state.json", soak_id="S", contract_hash="h")
    value = store.empty(); value["last_sample_sequence"] = 7
    store.save(value)
    assert store.load()["last_sample_sequence"] == 7
    with pytest.raises(SemanticStateError):
        SemanticStateStore(store.path, soak_id="S", contract_hash="other").load()
    store.path.write_text("{", encoding="utf-8")
    with pytest.raises(SemanticStateError): store.load()


class FakeRepository:
    def __init__(self, snapshots): self.snapshots = iter(snapshots)
    def collect(self, *, updated_since=None): return next(self.snapshots)


def complete_collection(c, run):
    return SemanticCollection(NOW, (run,), (result_for(run),), candles_for(c), CollectorStatus.SUCCESS,
                              CollectorStatus.SUCCESS, CollectorStatus.SUCCESS, {"runs_results": 1, "candles": 1})


def test_monitor_startup_artifacts_restart_no_duplicate_transition_and_new_instance(tmp_path):
    c = contract(tmp_path)
    run = run_for(c)
    first = SemanticMonitor(contract=c, repository=FakeRepository([complete_collection(c, run)]), observer_instance_id="one")
    first.start(); first.sample(sample_sequence=1, recorded_at=NOW)
    lines_before = (tmp_path / "window_status.jsonl").read_text().splitlines()
    second = SemanticMonitor(contract=c, repository=FakeRepository([complete_collection(c, run)]), observer_instance_id="two")
    second.start(); second.sample(sample_sequence=2, recorded_at=NOW + timedelta(minutes=1))
    assert (tmp_path / "incident_log.jsonl").exists()
    assert (tmp_path / "semantic_snapshots.jsonl").exists()
    assert len((tmp_path / "window_status.jsonl").read_text().splitlines()) == len(lines_before)
    assert json.loads((tmp_path / "semantic_state.json").read_text())["last_sample_sequence"] == 2


def test_partial_collector_does_not_create_false_missing_or_resolve(tmp_path):
    c = contract(tmp_path)
    partial = SemanticCollection(NOW, run_status=CollectorStatus.TIMEOUT, result_status=CollectorStatus.TIMEOUT,
                                 candle_status=CollectorStatus.TIMEOUT, errors={"runs_results": "SEMANTIC_DB_TIMEOUT"})
    monitor = SemanticMonitor(contract=c, repository=FakeRepository([partial]), observer_instance_id="one")
    monitor.start(); snapshot = monitor.sample(sample_sequence=1, recorded_at=NOW)
    types = {item["incident_type"] for item in monitor.state["incidents"].values()}
    assert snapshot["status"] == "PARTIAL" and "MISSING_RUN" not in types and "SEMANTIC_DB_TIMEOUT" in types


def test_reliable_observer_heartbeat_survives_semantic_timeout_and_final_summary(tmp_path):
    c = contract(tmp_path)
    partial = SemanticCollection(NOW, run_status=CollectorStatus.TIMEOUT, result_status=CollectorStatus.TIMEOUT,
                                 candle_status=CollectorStatus.TIMEOUT, errors={"runs_results": "SEMANTIC_DB_TIMEOUT"})
    monitor = SemanticMonitor(contract=c, repository=FakeRepository([partial]), observer_instance_id="placeholder")
    observer = ReliableObserver(ObserverConfig(tmp_path, sampling_interval_seconds=.03, heartbeat_interval_seconds=.005,
                                               allowed_jitter_seconds=.03, degraded_after_failures=1), [], semantic_monitor=monitor)
    monitor.observer_instance_id = observer.instance_id
    monitor.incidents.observer_instance_id = observer.instance_id
    assert observer.run(maximum_samples=1) == 0
    heartbeat = json.loads((tmp_path / "observer_heartbeat.json").read_text())
    final = json.loads((tmp_path / "observer_final_state.json").read_text())
    assert heartbeat["semantic_monitoring_enabled"] is True
    assert heartbeat["semantic_consecutive_failures"] == 1
    assert "semantic_summary" in final
    assert audit_jsonl(tmp_path)["corrupt_lines"] == 0


def test_incident_log_created_empty_without_fake_record(tmp_path):
    observer = ReliableObserver(ObserverConfig(tmp_path, sampling_interval_seconds=.03, heartbeat_interval_seconds=.005,
                                               allowed_jitter_seconds=.03), [])
    observer.start()
    try:
        assert (tmp_path / "incident_log.jsonl").exists() and (tmp_path / "incident_log.jsonl").stat().st_size == 0
    finally:
        observer.request_stop(); observer._finalize("TEST", 0)
