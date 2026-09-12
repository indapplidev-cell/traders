from __future__ import annotations

from datetime import datetime, timedelta, timezone

from traders_ml.parameter_sweep.separability import (
    FEATURE_SPECS, SOURCE_TYPE, build_activity, build_registry,
    categorical_analysis, construct_dataset, cyclic_distance, handoff_artifact,
    interaction_screen, label_net_pnl, numeric_analysis, rank_features,
    run_separability, stability_analysis,
)


def _source(index: int, pnl: float, *, symbol: str = "DOGEUSDT", value: float | None = None):
    boundary = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(hours=index)
    created = int((boundary - timedelta(seconds=10)).timestamp() * 1000)
    feature_value = value if value is not None else float(index)
    setup = {
        "setup_id": f"candidate-{index}", "created_at_ms": created,
        "closed_until_ms": created - 1000, "future_bars_used": False,
        "quality_score": feature_value,
        "quality_diagnostics": {"structural_score": feature_value, "confirmation_score": 30, "context_score": feature_value, "has_conflict": False},
        "source_confidence": feature_value, "setup_type": "A" if index % 2 else "B",
        "source_regime": "TREND", "source_impulse_phase": "IMPULSE",
        "setup_quality": "GOOD", "confirmation_state": "CONFIRMED",
        "diagnostics": {"liquidity_presence": True},
    }
    strategy = {"created_at_ms": created, "closed_until_ms": created - 1000, "future_bars_used": False, "strategy_score": feature_value, "strategy_quality": "GOOD", "strategy_cap_applied": False}
    risk = {"created_at_ms": created, "closed_until_ms": created - 1000, "future_bars_used": False, "risk_score": feature_value, "risk_level": "LOW", "risk_pre_approved": True}
    paper = {
        "created_at_ms": created, "closed_until_ms": created - 1000, "future_bars_used": False,
        "paper_plan_id": f"plan-{index}", "plan_score": feature_value,
        "planned_rr": feature_value, "hypothetical_entry_reference": 100,
        "hypothetical_stop_level": 99 - feature_value / 100,
        "hypothetical_target_level": 101 + feature_value / 100,
        "entry_reference_source": "CLOSE", "stop_source": "ATR", "target_source": "STRUCTURE",
        "paper_context": {"causal_primitives": {"atr_value": 1, "volatility_buffer": feature_value}},
    }
    return {
        "position_id": f"trade-{index}", "symbol": symbol, "side": "LONG" if index % 2 else "SHORT",
        "opened_at": boundary, "closed_at": boundary + timedelta(minutes=5), "realized_pnl": pnl,
        "command_id": f"command-{index}", "pipeline_run_id": f"run-{index}",
        "risk_decision_id": f"approval-{index}", "setup_id": f"candidate-{index}",
        "trade_profile_id": "trade-5m-v2", "command_created_at": boundary - timedelta(seconds=5),
        "closed_until_ms": created - 1000, "future_bars_used": False,
        "setup_payload_json": setup, "strategy_payload_json": strategy,
        "risk_payload_json": risk, "paper_payload_json": paper,
        "source_type": SOURCE_TYPE,
    }


def _analyze(rows):
    dataset, diagnostics = construct_dataset(rows, symbol="DOGEUSDT")
    registry = build_registry(dataset)
    activity = build_activity(registry, len(dataset))
    numeric = numeric_analysis(dataset, registry, activity)
    categorical = categorical_analysis(dataset, registry, activity)
    stability = stability_analysis(dataset, [*numeric, *categorical])
    ranking = rank_features(registry, numeric, categorical, stability, len(dataset))
    return dataset, diagnostics, registry, activity, numeric, categorical, stability, ranking


def test_one_trade_one_row_labels_symbol_and_reconstruction_rejection():
    rows = [_source(1, 1), _source(1, 1), _source(2, -1), _source(3, 0)]
    rows[1] = dict(rows[1])
    cross = _source(4, 1, symbol="ETHUSDT")
    reconstructed = dict(_source(5, 1), source_type="RECONSTRUCTED_OBSERVATION")
    dataset, diagnostics = construct_dataset([*rows, cross, reconstructed], symbol="DOGEUSDT")
    assert [row["label"] for row in dataset] == ["WIN", "LOSS", "NEUTRAL"]
    assert len({row["trade_id"] for row in dataset}) == len(dataset) == 3
    assert diagnostics == {"source_rows": 6, "duplicate_trade_rows": 1, "cross_symbol_rows": 1, "future_leakage_violations": 0, "reconstructed_rows_rejected": 1}
    assert label_net_pnl(1) == "WIN" and label_net_pnl(-1) == "LOSS" and label_net_pnl(0) == "NEUTRAL"


def test_future_feature_is_rejected_and_missing_is_not_imputed():
    row = _source(1, 1)
    row["setup_payload_json"]["created_at_ms"] = int((row["opened_at"] + timedelta(seconds=1)).timestamp() * 1000)
    dataset, diagnostics = construct_dataset([row], symbol="DOGEUSDT")
    assert dataset == []
    assert diagnostics["future_leakage_violations"] == 1
    clean, _ = construct_dataset([_source(2, -1)], symbol="DOGEUSDT")
    assert clean[0]["features"]["momentum_score"] is None


def test_numeric_and_categorical_direction_constant_and_handoff_forbids_ranges():
    rows = [_source(i, 1 if i >= 5 else -1, value=float(i)) for i in range(10)]
    dataset, _, registry, activity, numeric, categorical, stability, ranking = _analyze(rows)
    quality = next(row for row in numeric if row["feature"] == "setup_quality_score")
    assert quality["direction"] == "WINNERS_HIGHER" and quality["rank_auc"] == 1
    setup = next(row for row in categorical if row["feature"] == "setup_type")
    assert setup["direction"] == "CATEGORY_DEPENDENT"
    conflict = next(row for row in activity if row["feature"] == "has_conflict")
    assert conflict["activity_status"] == "CONSTANT"
    handoff = handoff_artifact(ranking, numeric, categorical)
    def keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()
    assert not keys(handoff) & {"recommended_min", "recommended_max", "candidate_range", "search_grid", "threshold", "promotion_value"}
    interactions = interaction_screen(dataset, ranking, top_n=3)
    assert len(interactions) <= 3


def test_utc_hour_is_cyclic_and_cannot_be_a_linear_range_or_interaction():
    rows = [_source(i, 1 if i >= 5 else -1) for i in range(10)]
    dataset, _, registry, activity, numeric, categorical, stability, ranking = _analyze(rows)
    utc_registry = next(row for row in registry if row["feature_name"] == "utc_hour")
    utc_ranking = next(row for row in ranking if row["feature"] == "utc_hour")
    utc_handoff = next(
        row for row in handoff_artifact(ranking, numeric, categorical)["features"]
        if row["feature"] == "utc_hour"
    )
    assert utc_registry["data_type"] == utc_registry["semantic_type"] == "CYCLIC"
    assert utc_registry["analysis_method"] == "CYCLIC_CATEGORY_WIN_LOSS_LIFT"
    assert utc_handoff["semantic_type"] == "CYCLIC"
    assert utc_handoff["period"] == 24
    assert utc_handoff["do_not_generate_linear_min_max_range"] is True
    assert utc_ranking["do_not_generate_linear_min_max_range"] is True
    assert cyclic_distance(23, 0, period=24) == 1
    assert cyclic_distance(0, 12, period=24) == 12
    assert all(
        "utc_hour" not in {row["feature_a"], row["feature_b"]}
        for row in interaction_screen(dataset, ranking, top_n=len(ranking))
    )


class _UnusedDatabase:
    pass


def test_run_artifacts_are_complete_and_deterministic(tmp_path):
    rows = [_source(i, 1 if i >= 5 else -1) for i in range(10)]
    first = tmp_path / "first"
    second = tmp_path / "second"
    one = run_separability(database=_UnusedDatabase(), symbol="DOGEUSDT", output=first, source_rows=rows)
    two = run_separability(database=_UnusedDatabase(), symbol="DOGEUSDT", output=second, source_rows=rows)
    required = {
        "SEPARABILITY_DATASET.jsonl", "SEPARABILITY_DATASET_MANIFEST.json", "FEATURE_REGISTRY.json",
        "NUMERIC_SEPARABILITY.json", "CATEGORICAL_SEPARABILITY.json", "FEATURE_ACTIVITY.json",
        "INTERACTION_SCREEN.json", "FEATURE_RANKING.json", "SEPARABILITY_HANDOFF.json", "REPORT.md",
    }
    assert required == {path.name for path in first.iterdir()}
    assert one["manifest"]["dataset_sha256"] == two["manifest"]["dataset_sha256"]
    assert (first / "FEATURE_RANKING.json").read_bytes() == (second / "FEATURE_RANKING.json").read_bytes()
    assert (first / "SEPARABILITY_HANDOFF.json").read_bytes() == (second / "SEPARABILITY_HANDOFF.json").read_bytes()
    assert one["manifest"]["ranges_generated"] is False
    assert one["manifest"]["search_executed"] is False
    assert one["manifest"]["holdout_opened"] is False


def test_low_and_sufficient_sample_status_mapping(tmp_path):
    low = [_source(i, 1 if i < 3 else -1) for i in range(10)]
    sufficient = [_source(i, 1 if i < 10 else -1) for i in range(20)]
    low_result = run_separability(
        database=_UnusedDatabase(), symbol="DOGEUSDT", output=tmp_path / "low",
        source_rows=low,
    )
    sufficient_result = run_separability(
        database=_UnusedDatabase(), symbol="DOGEUSDT", output=tmp_path / "sufficient",
        source_rows=sufficient,
    )
    assert low_result["manifest"]["sample_adequacy"] == "DESCRIPTIVE_ONLY"
    assert low_result["manifest"]["final_status"] == "PASS_LIMITED_SAMPLE"
    assert sufficient_result["manifest"]["sample_adequacy"] == "USABLE"
    assert sufficient_result["manifest"]["final_status"] == "PASS"


def test_source_history_span_is_independent_from_three_day_trade_sample(tmp_path):
    source_start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    source_history = [
        {"closed_until_ms": int(source_start.timestamp() * 1000)},
        {"closed_until_ms": int((source_start + timedelta(days=10)).timestamp() * 1000)},
    ]
    trade_start = source_start + timedelta(days=2)
    rows = [_source(i, 1 if i < 3 else -1) for i in range(10)]
    for index, row in enumerate(rows):
        row["opened_at"] = trade_start + timedelta(hours=index * 8)
        row["closed_at"] = row["opened_at"] + timedelta(minutes=5)
    rows[-1]["closed_at"] = trade_start + timedelta(days=3)
    result = run_separability(
        database=_UnusedDatabase(), symbol="DOGEUSDT", output=tmp_path / "spans",
        source_rows=rows, source_history_rows=source_history,
    )
    manifest = result["manifest"]
    assert manifest["source_history_actual_days"] == 10
    assert manifest["trade_sample_span_days"] == 3
    assert manifest["source_history_start"] != manifest["trade_sample_start"]
    assert manifest["source_history_end"] != manifest["trade_sample_end"]
    assert manifest["source_history_selection_mode"] == "DEEPEST_AVAILABLE_CLEAN_PERSISTED_SELECTED_SYMBOL_HISTORY"


def test_source_history_and_trade_sample_spans_are_independent(tmp_path):
    trades = [_source(24 + index * 18, 1 if index < 3 else -1) for index in range(5)]
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    history = [
        {"closed_until_ms": int((start + timedelta(days=day)).timestamp() * 1000)}
        for day in range(11)
    ]
    result = run_separability(
        database=_UnusedDatabase(), symbol="DOGEUSDT", output=tmp_path / "spans",
        source_rows=trades, source_history_rows=history,
    )["manifest"]
    assert result["source_history_actual_days"] == 10
    assert result["trade_sample_span_days"] == 3 + 5 / (24 * 60)
    assert result["source_history_actual_days"] != result["trade_sample_span_days"]
    assert result["source_history_rows"] == 11
    assert result["source_history_selection_mode"] == "DEEPEST_AVAILABLE_CLEAN_PERSISTED_SELECTED_SYMBOL_HISTORY"
    assert result["reconstructed_rows_used"] == 0
