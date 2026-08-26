from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict
import json

import pytest

from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_diagnostics import SetupDiagnostics, SetupSemanticBucket
from app.engine_setup.setup_quality_diagnostics import SetupQualityDiagnostics, diagnose_setup_quality, quality_from_score
from app.engine_setup.setup_rules import evaluate_setup_rules
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters


def test_detector_propagates_analysis_boundary_without_mutation(analysis_snapshot_factory):
    """Given one analysis boundary, when setup is detected, then boundary/source propagate unchanged."""
    snapshot = analysis_snapshot_factory()
    before = deepcopy(asdict(snapshot))
    candidate = SetupDetector().detect(snapshot)
    assert asdict(snapshot) == before
    assert candidate.closed_until_ms == snapshot.closed_until_ms
    assert candidate.source_analysis_snapshot_id == snapshot.snapshot_id
    assert candidate.future_bars_used is False


def test_scalping_candidate_has_first_class_family_geometry_and_stable_opportunity(
    analysis_snapshot_factory,
):
    parameters = resolve_runtime_parameters("trade-5m-v1")
    detector = SetupDetector(parameters)
    analysis = analysis_snapshot_factory(
        timeframe="5m",
        impulse_phase="IMPULSE_EXTENSION",
        reason_codes=["BREAKOUT_HELD_WITH_FOLLOW_THROUGH"],
        analysis_context={
            "scalping": {"market_regime": "UP"},
            "confirmation_close": 100.0,
            "causal_support_level": 99.5,
            "causal_resistance_level": 101.0,
            "causal_resistance_candidates": [{"price": 101.0, "source_type": "LOCAL_5M"}],
        },
    )
    first = detector.detect(analysis)
    second = detector.detect(analysis)
    assert first.setup_type == "SCALP_BREAKOUT"
    assert first.opportunity_id == second.opportunity_id
    assert first.entry_zone == {"lower": 100.0, "upper": 100.0}
    assert first.causal_invalidation == 99.5
    assert first.target_candidates == [{"price": 101.0, "source_type": "LOCAL_5M"}]
    assert first.regime == "UP"


def test_freshness_or_degraded_failure_never_creates_setup(analysis_snapshot_factory):
    """Given degraded analysis, when setup detection runs, then output is invalid and non-actionable."""
    candidate = SetupDetector().detect(analysis_snapshot_factory(degraded=True))
    assert candidate.status == "SETUP_INVALID"
    assert candidate.is_trade_signal is False


def test_not_enough_data_maps_to_no_setup(analysis_snapshot_factory):
    """Given insufficient analysis history, when detected, then NO_SETUP carries the explicit reason."""
    candidate = SetupDetector().detect(analysis_snapshot_factory(enough_data=False))
    assert candidate.status == "NO_SETUP"
    assert "NOT_ENOUGH_DATA" in candidate.invalidation_reasons


def test_rules_are_deterministic_and_do_not_mutate_context(context_factory):
    """Given one immutable context, when evaluated twice, then rule output and input remain stable."""
    context = context_factory(
        impulse_phase="CONTROLLED_PULLBACK",
        reason_codes=("BREAKOUT_HELD_WITH_FOLLOW_THROUGH",),
        analysis_context={"level": {"available": True}},
    )
    before = deepcopy(context.analysis_context)
    assert evaluate_setup_rules(context) == evaluate_setup_rules(context)
    assert context.analysis_context == before


def test_quality_components_are_bounded_and_deterministic():
    """Given structural/confirmation/context evidence, when scored, then current components stay in 0..100."""
    diagnostics = SetupDiagnostics(
        has_structural_trigger=True,
        has_directional_context=True,
        has_level_context=True,
        is_actionable_setup_candidate=True,
        semantic_bucket=SetupSemanticBucket.CANDIDATE_STRUCTURE.value,
    )
    arguments = dict(
        status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        direction_hint="BULLISH", confirmation_state="CONFIRMED_BY_ANALYSIS",
        diagnostics=diagnostics, source_analysis_entry_quality="GOOD",
        source_confidence=0.8, source_regime="UP", source_impulse_phase="IMPULSE_EXTENSION",
    )
    first = diagnose_setup_quality(**arguments)
    second = diagnose_setup_quality(**arguments)
    assert first == second
    assert all(0 <= value <= 100 for value in (
        first.structural_score, first.confirmation_score, first.context_score,
        first.conflict_penalty, first.invalidation_penalty, first.quality_score,
    ))


@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "GOOD"), (80, "GOOD"), (65, "ACCEPTABLE"), (45, "WEAK"), (1, "POOR"), (0, "UNKNOWN"), (None, "UNKNOWN")],
)
def test_quality_score_boundaries_and_missing_policy(score, expected):
    """Given a score or missing score, when tiered, then bounds and missing-input policy are stable."""
    assert quality_from_score(score) == expected


def test_quality_model_rejects_out_of_range_component():
    """Given an invalid component, when constructed, then the public 0..100 contract rejects it."""
    with pytest.raises(ValueError, match="0..100"):
        SetupQualityDiagnostics("GOOD", 80, 101, 0, 0, 0, 0)


def test_setup_quality_excludes_downstream_volume_target_and_rr_components():
    """Given the current setup contract, when fields are inspected, then downstream target/RR are absent."""
    fields = set(SetupQualityDiagnostics.__dataclass_fields__)
    assert {"structural_score", "confirmation_score", "context_score"} <= fields
    assert {"volume_score", "target_score", "rr_score"}.isdisjoint(fields)


def test_candidate_is_frozen_and_json_serializable(analysis_snapshot_factory):
    """Given a candidate, when serialized, then JSON round-trip works and identity mutation is blocked."""
    candidate = SetupDetector().detect(analysis_snapshot_factory())
    payload = asdict(candidate)
    assert json.loads(json.dumps(payload)) == payload
    with pytest.raises(FrozenInstanceError):
        candidate.symbol = "ETHUSDT"  # type: ignore[misc]


def test_missing_levels_and_confirmation_do_not_become_candidate(context_factory):
    """Given range context without edge/confirmation evidence, when evaluated, then no candidate appears."""
    result = evaluate_setup_rules(context_factory(regime="FLAT", analysis_context={"range_context": True}))
    assert result.status == "NO_SETUP"
    assert "RANGE_PRESENT_BUT_NO_EDGE_TOUCH" in result.reason_codes


def test_public_imports_have_no_legacy_setup_module():
    """Given the current package, when legacy imports are attempted, then they remain absent."""
    with pytest.raises(ModuleNotFoundError):
        __import__("app.engine_trend.setup")
