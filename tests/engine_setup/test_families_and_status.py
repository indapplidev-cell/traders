from __future__ import annotations

import pytest

from app.engine_setup.setup_rules import evaluate_setup_rules
from app.engine_setup.setup_status import SetupStatus
from app.engine_setup.setup_type import SetupType
from app.engine_setup.setup_detector import SetupDetector


@pytest.mark.parametrize(
    ("changes", "expected_type", "expected_status"),
    [
        ({"impulse_phase": "IMPULSE_EXTENSION", "reason_codes": ("BREAKOUT_HELD_WITH_FOLLOW_THROUGH",)}, "BREAKOUT_CONTINUATION", "SETUP_CANDIDATE"),
        ({"impulse_phase": "CONTROLLED_PULLBACK", "reason_codes": ("BREAKOUT_HELD_WITH_FOLLOW_THROUGH",)}, "PULLBACK_CONTINUATION", "SETUP_CANDIDATE"),
        ({"reason_codes": ("SUCCESSFUL_RETEST",)}, "BREAKOUT_RETEST", "SETUP_CANDIDATE"),
        ({"regime": "FLAT", "reason_codes": ("RANGE_BOUNDARY_REJECTION",), "analysis_context": {"market_structure": "RANGE", "price_location": "LOWER_BOUNDARY", "follow_through": "CONFIRMED"}}, "RANGE_REJECTION", "SETUP_CANDIDATE"),
        ({"reason_codes": ("FAILED_BREAKOUT_RANGE_REENTRY", "REVERSAL_CONFIRMED"), "analysis_context": {"failed_breakout_direction": "UP"}}, "FALSE_BREAKOUT_REVERSAL", "SETUP_CANDIDATE"),
        ({"impulse_phase": "IMPULSE_EXHAUSTION_RISK", "reason_codes": ("WICK_REJECTION_AFTER_EXTENSION",)}, "MOMENTUM_EXHAUSTION", "WAIT_FOR_CONFIRMATION"),
        ({"reason_codes": ("REVERSAL_EVIDENCE",), "analysis_context": {"direction": "BULLISH"}}, "REVERSAL_START", "WAIT_FOR_CONFIRMATION"),
        ({"impulse_phase": "IMPULSE_EXTENSION", "reason_codes": ()}, "TREND_CONTINUATION", "WAIT_FOR_CONFIRMATION"),
    ],
)
def test_current_setup_families_route_by_existing_contract(context_factory, changes, expected_type, expected_status):
    """Given current analysis evidence, when rules run, then the documented current family/status is selected."""
    result = evaluate_setup_rules(context_factory(**changes))
    assert result.setup_type == expected_type
    assert result.status == expected_status


def test_untriggered_no_action_maps_to_no_setup(context_factory):
    """Given NO_ACTION without structure, when rules run, then it maps to NO_SETUP with a reason."""
    result = evaluate_setup_rules(context_factory())
    assert result.status == SetupStatus.NO_SETUP.value
    assert result.setup_type == SetupType.NO_SETUP.value
    assert "ANALYSIS_NO_ACTION_WITHOUT_SETUP_CONTEXT" in result.reason_codes


def test_unknown_analysis_input_is_safe(context_factory):
    """Given UNKNOWN/missing quality, when rules run, then no setup candidate is manufactured."""
    result = evaluate_setup_rules(context_factory(regime="UNKNOWN", entry_quality=None, action=None))
    assert result.status == SetupStatus.NO_SETUP.value
    assert result.setup_type == SetupType.NO_SETUP.value


def test_invalid_quality_invalidates_existing_structure(context_factory):
    """Given a breakout structure with invalid quality, when rules run, then the setup is invalid."""
    result = evaluate_setup_rules(
        context_factory(
            entry_quality="INVALID",
            impulse_phase="IMPULSE_EXTENSION",
            reason_codes=("BREAKOUT_HELD_WITH_FOLLOW_THROUGH",),
        )
    )
    assert result.status == SetupStatus.SETUP_INVALID.value
    assert "ENTRY_QUALITY_INVALID" in result.invalidation_reasons


def test_legacy_family_labels_are_not_current_public_enums():
    """Given historical family labels, when compared to current enums, then only current contracts remain public."""
    values = {item.value for item in SetupType}
    assert "SHORT_CONTINUATION_PRACTICAL_TARGET" not in values
    assert "SHORT_FAILED_REBOUND" not in values
    assert "TRAP_REVERSAL" not in values
    assert "RANGE_REJECTION" in values
    assert "FALSE_BREAKOUT_REVERSAL" in values


def test_all_first_class_scalping_families_are_public_and_profile_owned():
    expected = {
        "SCALP_TREND_PULLBACK", "SCALP_BREAKOUT", "SCALP_BREAKOUT_RETEST",
        "SCALP_RANGE_BOUNCE", "SCALP_LIQUIDITY_SWEEP",
        "SCALP_MOMENTUM_CONTINUATION", "SCALP_COMPRESSION_BREAK",
    }
    assert expected <= {item.value for item in SetupType}
