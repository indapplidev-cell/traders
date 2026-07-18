from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict
import json
from pathlib import Path

import pytest

from app.engine_strategy.strategy_filter import StrategyFilter
from app.engine_strategy.strategy_status import StrategyStatus


def test_approved_current_setup_requires_risk_review(candidate_factory):
    """Given an acceptable confirmed setup, when filtered, then research approval requires engine_risk."""
    decision = StrategyFilter().evaluate(candidate_factory())
    assert decision.decision_status == StrategyStatus.ALLOW_RESEARCH_TRADE_PLAN.value
    assert decision.requires_risk_review is True
    assert decision.required_next_layer == "engine_risk"
    assert decision.is_executable is False
    assert "STRATEGY_REQUIRES_RISK_REVIEW" in decision.decision_reasons


def test_invalid_setup_is_rejected_with_stable_reason(candidate_factory):
    """Given SETUP_INVALID, when filtered, then rejection has the stable invalid-setup reason."""
    decision = StrategyFilter().evaluate(
        candidate_factory(status="SETUP_INVALID", setup_quality="INVALID", quality_score=0)
    )
    assert decision.decision_status == StrategyStatus.REJECT.value
    assert decision.rejection_reasons == ["STRATEGY_REJECT_SETUP_INVALID"]


def test_no_setup_and_unknown_quality_never_approve(candidate_factory):
    """Given NO_SETUP or unknown quality, when filtered, then neither can become approved."""
    no_setup = StrategyFilter().evaluate(
        candidate_factory(
            status="NO_SETUP", setup_type="NO_SETUP", direction_hint="NONE",
            confirmation_state="NOT_APPLICABLE", setup_quality="UNKNOWN", quality_score=None,
        )
    )
    assert no_setup.decision_status == StrategyStatus.NO_DECISION.value
    assert "STRATEGY_NO_DECISION_NO_SETUP" in no_setup.decision_reasons
    with pytest.raises(ValueError, match="UNKNOWN is also forbidden"):
        candidate_factory(setup_quality="UNKNOWN", quality_score=None)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"direction_hint": "NEUTRAL"}, "STRATEGY_REJECT_NEUTRAL_DIRECTION"),
        ({"setup_type": "BREAKOUT_RETEST"}, "STRATEGY_REJECT_UNSUPPORTED_SETUP_TYPE"),
    ],
)
def test_unsupported_direction_or_family_is_rejected(candidate_factory, changes, reason):
    """Given unsupported direction/family, when filtered, then rejection explains the contract gate."""
    decision = StrategyFilter().evaluate(candidate_factory(**changes))
    assert decision.decision_status == StrategyStatus.REJECT.value
    assert reason in decision.rejection_reasons


def test_conflict_warnings_propagate_to_rejection(candidate_factory):
    """Given severe contemporaneous conflict, when filtered, then warning and conflict reason survive."""
    decision = StrategyFilter().evaluate(
        candidate_factory(quality_warnings=["SEVERE_STRUCTURE_CONFLICT"])
    )
    assert decision.decision_status == StrategyStatus.REJECT.value
    assert decision.decision_warnings == ["SEVERE_STRUCTURE_CONFLICT"]
    assert "STRATEGY_REJECT_CONFLICTING_CONTEXT" in decision.rejection_reasons


def test_decision_is_deterministic_except_creation_time_and_does_not_mutate(candidate_factory):
    """Given one setup, when filtered twice, then contract output is deterministic and input unchanged."""
    candidate = candidate_factory(context={"analysis_confidence": 0.8})
    before = deepcopy(asdict(candidate))
    first = StrategyFilter().evaluate(candidate).to_dict()
    second = StrategyFilter().evaluate(candidate).to_dict()
    first.pop("created_at_ms")
    second.pop("created_at_ms")
    assert first == second
    assert asdict(candidate) == before


def test_serialization_round_trip_immutability_and_boundary(candidate_factory):
    """Given a decision, when serialized, then boundary round-trips and the model is immutable."""
    candidate = candidate_factory()
    decision = StrategyFilter().evaluate(candidate)
    payload = decision.to_dict()
    assert json.loads(json.dumps(payload)) == payload
    assert decision.closed_until_ms == candidate.closed_until_ms
    assert decision.source_setup_id == candidate.setup_id
    with pytest.raises(FrozenInstanceError):
        decision.symbol = "ETHUSDT"  # type: ignore[misc]


def test_strategy_source_has_no_network_database_or_docker_access():
    """Given strategy source, when statically inspected, then it has no external I/O dependencies."""
    root = Path(__file__).resolve().parents[2] / "app" / "engine_strategy"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    forbidden = ("import socket", "import requests", "import httpx", "sqlalchemy", "psycopg", "docker")
    assert not any(token in source for token in forbidden)


def test_no_legacy_strategy_import():
    """Given current public imports, when legacy strategy is imported, then it remains absent."""
    with pytest.raises(ModuleNotFoundError):
        __import__("app.engine_trend.strategy")
