import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from sqlalchemy import text

from app.research.scalping_v2_parameter_sweep import (
    ParameterSweepSearchPlanner, ReadOnlyResearchDatabase, SweepExpectedError,
    _baseline_control, _candidate_config, _candidate_indices,
    _config_from_index, _conditional_variants, _dataset_coverage,
    _gate_funnel, _shadow_observation, _stale_policy,
    resolve_database_binding, run,
)


def _time_stop_space() -> dict[str, list[object]]:
    return {
        "soft_timeout_seconds": [600], "hard_timeout_seconds": [900],
        "min_target_progress_at_soft_timeout": [.2],
        "min_mfe_bps_at_soft_timeout": [None],
        "min_remaining_ev_r_at_soft_timeout": [0],
        "extension_seconds": [300], "max_extensions": [1],
        "break_even_activation_target_progress": [.5],
        "net_break_even_protection_enabled": [True],
    }


def _rows() -> list[dict[str, object]]:
    rows = []
    for index, split in enumerate((
        "CALIBRATION", "CALIBRATION", "VALIDATION", "VALIDATION",
        "HOLDOUT", "HOLDOUT",
    )):
        opened = index * 2_000_000
        rows.append({
            "position_id": f"p{index}", "command_id": f"c{index}",
            "profile_id": "trade-5m-v2", "split": split,
            "opened_at_ms": opened, "closed_at_ms": opened + 1_200_000,
            "expected_ev_r": .2, "ev_reserve": .3, "net_edge_bps": 20,
            "probability_sample_size": 50, "stop_distance_bps": 40,
            "target_distance_bps": 80, "causal_reset_conditions": 1,
            "one_min_confirmation_count": 1,
            "net_pnl": 1 if index % 2 == 0 else -.5, "gross_pnl": 1.2,
            "fees": .2, "exit_reason": "TARGET" if index % 2 == 0 else "STOP",
            "holding_time_ms": 1_200_000, "mae": 2, "mfe": 4,
            "symbol": "BTCUSDT", "direction": "LONG",
            "setup_type": "BREAKOUT", "session": "UTC",
            "entry_price": 100, "quantity": 1, "stop_price": 99,
            "exit_price": 101, "target_price": 102,
            "entry_fee_incurred": .09, "exit_fee_incurred": .11,
            "time_stop_observations": [{
                "evaluation_time_ms": opened + 600_000,
                "evaluation_closed_until_ms": opened + 600_000,
                "current_price": 100.1, "highs": [100.2], "lows": [99.9],
                "exit_commission_bps": 9, "spread_bps": 2,
                "slippage_bps": 2, "adverse_exit_reserve_bps": 3,
                "setup_valid": False, "momentum_valid": False,
                "remaining_ev_r": 0, "historical_cost_evidence": True,
                "commission_source": "HISTORICAL_BINANCE_ACCOUNT_COMMISSION",
            }],
            "causal_later_candidates": [{
                "candidate_id": f"later-{index}",
                "candidate_time_ms": opened + 700_000,
            }],
        })
    return rows


def _search(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    space = {
        "min_positive_ev_r": [0, .1], "min_ev_reserve_r": [0],
        "min_net_edge_bps": [1], "bucket_min_sample": [20],
        "probability_confidence_level": [.95], "prior_alpha": [1],
        "prior_beta": [1], "adverse_fill_reserve_bps": [3],
        "entry_slippage_bps": [2], "stop_max_bps": [50],
        "target_min_bps": [45], "causal_reset_min_conditions": [1],
        "entry_refinement_1m_confirmation_count": [1], **_time_stop_space(),
    }
    search = {
        "schema_version": 2, "seed": 1, "dataset": str(dataset),
        "output_root": str(tmp_path / "artifacts"),
        "minimum_samples": {"calibration": 2, "validation": 2, "holdout": 2},
        "search_space": space,
    }
    search_path = tmp_path / "search.yaml"
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    return search_path


def test_two_variant_smoke_reuses_time_stop_evaluator_and_has_zero_mutation(tmp_path):
    output = run(_search(tmp_path, _rows()), run_id="smoke")
    expected = {
        "RUN_CONFIG.yaml", "RESULTS.csv", "RESULTS.json", "TOP_CONFIGS.json",
        "REJECTED_CONFIGS.json", "REPORT.md", "PREFLIGHT.json",
        "SEARCH_PLAN.json", "CHECKPOINT.json", "RESULTS.jsonl",
    }
    assert {path.name for path in output.iterdir()} == expected
    results = json.loads((output / "RESULTS.json").read_text())
    assert len(results) == 2
    validation = results[0]["validation"]
    assert validation["soft_timeout_count"] == 2
    assert validation["time_stop_exit_count"] == 2
    assert validation["stale_position_seconds_saved"] == 1200
    assert validation["candidates_blocked_while_position_open"] == 2
    assert validation["hypothetical_candidates_unblocked_after_stale_exit"] == 2
    assert validation["replay_status"] == {"REPLAYABLE": 2}
    report = (output / "REPORT.md").read_text(encoding="utf-8")
    assert "TIME-STOP ANALYSIS" in report
    assert "Holdout is evaluated for reporting only" in report
    run_config = yaml.safe_load((output / "RUN_CONFIG.yaml").read_text())
    assert run_config["time_stop_policy_schema"] == "StalePositionPolicyParameters"
    assert run_config["production_mutations"] == 0
    assert run_config["production_config_writes"] == 0
    assert run_config["approvals_created"] == 0
    assert run_config["commands_created"] == 0
    assert run_config["positions_created"] == 0
    assert run_config["binance_order_api_calls"] == 0
    preflight = json.loads((output / "PREFLIGHT.json").read_text())
    assert preflight["PARAMETER_SWEEP_PREFLIGHT"] == "PASS"
    assert preflight["PRODUCTION_MUTATION_GUARD_ACTIVE"] is True
    assert preflight["SECRET_OUTPUT"] == 0


def test_invalid_timeout_relationship_is_not_generated(tmp_path):
    search_path = _search(tmp_path, _rows())
    search = yaml.safe_load(search_path.read_text())
    search["search_space"]["hard_timeout_seconds"] = [600]
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    with pytest.raises(SweepExpectedError, match="invalid research search space"):
        run(search_path, run_id="invalid", max_configs=1)


def test_missing_historical_cost_evidence_is_unreplayable_without_invention(tmp_path):
    rows = _rows()
    rows[2]["time_stop_observations"][0]["historical_cost_evidence"] = False
    rows[3]["time_stop_observations"] = []
    output = run(_search(tmp_path, rows), run_id="missing", max_configs=1)
    result = json.loads((output / "RESULTS.json").read_text())[0]
    assert result["validation"]["replay_status"] == {
        "UNREPLAYABLE_MISSING_COST_TIMELINE": 1,
        "UNREPLAYABLE_MISSING_MARKET_TIMELINE": 1,
    }
    assert result["validation"]["time_stop_exit_count"] == 0


def test_search_schema_requires_every_runtime_time_stop_dimension(tmp_path):
    search_path = _search(tmp_path, _rows())
    search = yaml.safe_load(search_path.read_text())
    del search["search_space"]["min_mfe_bps_at_soft_timeout"]
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid research search space"):
        run(search_path, run_id="missing-dimension")


@pytest.mark.parametrize("overrides", (
    {"hard_timeout_seconds": 600},
    {"extension_seconds": 0, "max_extensions": 1},
    {"max_extensions": -1},
    {"min_target_progress_at_soft_timeout": 1.1},
    {"break_even_activation_target_progress": -0.1},
    {"min_mfe_bps_at_soft_timeout": -1},
    {"min_remaining_ev_r_at_soft_timeout": -0.1},
))
def test_runtime_schema_rejects_invalid_or_contradictory_time_stop_configs(overrides):
    config = {name: values[0] for name, values in _time_stop_space().items()}
    config.update(overrides)
    with pytest.raises(ValueError):
        _stale_policy(config)


def _binding(path: Path) -> None:
    path.write_text(
        "TRADERS_READONLY_API_DATABASE_URL="
        "postgresql+psycopg://readonly:read-secret@postgres:5432/traders_ml\n"
        "TRADERS_PAPER_RUNTIME_DATABASE_URL="
        "postgresql+psycopg://runtime:runtime-secret@127.0.0.1:5433/traders_ml\n",
        encoding="utf-8",
    )


def test_project_binding_resolves_without_database_url_and_reuses_host_endpoint(tmp_path):
    protected = tmp_path / ".env.production.local"
    _binding(protected)
    binding = resolve_database_binding(protected_path=protected, environment={})
    assert binding.source == "PROJECT_PROTECTED_BINDING"
    assert binding.url.username == "readonly"
    assert binding.url.host == "127.0.0.1"
    assert binding.url.port == 5433


def test_resolution_precedence_explicit_then_project_then_environment(tmp_path):
    protected = tmp_path / ".env.production.local"
    _binding(protected)
    explicit = resolve_database_binding(
        explicit_url="postgresql://explicit:x@localhost:5434/dev",
        protected_path=protected, environment={"DATABASE_URL": "postgresql://env:x@localhost/env"},
    )
    assert explicit.source == "EXPLICIT_CLI_OVERRIDE"
    assert explicit.url.username == "explicit"
    project = resolve_database_binding(
        protected_path=protected,
        environment={"DATABASE_URL": "postgresql://env:x@localhost/env"},
    )
    assert project.source == "PROJECT_PROTECTED_BINDING"
    fallback = resolve_database_binding(
        protected_path=tmp_path / "missing",
        environment={"DATABASE_URL": "postgresql://env:x@localhost/env"},
    )
    assert fallback.source == "DATABASE_URL_ENVIRONMENT"


def test_missing_binding_fails_cleanly(tmp_path):
    with pytest.raises(SweepExpectedError, match="PROJECT_DATABASE_BINDING_NOT_AVAILABLE"):
        resolve_database_binding(protected_path=tmp_path / "missing", environment={})


@pytest.mark.parametrize("statement", (
    "INSERT INTO x VALUES (1)", "UPDATE x SET y=1",
    "DELETE FROM x", "CREATE TABLE x (id int)",
))
def test_select_only_adapter_rejects_all_write_classes(statement):
    with pytest.raises(SweepExpectedError, match="PRODUCTION_MUTATION_GUARD_REJECTED_WRITE"):
        ReadOnlyResearchDatabase._assert_select(text(statement))


def test_run_id_collision_fails_closed(tmp_path):
    search = _search(tmp_path, _rows())
    run(search, run_id="collision", max_configs=1)
    with pytest.raises(SweepExpectedError, match="RUN_ID_ALREADY_EXISTS"):
        run(search, run_id="collision", max_configs=1)


def test_empty_dataset_is_semantic_failure_with_safe_preflight(tmp_path):
    search = _search(tmp_path, [])
    with pytest.raises(SweepExpectedError, match="DATASET_EMPTY"):
        run(search, run_id="empty", max_configs=1)
    preflight = json.loads(
        (tmp_path / "artifacts" / "empty" / "PREFLIGHT.json").read_text()
    )
    assert preflight["PARAMETER_SWEEP_PREFLIGHT"] == "FAILED"
    assert preflight["REASON"] == "DATASET_EMPTY"
    assert preflight["SECRET_OUTPUT"] == 0
    assert preflight["RUN_STARTED_AT"] and preflight["RUN_FAILED_AT"]


def test_artifacts_do_not_contain_database_secret(tmp_path):
    output = run(_search(tmp_path, _rows()), run_id="redaction", max_configs=1)
    rendered = "\n".join(
        path.read_text(encoding="utf-8") for path in output.iterdir() if path.is_file()
    )
    assert "read-secret" not in rendered
    assert "runtime-secret" not in rendered


def _planner_search(**overrides):
    value = {
        "strategy": "auto", "seed": 20260907,
        "exhaustive_max_configs": 10_000, "max_evaluated_configs": 5_000,
        "batch_size": 100, "stage1_fraction": .6,
        "stage2_fraction": .3, "stage3_fraction": .1,
        "max_configs_per_observation": 100,
        "minimum_validation_sample": 20, "minimum_holdout_sample": 20,
    }
    value.update(overrides)
    return value


def test_raw_cardinality_small_exhaustive_and_large_auto_bounded():
    planner = ParameterSweepSearchPlanner()
    small = {"a": [1, 2], "b": [3, 4, 5]}
    assert planner.raw_cardinality(small) == 6
    assert planner.plan(
        dataset_rows=100, space=small, search=_planner_search(),
        validation_rows=20, holdout_rows=20,
    ).selected_strategy == "EXHAUSTIVE_LAZY"
    large = {"a": list(range(1001)), "b": list(range(1001))}
    plan = planner.plan(
        dataset_rows=53, space=large, search=_planner_search(),
        validation_rows=11, holdout_rows=11,
    )
    assert plan.raw_search_space_size == 1_002_001
    assert plan.selected_strategy == "AUTO_BOUNDED"
    assert plan.evaluation_budget == 5_000
    assert plan.statistical_warning == "LARGE_HYPOTHESIS_SPACE_SMALL_SAMPLE"
    assert plan.promotion_eligible is False


def test_bounded_candidate_generation_is_lazy_and_reproducible():
    planner = ParameterSweepSearchPlanner()
    space = {"a": list(range(1001)), "b": list(range(1001))}
    plan = planner.plan(dataset_rows=53, space=space, search=_planner_search())
    iterator = _candidate_indices(plan)
    assert iter(iterator) is iterator
    first = [next(iterator) for _ in range(20)]
    assert first == [next(_candidate_indices(plan)) for _ in range(1)] + list(
        __import__("itertools").islice(_candidate_indices(plan), 1, 20)
    )
    assert len(set(first)) == 20
    assert _config_from_index(space, first[0]) == _config_from_index(space, first[0])


def test_memory_guard_auto_reduces_batch_and_can_fail_cleanly(monkeypatch):
    planner = ParameterSweepSearchPlanner()
    plan = planner.plan(
        dataset_rows=100, space={"a": list(range(20_000))},
        search=_planner_search(batch_size=100_000),
    )
    assert plan.batch_size == 256
    monkeypatch.setattr(planner, "MAX_ACTIVE_BATCH_MEMORY_MB", 0)
    with pytest.raises(SweepExpectedError, match="UNSAFE_MEMORY_PLAN"):
        planner.plan(
            dataset_rows=100, space={"a": list(range(20_000))},
            search=_planner_search(),
        )


def test_incremental_checkpoint_and_compatible_resume(tmp_path):
    search = _search(tmp_path, _rows())
    output = run(search, run_id="resume", stop_after_batches=1)
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    assert checkpoint["last_durable_result_index"] >= 0
    resumed = run(search, run_id="resume", resume=True)
    final = json.loads((resumed / "CHECKPOINT.json").read_text())
    assert final["completed"] is True
    assert final["evaluated_count"] == 2
    assert len((resumed / "RESULTS.jsonl").read_text().splitlines()) == 2


def test_resume_hash_mismatch_is_rejected(tmp_path):
    search_path = _search(tmp_path, _rows())
    run(search_path, run_id="mismatch", stop_after_batches=1)
    search = yaml.safe_load(search_path.read_text())
    search["search_space"]["min_positive_ev_r"].append(.3)
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    with pytest.raises(SweepExpectedError, match="RESUME_FINGERPRINT_MISMATCH"):
        run(search_path, run_id="mismatch", resume=True)


def test_holdout_is_never_used_for_search_or_ranking(tmp_path):
    output = run(_search(tmp_path, _rows()), run_id="holdout", max_configs=1)
    plan = json.loads((output / "SEARCH_PLAN.json").read_text())
    top = json.loads((output / "TOP_CONFIGS.json").read_text())
    assert all(stage["uses_holdout"] is False for stage in plan["STAGED_SEARCH_PLAN"])
    assert top["holdout_used_for_search"] is False
    assert "Holdout used for search/refinement/ranking: `NO`" in (
        output / "REPORT.md"
    ).read_text()


def test_incident_764411904_space_is_bounded_without_materialization(tmp_path):
    source = yaml.safe_load(
        Path("config/research/scalping_v2_parameter_sweep.yaml").read_text()
    )
    rows = []
    base = _rows()
    for index in range(53):
        row = dict(base[index % len(base)])
        row["position_id"] = f"incident-{index}"
        row["split"] = (
            "CALIBRATION" if index < 31 else "VALIDATION" if index < 42 else "HOLDOUT"
        )
        rows.append(row)
    dataset = tmp_path / "incident.json"
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    source["dataset"] = str(dataset)
    source["output_root"] = str(tmp_path / "artifacts")
    config = tmp_path / "incident.yaml"
    config.write_text(yaml.safe_dump(source), encoding="utf-8")
    output = run(config, run_id="incident", max_configs=5)
    preflight = json.loads((output / "PREFLIGHT.json").read_text())
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    assert preflight["RAW_SEARCH_SPACE_SIZE"] == 764_411_904
    assert preflight["EFFECTIVE_SEARCH_SPACE_SIZE"] < 764_411_904
    assert preflight["INVALID_COMBINATIONS_GENERATED"] == 0
    assert preflight["SEARCH_STRATEGY"] == "AUTO_BOUNDED"
    assert preflight["CONFIGURATIONS_PLANNED"] == 5
    assert checkpoint["evaluated_count"] == 5
    assert not (output / ".search-aggregate.sqlite3").exists()


def test_incident_53_closed_rows_without_causal_observations_stops_before_search(tmp_path):
    rows = []
    for index in range(53):
        row = dict(_rows()[index % 6])
        row["position_id"] = f"incident-empty-{index}"
        row["command_id"] = f"incident-command-{index}"
        row["time_stop_observations"] = []
        rows.append(row)
    search = _search(tmp_path, rows)
    with pytest.raises(
        SweepExpectedError, match="NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS",
    ):
        run(search, run_id="incident-53-zero-causal", max_configs=5)
    output = tmp_path / "artifacts" / "incident-53-zero-causal"
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    run_config = yaml.safe_load((output / "RUN_CONFIG.yaml").read_text())
    assert checkpoint["STATUS"] == "INSUFFICIENT_REPLAY_DATA"
    assert checkpoint["evaluated_count"] == 0
    assert checkpoint["SEARCH_ABORTED_BEFORE_5000_CONFIGS"] == "YES"
    assert run_config["baseline_control"]["BASELINE_EVALUATED"] == "YES"
    assert run_config["baseline_control"]["BASELINE_TRADES"] == 53


def test_baseline_zero_trade_contract_mismatch_fails_closed(tmp_path):
    rows = _rows()
    for row in rows:
        row.pop("exit_price")
    with pytest.raises(SweepExpectedError, match="BASELINE_REPLAY_INVALID"):
        run(_search(tmp_path, rows), run_id="baseline-invalid", max_configs=5)
    checkpoint = json.loads(
        (tmp_path / "artifacts" / "baseline-invalid" / "CHECKPOINT.json").read_text()
    )
    assert checkpoint["evaluated_count"] == 0
    assert checkpoint["FAILURE_REASON"] == "BASELINE_REPLAY_INVALID"
    assert checkpoint["RUN_STARTED_AT"] and checkpoint["RUN_FAILED_AT"]
    assert checkpoint["RUN_DURATION_SECONDS"] >= 0


def test_outcome_causal_and_full_replay_capabilities_are_separate():
    outcome_only = dict(_rows()[0])
    outcome_only["time_stop_observations"] = []
    causal = dict(_rows()[1])
    causal.update({
        "p_win_raw": .6, "effective_total_cost_bps": 10,
        "causal_opportunity": "opportunity-1",
    })
    coverage = _dataset_coverage([outcome_only, causal])
    assert coverage["OUTCOME_ONLY_REPLAY_ROWS"] == 2
    assert coverage["TIME_STOP_REPLAY_ELIGIBLE_ROWS"] == 1
    assert coverage["FULL_REPLAY_ELIGIBLE_ROWS"] == 1
    assert coverage["PRE_TIME_STOP_INSTRUMENTATION_ROWS"] == 1
    assert coverage["POST_TIME_STOP_INSTRUMENTATION_ROWS"] == 1


def test_gate_funnel_reports_exact_first_rejection_reason():
    rows = _rows()[:2]
    params = {name: values[0] for name, values in yaml.safe_load(
        Path("config/research/scalping_v2_parameter_sweep.yaml").read_text()
    )["search_space"].items()}
    params["min_net_edge_bps"] = 100
    admitted, funnel = _gate_funnel(rows, params)
    assert admitted == []
    assert funnel["INPUT_ROWS"] == 2
    assert funnel["REJECT_MIN_NET_EDGE"] == 2
    assert funnel["PASSED_ROWS"] == 0 and funnel["REJECTED_ROWS"] == 2
    assert "ALL_TRADES_FILTERED" not in funnel


def test_conditional_generator_never_emits_soft_gte_hard_and_collapses_children():
    space = yaml.safe_load(
        Path("config/research/scalping_v2_parameter_sweep.yaml").read_text()
    )["search_space"]
    variants = _conditional_variants(space)
    assert variants
    assert all(item["soft_timeout_seconds"] < item["hard_timeout_seconds"] for item in variants)
    assert all(
        item["max_extensions"] != 0 or item["extension_seconds"] == 0
        for item in variants
    )
    assert len(variants) < ParameterSweepSearchPlanner.raw_cardinality({
        name: space[name] for name in sorted(space) if name in _time_stop_space()
    })
    plan = ParameterSweepSearchPlanner().plan(
        dataset_rows=53, space=space, search=_planner_search(), max_configs_override=5,
    )
    configs = [
        _candidate_config(space, index)
        for index in __import__("itertools").islice(_candidate_indices(plan), 5)
    ]
    assert all(config["soft_timeout_seconds"] < config["hard_timeout_seconds"] for config in configs)
    assert plan.invalid_combinations_generated == 0
    assert plan.conditional_dimension_collapse is True


def test_shadow_observation_adapter_uses_persisted_causal_market_and_cost_evidence():
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    position = SimpleNamespace(
        average_entry_price=Decimal("100"), entry_quantity=Decimal("2"), side="LONG",
    )
    shadow = SimpleNamespace(
        current_price=Decimal("101"), mfe_bps=Decimal("200"), mae_bps=Decimal("100"),
        expected_exit_commission=Decimal("0.1818"), spread_cost=Decimal("0.0404"),
        slippage_cost=Decimal("0.0404"), adverse_exit_reserve=Decimal("0.0606"),
        evaluated_at=now, evaluation_closed_until_ms=int(now.timestamp() * 1000),
        setup_valid=True, momentum_valid=True, remaining_ev_r=Decimal("0.1"),
        target_progress=Decimal("0.5"), estimated_net_exit_pnl=Decimal("1.2"),
        shadow_decision="MONITORING", shadow_exit_price=None, shadow_fees=None,
        shadow_exit_reason=None, decision_reason=None,
        provenance={"commission": {"source": "BINANCE_ACCOUNT_COMMISSION"}},
    )
    observation = _shadow_observation(shadow, position)
    assert observation["source"] == "scalping_stale_position_shadow_diagnostics"
    assert observation["historical_cost_evidence"] is True
    assert observation["highs"] == [102.0] and observation["lows"] == [99.0]
    assert observation["evaluation_time_ms"] == observation["evaluation_closed_until_ms"]


def test_dataset_fingerprint_and_success_timing_are_persisted(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = run(_search(tmp_path / "a", _rows()), run_id="fingerprint-a", max_configs=1)
    changed = _rows()
    changed[0]["net_pnl"] = 99
    second = run(_search(tmp_path / "b", changed), run_id="fingerprint-b", max_configs=1)
    first_config = yaml.safe_load((first / "RUN_CONFIG.yaml").read_text())
    second_config = yaml.safe_load((second / "RUN_CONFIG.yaml").read_text())
    assert first_config["dataset_fingerprint"] != second_config["dataset_fingerprint"]
    assert first_config["RUN_STARTED_AT"] and first_config["RUN_FINISHED_AT"]
    assert first_config["RUN_DURATION_SECONDS"] >= 0
    assert first_config["RUN_DURATION_HUMAN"]
    report = (first / "REPORT.md").read_text()
    assert all(section in report for section in (
        "RUN SUMMARY", "RUNTIME", "DATASET COVERAGE", "BASELINE CONTROL",
        "REPLAY CAPABILITY", "GATE REJECTION FUNNEL", "SEARCH PLAN", "RESULTS",
        "TIME-STOP ANALYSIS", "STATISTICAL SUFFICIENCY",
    ))


def test_top_and_pareto_exclude_unaccepted_and_holdout_is_reporting_only(tmp_path):
    output = run(_search(tmp_path, _rows()), run_id="ranking-contract", max_configs=2)
    results = json.loads((output / "RESULTS.json").read_text())
    top = json.loads((output / "TOP_CONFIGS.json").read_text())
    eligible = {
        item["config_hash"] for item in results
        if item["result_status"] == "ACCEPTED"
        and item["validation"]["trade_count"] > 0
    }
    assert {item["config_hash"] for item in top["ranked_without_holdout"]} <= eligible
    assert set(top["pareto_frontier"]) <= eligible
    assert top["holdout_used_for_search"] is False
