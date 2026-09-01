from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine_observation.scalping_prospective_collector import (
    AppendOnlyStore,
    ANALYSIS_SEMANTICS_VERSION,
    CollectorConfig,
    DECISION_SEMANTICS_VERSION,
    HomogeneityIdentity,
    MixedRuntimeLineageWithinBoundary,
    ProspectiveCalibrationCollector,
    evaluate_outcome,
    market_universe_id,
    normalize_microstructure,
)


PARAMETERS = "trade-5m-v1-runtime-v1-87b8a882d06b3539"
SOURCE = "3aad38787a0ccb0af760a0ac7796913d965f2368"
ARTIFACT = "sha256:" + "7" * 64


class FakeOwner:
    def __init__(self, registry: dict[str, bool] | None = None) -> None:
        self.registry = registry if registry is not None else {}
        self.held = False

    def acquire(self) -> bool:
        if self.registry.get("held"):
            return False
        self.registry["held"] = self.held = True
        return True

    def active(self) -> bool:
        return self.held

    def owner_count(self) -> int:
        return int(self.registry.get("held", False))

    def release(self) -> None:
        if self.held:
            self.registry["held"] = False
        self.held = False


class FakeRepository:
    def __init__(self, rows: dict[int, list[dict]], latest: int = 1000) -> None:
        self.rows, self.latest = rows, latest
        self.query_count = 0

    def latest_boundary(self):
        self.query_count += 1
        return self.latest

    def next_boundary(self, after_ms):
        self.query_count += 1
        return min((value for value in self.rows if value > after_ms), default=None)

    def load_boundary(self, boundary_ms):
        self.query_count += 1
        return self.rows[boundary_ms]

    def load_outcome_candles(self, followups):
        self.query_count += 1
        return {item["symbol"]: [] for item in followups}


def identity(artifact: str = ARTIFACT) -> HomogeneityIdentity:
    return HomogeneityIdentity(
        profile_id="trade-5m-v1", parameter_set_id=PARAMETERS,
        runtime_source_commit=SOURCE, runtime_artifact_id=artifact,
        schema_revision="0020_paper_plan_execution_outcomes",
        market_universe_id=market_universe_id(("BTCUSDT", "ETHUSDT")),
    )


def config(root: Path, symbols=("BTCUSDT", "ETHUSDT")) -> CollectorConfig:
    return CollectorConfig(
        output_directory=root, symbols=symbols, parameter_set_id=PARAMETERS,
        runtime_source_commit=SOURCE, runtime_artifact_id=ARTIFACT,
        boundary_wait_seconds=1, max_part_bytes=400,
    )


def row(symbol: str, boundary: int, result_id: int = 1, *, candidate: bool = True,
        timestamp: int | None = None, cutoff: int | None = None,
        daemon_instance_id: str = "runtime-one") -> dict:
    timestamp = timestamp if timestamp is not None else boundary + 10
    cutoff = cutoff if cutoff is not None else boundary + 20
    setup = {
        "status": "SETUP_CANDIDATE" if candidate else "NO_SETUP",
        "symbol": symbol, "setup_type": "SCALP_BREAKOUT", "direction_hint": "BULLISH",
        "opportunity_id": f"opportunity:{symbol}:{boundary}", "quality_score": 75,
        "context": {
            "scalping": {"semantics_version": ANALYSIS_SEMANTICS_VERSION},
            "confirmation_close": 100, "atr_value": 1,
            "causal_target_candidates": [{"price": 102, "source_type": "LOCAL_5M"}],
        },
    }
    paper_context = {}
    if candidate:
        paper_context["strategy_cap_shadow_economic_snapshot"] = {
            "bid": 99.9, "ask": 100.1, "spread_bps": 20, "buy_vwap": 100.2,
            "sell_vwap": 99.8, "depth_impact_bps": 3, "safety_margin_bps": 3,
            "economic_input_timestamp_ms": timestamp,
            "decision_cutoff_timestamp_ms": cutoff,
            "maximum_age_ms": 5000, "causally_usable": True,
            "economic_input_source": "PUBLIC_TEST", "spread_source": "PUBLIC_TEST",
            "depth_impact_source": "PUBLIC_TEST", "fee_source": "CONFIG",
        }
    return {
        "run_id": f"run:{symbol}:{boundary}", "symbol": symbol, "closed_until_ms": boundary,
        "finished_at": "now", "duration_ms": 10, "pipeline_status": "COMPLETED",
        "analysis_status": "ANALYZED", "setup_status": setup["status"],
        "strategy_status": "ALLOW_RESEARCH_TRADE_PLAN" if candidate else "NO_DECISION",
        "risk_status": "REJECT", "paper_status": "NO_PLAN", "final_result": "NO_PLAN",
        "final_reason": "TEST", "error_code": None, "future_bars_used": False,
        "daemon_instance_id": daemon_instance_id, "result_id": result_id,
        "market": {"1m": {"first_open_time_ms": boundary - 60_000, "last_open_time_ms": boundary - 60_000},
                   "5m": {"first_open_time_ms": boundary - 300_000, "last_open_time_ms": boundary - 300_000},
                   "15m": {}, "1h": {}},
        "analysis": {"status": "ANALYZED", "regime": "EXPANSION", "confidence": .7,
                     "runtime_parameter_set_id": PARAMETERS},
        "setup": setup,
        "strategy": {"created_at_ms": cutoff, "strategy_score": 70,
                     "strategy_raw_score": 75, "strategy_quality_threshold": 65,
                     "runtime_parameter_set_id": PARAMETERS},
        "risk": {"risk_status": "REJECT"},
        "paper": {"created_at_ms": cutoff, "paper_status": "NO_PLAN",
                  "runtime_parameter_set_id": PARAMETERS, "paper_context": paper_context,
                  "hypothetical_entry_reference": 100, "hypothetical_stop_level": 99,
                  "hypothetical_target_level": 102, "paper_direction": "BULLISH"},
        "module_reasons": {}, "module_warnings": {}, "safety_counters": {},
        "candle_open_time_ms": boundary - 300_000, "candle_close_time_ms": boundary - 1,
        "candle_open": 99, "candle_high": 101, "candle_low": 98, "candle_close": 100,
        "candle_volume": 12, "candle_quote_volume": 1200, "candle_trades_count": 5,
        "candle_source": "rest", "candle_checksum": "abc",
    }


def candle(opened: int, low: float, high: float, close: float = 100) -> dict:
    return {"open_time_ms": opened, "close_time_ms": opened + 59_999,
            "open": 100, "high": high, "low": low, "close": close,
            "volume": 1, "quote_volume": 100, "trades_count": 1,
            "source": "test", "data_checksum": str(opened)}


def followup(**updates) -> dict:
    value = {"observation_id": "obs", "opportunity_id": "opp", "symbol": "BTCUSDT",
             "boundary_time_ms": 1_000_000, "entry_reference": 100,
             "direction": "BULLISH", "baseline_stop": 99, "baseline_target": 102,
             "ttl_ms": 60_000, "time_stop_ms": 30 * 60_000,
             "followup_due_ms": 1_000_000 + 47 * 60_000}
    value.update(updates)
    return value


def test_microstructure_accepts_decision_time_snapshot_and_rejects_future_and_stale():
    paper = {"paper_context": {"strategy_cap_shadow_economic_snapshot": {
        "bid": 10, "ask": 11, "spread_bps": 1, "economic_input_timestamp_ms": 1000,
        "decision_cutoff_timestamp_ms": 1100, "maximum_age_ms": 500, "causally_usable": True,
    }}}
    accepted = normalize_microstructure(paper, 1100)
    assert accepted["microstructure_status"] == "AVAILABLE" and accepted["best_bid"] == 10
    paper["paper_context"]["strategy_cap_shadow_economic_snapshot"]["economic_input_timestamp_ms"] = 1200
    future = normalize_microstructure(paper, 1100)
    assert future["unavailable_reason"] == "FUTURE_QUOTE_REJECTED" and future["best_bid"] is None
    paper["paper_context"]["strategy_cap_shadow_economic_snapshot"].update(
        economic_input_timestamp_ms=100, maximum_age_ms=500
    )
    stale = normalize_microstructure(paper, 1100)
    assert stale["unavailable_reason"] == "STALE_QUOTE_REJECTED" and not stale["future_leakage"]


@pytest.mark.parametrize(("candles", "expected"), [
    ([candle(1_000_000, 99.5, 100.5), candle(1_060_000, 99.5, 102.1)], "TP_FIRST"),
    ([candle(1_000_000, 99.5, 100.5), candle(1_060_000, 98.9, 101)], "SL_FIRST"),
    ([candle(1_000_000, 98.9, 102.1)], "AMBIGUOUS_BOTH_SAME_CANDLE"),
    ([candle(1_000_000, 99.5, 100.5), candle(1_060_000, 99.2, 101.5)], "TIME_EXPIRED"),
])
def test_outcome_tp_sl_ambiguity_and_expiry(candles, expected):
    value = evaluate_outcome(followup(), candles)
    assert value["baseline_outcome"] == expected
    assert value["mfe_bps"] is not None and value["mae_bps"] is not None
    assert value["intrabar_path_inferred"] is False


def test_outcome_entry_ttl_and_path_without_geometry():
    expired = evaluate_outcome(followup(), [candle(1_060_000, 99, 101)])
    assert expired["baseline_outcome"] == "ENTRY_EXPIRED"
    path = evaluate_outcome(followup(baseline_stop=None, baseline_target=None), [candle(1_000_000, 99, 101)])
    assert path["baseline_outcome"] == "PATH_CAPTURED_NO_BASELINE_GEOMETRY"


def test_append_checkpoint_restart_dedupe_rotation_and_same_segment(tmp_path):
    first = AppendOnlyStore(tmp_path, identity(), max_part_bytes=20)
    record = {"observation_id": "one", "value": 1}
    assert first.append("observations", record)
    assert not first.append("observations", record)
    first.write_checkpoint({"observation_segment_id": identity().segment_id, "last_persisted_boundary": 10})
    second = AppendOnlyStore(tmp_path, identity(), max_part_bytes=20)
    assert second.identity.segment_id == first.identity.segment_id
    assert not second.append("observations", record)
    assert second.load_checkpoint()["last_persisted_boundary"] == 10
    assert len(json.loads((tmp_path / "manifest.json").read_text())["parts"]) == 1


def test_semantic_change_starts_new_segment(tmp_path):
    first = AppendOnlyStore(tmp_path, identity())
    changed = AppendOnlyStore(tmp_path, identity("sha256:" + "8" * 64))
    assert first.identity.segment_id != changed.identity.segment_id
    assert len(json.loads((tmp_path / "manifest.json").read_text())["segments"]) == 2


def test_current_risk_contract_semantics_has_an_explicit_segment_identity():
    current = identity()
    assert current.decision_semantics_version == "scalping-risk-type-contract-v2"
    assert current.segment_id.startswith("scalping-calibration-segment-")


def test_boundary_append_checkpoint_missing_and_crash_replay_dedupe(tmp_path):
    boundary = 2_000
    rows = {boundary: [row("BTCUSDT", boundary)]}
    collector = ProspectiveCalibrationCollector(config(tmp_path), FakeRepository(rows), FakeOwner())
    assert collector.process_boundary(boundary)
    assert collector.records_written == 1 and collector.missing_records == 1
    assert collector.boundary_diagnostics == 1
    assert len(collector.store.identities["diagnostics"]) == 1
    checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    assert checkpoint["last_persisted_boundary"] == boundary
    # Simulate a crash after fsync append but before the boundary checkpoint.
    checkpoint["last_persisted_boundary"] = checkpoint["last_seen_boundary"] = 1000
    checkpoint["persisted_boundaries"] = []
    (tmp_path / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    restarted = ProspectiveCalibrationCollector(config(tmp_path), FakeRepository(rows), FakeOwner())
    assert restarted.micro_total == 1 and restarted.micro_available == 1
    assert restarted.missing_records == 1 and restarted.boundary_diagnostics == 1
    assert restarted.process_boundary(boundary)
    assert len(restarted.store.observation_ids) == 1
    assert restarted.duplicate_records == 0


def test_mixed_boundary_fails_closed_preserves_incident_and_recovers_next_clean(tmp_path):
    good = 2_000
    mixed = 3_000
    recovered = 4_000
    rows = {
        good: [row("BTCUSDT", good, 1), row("ETHUSDT", good, 2)],
        mixed: [
            row("BTCUSDT", mixed, 3),
            row("ETHUSDT", mixed, 4, daemon_instance_id="runtime-two"),
        ],
        recovered: [row("BTCUSDT", recovered, 5), row("ETHUSDT", recovered, 6)],
    }
    collector = ProspectiveCalibrationCollector(
        config(tmp_path), FakeRepository(rows), FakeOwner()
    )
    assert collector.process_boundary(good)
    good_observation_ids = set(collector.store.observation_ids)
    pending_before = set(collector.pending)

    with pytest.raises(
        MixedRuntimeLineageWithinBoundary,
        match="MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY",
    ):
        collector.process_boundary(mixed)

    checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert checkpoint["last_seen_boundary"] == mixed
    assert checkpoint["last_persisted_boundary"] == good
    assert checkpoint["excluded_boundaries"] == [mixed]
    assert set(collector.store.observation_ids) == good_observation_ids
    assert set(collector.pending) == pending_before
    assert manifest["exclusions"] == [{
        "incident_id": manifest["exclusions"][0]["incident_id"],
        "observation_segment_id": identity().segment_id,
        "boundary_time_ms": mixed,
        "reason": "MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY",
        "calibration_eligible": False,
        "raw_records_mutated": False,
    }]
    incident_part = next(
        item for item in manifest["parts"] if item["kind"] == "incidents"
    )
    incident = json.loads((tmp_path / incident_part["path"]).read_text())
    assert incident["distinct_runtime_lineage_count"] == 2
    assert incident["runtime_lineage_distribution"] == {
        "runtime-one": 1,
        "runtime-two": 1,
    }
    assert incident["exclusion"]["calibration_eligible"] is False
    assert incident["exclusion"]["outcome_followup_eligible"] is False

    restarted = ProspectiveCalibrationCollector(
        config(tmp_path), FakeRepository(rows), FakeOwner()
    )
    assert restarted.last_seen_boundary == mixed
    assert restarted.last_persisted_boundary == good
    assert restarted.runtime_daemon_instance_id == "runtime-one"
    assert restarted.process_boundary(recovered)
    final_checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    assert final_checkpoint["last_seen_boundary"] == recovered
    assert final_checkpoint["last_persisted_boundary"] == recovered
    assert final_checkpoint["excluded_boundaries"] == [mixed]
    assert len(restarted.store.observation_ids) == 4


def test_single_owner_second_denied_and_stale_recovery():
    registry: dict[str, bool] = {}
    first, second = FakeOwner(registry), FakeOwner(registry)
    assert first.acquire() and first.owner_count() == 1
    assert not second.acquire()
    first.release()
    assert second.acquire() and second.owner_count() == 1


def test_health_and_safety_are_passive(tmp_path):
    collector = ProspectiveCalibrationCollector(config(tmp_path), FakeRepository({}), FakeOwner())
    collector.owner.acquire()
    health = collector.health()
    assert health["safety"] == {"production_trading_mutations": 0, "binance_order_api_calls": 0, "parameter_promotions": 0}
    source = Path("app/engine_observation/scalping_prospective_collector.py").read_text(encoding="utf-8")
    assert "BinancePublic" not in source and "operator_control" not in source
    assert "trade-15m-v1" not in source
