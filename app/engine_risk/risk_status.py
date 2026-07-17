"""Closed vocabulary for research-only risk decisions."""

from enum import StrEnum


class RiskStatus(StrEnum):
    RISK_PRE_APPROVED_RESEARCH = "RISK_PRE_APPROVED_RESEARCH"
    REJECT = "REJECT"
    WAIT = "WAIT"
    NO_DECISION = "NO_DECISION"
    ERROR = "ERROR"
