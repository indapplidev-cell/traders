"""Canonical user-launchable Parameter Sweep research modes."""

from __future__ import annotations

from enum import StrEnum
ACTIVE_RESEARCH_FAMILIES = ("SIGNAL", "REGIME", "ENTRY", "GEOMETRY")
FROZEN_RESEARCH_FAMILIES = (
    "ECONOMICS", "LIFECYCLE_SHADOW", "RISK_SAFETY", "COSTS",
)


class ResearchMode(StrEnum):
    ALL = "ALL"
    SET2_BASELINE = "SET2_BASELINE"
    ONE_FACTOR_SENSITIVITY = "ONE_FACTOR_SENSITIVITY"
    SMALL_FAMILY_SEARCH = "SMALL_FAMILY_SEARCH"
    TOP_REGION_REFINEMENT = "TOP_REGION_REFINEMENT"
    LOCAL_FINALIST_VALIDATION = "LOCAL_FINALIST_VALIDATION"

    @property
    def selected_stage(self) -> str | None:
        return None if self is ResearchMode.ALL else self.value


RESEARCH_MODES = tuple(ResearchMode)
RESEARCH_MODE_VALUES = tuple(mode.value for mode in RESEARCH_MODES)


def parse_research_mode(value: object) -> ResearchMode:
    """Return the one typed mode identity or fail closed without aliases."""
    if isinstance(value, ResearchMode):
        return value
    if not isinstance(value, str):
        raise ValueError("UNSUPPORTED_RESEARCH_MODE")
    try:
        return ResearchMode(value)
    except ValueError:
        raise ValueError("UNSUPPORTED_RESEARCH_MODE") from None


def families_for_mode(mode: ResearchMode) -> tuple[str, ...]:
    """All current stage modes operate only on the targeted v2 family union."""
    return ACTIVE_RESEARCH_FAMILIES


__all__ = [
    "ACTIVE_RESEARCH_FAMILIES", "FROZEN_RESEARCH_FAMILIES", "RESEARCH_MODES",
    "RESEARCH_MODE_VALUES", "ResearchMode", "families_for_mode",
    "parse_research_mode",
]
