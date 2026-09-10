from __future__ import annotations

import json

import pytest

from traders_ml.parameter_sweep.artifact_v2 import (
    ArtifactSizeBudgetExceeded, compact_result, compact_trade,
    enforce_size_budget, iter_results, make_market_path_ref,
    migrate_v1_run, recursive_inline_market_path_count, resolve_market_path,
)


def _legacy_result():
    path = [{"close_time_ms": 60_000, "open": 100, "high": 102, "low": 99, "close": 101}]
    return {
        "result_index": 0, "config_hash": "c1", "stage": "SENSITIVITY",
        "result_status": "ACCEPTED", "parameters": {"stop_max_bps": 50},
        "INPUT_ROWS": 4,
        "validation": {
            "trade_count": 1, "wins": 1, "losses": 0, "win_rate": 1.0,
            "gross_pnl": 2.0, "net_pnl": 1.0, "net_expectancy_per_trade": 1.0,
            "profit_factor": 2.0, "max_drawdown": 0.0,
            "symbol_distribution": {"BTCUSDT": 1}, "setup_distribution": {"BREAKOUT": 1},
            "funnel": {"PASSED_ROWS": 1, "REJECT_RR": 3},
            "trades": [{"symbol": "BTCUSDT", "opened_at_ms": 0, "closed_at_ms": 60_000, "market_path_1m": path}],
        },
    }


def test_compact_result_has_v2_semantics_and_no_inline_market_path():
    row = compact_result(_legacy_result(), baseline_config_hash="base", research_config_hash="research")
    assert row["artifact_schema_version"] == 2
    assert row["evaluation_status"] == "ACCEPTED"
    assert row["performance_class"] != "ACCEPTED"
    assert recursive_inline_market_path_count(row) == 0
    assert "validation" not in row and "trades" not in row


def test_market_path_reference_resolves_semantically_exact():
    legacy = _legacy_result()["validation"]["trades"][0]
    reference = make_market_path_ref("manifest", legacy, legacy["market_path_1m"])
    compact = compact_trade(legacy, "manifest")
    assert "market_path_1m" not in compact
    assert compact["market_path_ref"] == reference
    assert resolve_market_path(reference, [{"symbol": "BTCUSDT", "market_path_1m": legacy["market_path_1m"]}]) == legacy["market_path_1m"]


def test_v1_reader_and_non_destructive_atomic_migration(tmp_path):
    source, target = tmp_path / "v1", tmp_path / "v2"
    source.mkdir()
    original = json.dumps(_legacy_result(), sort_keys=True) + "\n"
    (source / "RESULTS.jsonl").write_text(original, encoding="utf-8")
    (source / "DATASET_MANIFEST.json").write_text("{}", encoding="utf-8")
    (source / "DATASET_SNAPSHOT.json").write_text("[]", encoding="utf-8")
    assert list(iter_results(source / "RESULTS.jsonl"))[0]["artifact_schema_version"] == 2
    dry = migrate_v1_run(source, target, dry_run=True)
    assert dry.source_rows == dry.target_rows == 1 and not target.exists()
    report = migrate_v1_run(source, target)
    assert report.inline_market_path_count == 0
    assert (source / "RESULTS.jsonl").read_text(encoding="utf-8") == original
    assert {"RUN_MANIFEST.json", "RESULTS.jsonl", "RESULTS.csv", "TOP_CONFIGS.json", "CHECKPOINT.json", "REPORT.md"} <= {p.name for p in target.iterdir()}


def test_hard_size_budget_guard(tmp_path, monkeypatch):
    (tmp_path / "RESULTS.jsonl").write_bytes(b"x" * 20)
    from traders_ml.parameter_sweep import artifact_v2
    from types import SimpleNamespace
    policy = artifact_v2.RESEARCH_PARAMETERS.artifact.model_copy(update={"hard_total_bytes": 10})
    monkeypatch.setattr(artifact_v2, "RESEARCH_PARAMETERS", SimpleNamespace(artifact=policy))
    with pytest.raises(ArtifactSizeBudgetExceeded, match="ARTIFACT_SIZE_BUDGET_EXCEEDED"):
        enforce_size_budget(tmp_path)
