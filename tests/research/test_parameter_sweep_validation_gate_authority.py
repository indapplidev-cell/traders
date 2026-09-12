from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import (
    RESEARCH_PARAMETERS, load_validation_sample_policy,
)
from traders_ml.parameter_sweep.artifact_v2 import (
    aggregate_result_semantics, compact_result,
)
from traders_ml.parameter_sweep.controller import PresentationState
from traders_ml.parameter_sweep.engine import ParameterSweepSearchPlanner
from traders_ml.parameter_sweep.ranking import rank_score


def _write_policy(tmp_path: Path, *, trades: int = 20, periods: int = 3) -> Path:
    value = RESEARCH_PARAMETERS.model_dump(mode="json")
    value["ranking"]["validation_minimum_trades"] = trades
    value["ranking"]["minimum_independent_periods"] = periods
    path = tmp_path / "research_parameters.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _policy(path: Path):
    return load_validation_sample_policy(path)


def _item(*, trades: int, periods: int) -> dict[str, object]:
    start = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    validation_trades = [
        {
            "symbol": "DOGEUSDT", "setup_type": "BREAKOUT", "net_pnl": 1,
            "opened_at_ms": start + (index % periods) * 86_400_000,
        }
        for index in range(trades)
    ]
    return {
        "result_index": 0, "result_status": "ACCEPTED",
        "calibration": {"trade_count": 1},
        "validation": {"trades": validation_trades},
        "holdout": {"status": "NOT_EVALUATED"},
    }


def test_canonical_values_and_provenance_are_resolved_once():
    policy = load_validation_sample_policy(
        Path("config/research/research_parameters.yaml"),
    )
    assert policy.minimum_validation_trades == 20
    assert policy.minimum_independent_periods == 3
    assert policy.independent_period_unit == "UTC_CALENDAR_DAY"
    assert policy.source("minimum_validation_trades").endswith(
        ":ranking.validation_minimum_trades"
    )


def test_temporary_21_and_4_propagate_to_every_consumer(tmp_path):
    policy = _policy(_write_policy(tmp_path, trades=21, periods=4))
    planner = ParameterSweepSearchPlanner()
    search = RESEARCH_PARAMETERS.search.model_dump(mode="python")
    plan = planner.plan(
        dataset_rows=21, validation_rows=20, space={"a": [1]}, search=search,
        validation_policy=policy,
    )
    assert plan.promotion_eligible is False  # search sees 21, not 20

    row = compact_result(_item(trades=21, periods=4), validation_policy=policy)
    assert rank_score(row, policy)[3] == 21  # ranking sees 21
    assert row["performance_class"] != "INSUFFICIENT_SAMPLE"
    assert row["independent_period_unit"] == "UTC_CALENDAR_DAY"
    readiness = aggregate_result_semantics([row], validation_policy=policy)[
        "validation_readiness"
    ]
    assert readiness["validation_trade_count"]["required"] == 21
    assert readiness["independent_period_count"]["required"] == 4
    assert readiness["validation_trade_count"]["pass"] is True
    assert readiness["independent_period_count"]["pass"] is True

    fields = policy.artifact_fields()
    assert fields["VALIDATION_MINIMUM_TRADES"] == 21  # report/artifact consumer
    assert fields["MINIMUM_INDEPENDENT_PERIODS"] == 4
    gui = PresentationState(
        validation_minimum_trades=fields["VALIDATION_MINIMUM_TRADES"],
        minimum_independent_periods=fields["MINIMUM_INDEPENDENT_PERIODS"],
        independent_period_unit=fields["INDEPENDENT_PERIOD_UNIT"],
    )
    assert (gui.validation_minimum_trades, gui.minimum_independent_periods) == (21, 4)


def test_missing_canonical_key_fails_closed(tmp_path):
    path = _write_policy(tmp_path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    del value["ranking"]["validation_minimum_trades"]
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative YAML"):
        load_validation_sample_policy(path)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("search", "minimum_validation_sample"), 20),
        (("minimum_samples", "validation"), 20),
        (("ranking", "minimum_trades"), 20),
    ),
)
def test_duplicate_authority_keys_fail_closed(tmp_path, path, value):
    policy_path = _write_policy(tmp_path)
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    payload[path[0]][path[1]] = value
    policy_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative YAML"):
        load_validation_sample_policy(policy_path)


@pytest.mark.parametrize(
    ("name", "value"),
    (("validation_minimum_trades", "20"), ("minimum_independent_periods", 3.5)),
)
def test_gate_types_do_not_coerce_unsafely(tmp_path, name, value):
    path = _write_policy(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["ranking"][name] = value
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative YAML"):
        load_validation_sample_policy(path)
