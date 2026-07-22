from __future__ import annotations

import json

from app.engine_observation.observer_reliability import (
    JsonFileCollector,
    ObserverConfig,
    ReliableObserver,
    atomic_write_json,
    audit_jsonl,
)


class TransitioningHealthCollector:
    name = "service_health"

    def __init__(self, path, states):
        self.path = path
        self.states = iter(states)
        self.delegate = JsonFileCollector(self.name, {"online_orchestrator": path})

    def collect(self):
        atomic_write_json(self.path, next(self.states))
        return self.delegate.collect()


def test_observer_preserves_freshness_waiting_to_ready_contract(tmp_path):
    run_id = "orchestrator:combined-canary"
    health_path = tmp_path / "latest_health.json"
    states = [
        {
            "run_id": run_id,
            "status": "WAITING_FOR_REQUIRED_BOUNDARY",
            "freshness_classification": "WAITING_RETRYABLE",
            "waiting_timeframes": ["1m"],
            "freshness_reasons": ["1m:STATUS_RECOVERING"],
            "public_status": "RECOVERING",
            "result_count": 0,
        },
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "freshness_classification": "READY",
            "waiting_timeframes": [],
            "freshness_reasons": [],
            "public_status": "OK",
            "result_count": 1,
        },
    ]
    observer = ReliableObserver(
        ObserverConfig(
            tmp_path / "observer",
            sampling_interval_seconds=0.03,
            heartbeat_interval_seconds=0.005,
            allowed_jitter_seconds=0.03,
        ),
        [TransitioningHealthCollector(health_path, states)],
    )

    assert observer.run(maximum_samples=2) == 0

    observations = [
        json.loads(line)
        for line in (tmp_path / "observer" / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    samples = [item for item in observations if item["record_type"] == "ObserverSample"]
    health = [item["collectors"][0]["data"]["values"]["online_orchestrator"] for item in samples]
    assert [item["run_id"] for item in health] == [run_id, run_id]
    assert health[0]["freshness_classification"] == "WAITING_RETRYABLE"
    assert health[0]["waiting_timeframes"] == ["1m"]
    assert health[0]["public_status"] == "RECOVERING"
    assert health[1]["freshness_classification"] == "READY"
    assert health[1]["waiting_timeframes"] == []
    assert health[1]["result_count"] == 1
    assert sum(item["result_count"] for item in health) == 1
    assert len({(item["observer_instance_id"], item["sample_sequence"]) for item in samples}) == 2
    assert audit_jsonl(tmp_path / "observer")["corrupt_lines"] == 0
    assert audit_jsonl(tmp_path / "observer")["duplicate_identities"] == 0
    heartbeat_states = {
        json.loads(line)["state"]
        for line in (tmp_path / "observer" / "heartbeat_history.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert {"RUNNING", "STOPPING", "STOPPED"}.issubset(heartbeat_states)
