from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Protocol

from app.engine_observation.observer_reliability import CollectorStatus, iso_utc
from .contracts import AcceptanceImpact, SemanticContract, Severity, WindowState
from .expected_windows import generate_expected_windows
from .incident_engine import IncidentEngine
from .models import Finding, SemanticCollection
from .serializer import append_canonical_jsonl
from .state_store import SemanticStateError, SemanticStateStore
from .validators import validate_semantics


SNAPSHOT_SCHEMA = "OBSERVER_SEMANTIC_SNAPSHOT/1.0"
WINDOW_SCHEMA = "OBSERVER_SEMANTIC_WINDOW/1.0"


class SemanticRepository(Protocol):
    def collect(self, *, updated_since: datetime | None = None) -> SemanticCollection: ...


class SemanticMonitor:
    def __init__(self, *, contract: SemanticContract, repository: SemanticRepository, observer_instance_id: str,
                 artifact_directory: Path | None = None) -> None:
        self.contract, self.repository, self.observer_instance_id = contract, repository, observer_instance_id
        self.root = (artifact_directory or contract.soak_directory).resolve()
        self.state_store = SemanticStateStore(self.root / "semantic_state.json", soak_id=contract.soak_id, contract_hash=contract.contract_hash)
        self.incidents = IncidentEngine(self.root / "incident_log.jsonl", soak_id=contract.soak_id, observer_instance_id=observer_instance_id)
        self.state: dict[str, Any] = {}
        self._lock = RLock()
        self._health = {"semantic_monitoring_enabled": True, "semantic_last_success_at_utc": None,
                        "semantic_last_db_clock_utc": None, "semantic_consecutive_failures": 0,
                        "semantic_open_incidents": 0, "semantic_blocking_incidents": 0,
                        "semantic_last_error_code": None, "semantic_state_version": "OBSERVER_SEMANTIC_STATE/1.0"}

    def start(self) -> None:
        try:
            self.state = self.state_store.load()
        except SemanticStateError as exc:
            temporary = self.state_store.empty()
            self.incidents.reconcile([Finding("SEMANTIC_STATE_CORRUPTION", Severity.CRITICAL, AcceptanceImpact.BLOCKING,
                                                reason_code="CONTRACT_MISMATCH_OR_CORRUPTION", evidence={"error_type": type(exc).__name__})],
                                     temporary, datetime.now(timezone.utc), complete_snapshot=False)
            raise

    @property
    def health(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._health)

    def _collector_findings(self, collection: SemanticCollection) -> list[Finding]:
        findings = []
        statuses = {"run": collection.run_status, "result": collection.result_status, "candle": collection.candle_status}
        for name, status in statuses.items():
            if status == CollectorStatus.SUCCESS:
                continue
            kind = "SEMANTIC_DB_TIMEOUT" if status == CollectorStatus.TIMEOUT else "SEMANTIC_DB_UNAVAILABLE"
            findings.append(Finding(kind, Severity.ERROR, AcceptanceImpact.REVIEW, reason_code=f"{name.upper()}_{status}",
                                    stable_sub_key=name, evidence={"collector": name, "status": status}))
        return findings

    def sample(self, *, sample_sequence: int, recorded_at: datetime) -> dict[str, Any]:
        updated = self.state.get("last_processed_run_updated_at")
        watermark = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else None
        collection = self.repository.collect(updated_since=watermark)
        complete = collection.complete and collection.database_now is not None
        findings = self._collector_findings(collection)
        verdicts = []
        expected = ()
        if collection.database_now is not None and collection.run_status == CollectorStatus.SUCCESS:
            expected = generate_expected_windows(self.contract, collection.database_now)
        if complete:
            verdicts, semantic_findings = validate_semantics(
                contract=self.contract, database_now=collection.database_now, expected=expected, runs=collection.runs,
                results=collection.results, candles=collection.candles, previous_run_ids=self.state.get("known_window_run_ids", {}),
                previous_states=self.state.get("known_window_states", {}))
            findings.extend(semantic_findings)
        emitted = self.incidents.reconcile(findings, self.state, collection.database_now or recorded_at, complete_snapshot=complete)
        known_states = self.state.setdefault("known_window_states", {})
        known_run_ids = self.state.setdefault("known_window_run_ids", {})
        for verdict in verdicts:
            key = "|".join(map(str, verdict.key))
            previous = known_states.get(key)
            current = {"state": verdict.state, "run_id": verdict.run_id, "diagnostic_hash": verdict.diagnostic_hash,
                       "attempt_count": verdict.evidence.get("attempt_count")}
            if previous != current:
                append_canonical_jsonl(self.root / "window_status.jsonl", {
                    "schema_version": WINDOW_SCHEMA, "observer_instance_id": self.observer_instance_id,
                    "sample_sequence": sample_sequence, "recorded_at_utc": iso_utc(recorded_at), "soak_id": self.contract.soak_id,
                    "symbol": verdict.key[0], "timeframe": verdict.key[1], "closed_until_ms": verdict.key[2],
                    "previous_state": previous.get("state") if previous else None, "state": verdict.state,
                    "run_id": verdict.run_id, "diagnostic_hash": verdict.diagnostic_hash, "evidence": verdict.evidence,
                })
            known_states[key] = current
            if verdict.run_id:
                known_run_ids[key] = verdict.run_id
        counts = Counter(value["state"] for value in known_states.values())
        incident_values = list(self.state.get("incidents", {}).values())
        open_incidents = [item for item in incident_values if item.get("state") != "RESOLVED"]
        blocking = [item for item in open_incidents if item.get("acceptance_impact") == "BLOCKING"]
        collector_statuses = {"runs": collection.run_status, "results": collection.result_status, "candles": collection.candle_status}
        snapshot = {
            "schema_version": SNAPSHOT_SCHEMA, "observer_instance_id": self.observer_instance_id,
            "sample_sequence": sample_sequence, "soak_id": self.contract.soak_id, "recorded_at_utc": iso_utc(recorded_at),
            "database_now_utc": iso_utc(collection.database_now), "status": "SUCCESS" if complete else "PARTIAL",
            "expected_due_windows": sum(1 for item in expected if item.due),
            "completed_exactly_once": counts[WindowState.RUN_COMPLETED], "waiting_retryable": counts[WindowState.RUN_WAITING_RETRYABLE],
            "skipped": counts[WindowState.RUN_SKIPPED], "failed": counts[WindowState.RUN_FAILED],
            "missing": counts[WindowState.DUE_WAITING_FOR_RUN], "duplicate_windows": counts[WindowState.RUN_DUPLICATE],
            "completed_without_result": sum(1 for item in open_incidents if item["incident_type"] == "COMPLETED_WITHOUT_RESULT"),
            "completed_with_multiple_results": sum(1 for item in open_incidents if item["incident_type"] == "COMPLETED_WITH_MULTIPLE_RESULTS"),
            "orphan_results": sum(1 for item in open_incidents if item["incident_type"] == "ORPHAN_RESULT"),
            "duplicate_results": sum(1 for item in open_incidents if item["incident_type"] == "DUPLICATE_RESULT"),
            "market_data_missing": sum(1 for item in open_incidents if item["incident_type"] == "MISSING_CANDLE"),
            "duplicate_candles": sum(1 for item in open_incidents if item["incident_type"] == "DUPLICATE_CANDLE"),
            "persistent_gaps": sum(1 for item in open_incidents if item["incident_type"] == "PERSISTENT_MARKET_DATA_GAP"),
            "open_incidents": len(open_incidents), "blocking_incidents": len(blocking),
            "resolved_incidents": len(self.state.get("resolved_incident_ids", [])), "collector_statuses": collector_statuses,
            "query_durations_ms": collection.query_durations_ms, "collector_errors": collection.errors,
        }
        append_canonical_jsonl(self.root / "semantic_snapshots.jsonl", snapshot)
        now_text = iso_utc(recorded_at)
        self.state.update({"last_sample_sequence": sample_sequence, "updated_at_utc": now_text})
        if complete:
            self.state["last_successful_db_clock"] = iso_utc(collection.database_now)
            if collection.runs:
                latest = max((item.updated_at for item in collection.runs if item.updated_at is not None), default=None)
                self.state["last_processed_run_updated_at"] = iso_utc(latest)
                self.state["last_processed_closed_until_ms"] = max(item.closed_until_ms for item in collection.runs)
        try:
            self.state_store.save(self.state)
        except Exception:
            self.incidents.reconcile([Finding("SEMANTIC_CHECKPOINT_WRITE_FAILED", Severity.CRITICAL, AcceptanceImpact.BLOCKING,
                                                reason_code="ATOMIC_STATE_WRITE_FAILED")], self.state, recorded_at, complete_snapshot=False)
            raise
        with self._lock:
            if complete:
                self._health["semantic_last_success_at_utc"] = now_text
                self._health["semantic_last_db_clock_utc"] = iso_utc(collection.database_now)
                self._health["semantic_consecutive_failures"] = 0
                self._health["semantic_last_error_code"] = None
            else:
                self._health["semantic_consecutive_failures"] += 1
                self._health["semantic_last_error_code"] = next(iter(collection.errors.values()), "SEMANTIC_PARTIAL")
            self._health["semantic_open_incidents"] = len(open_incidents)
            self._health["semantic_blocking_incidents"] = len(blocking)
        return snapshot

    def final_summary(self) -> dict[str, Any]:
        incidents = list(self.state.get("incidents", {}).values())
        return {"enabled": True, "soak_id": self.contract.soak_id, "contract_hash": self.contract.contract_hash,
                "last_sample_sequence": self.state.get("last_sample_sequence", 0),
                "known_windows": len(self.state.get("known_window_states", {})),
                "open_incidents": sum(item.get("state") != "RESOLVED" for item in incidents),
                "blocking_incidents": sum(item.get("state") != "RESOLVED" and item.get("acceptance_impact") == "BLOCKING" for item in incidents),
                "resolved_incidents": len(self.state.get("resolved_incident_ids", []))}
