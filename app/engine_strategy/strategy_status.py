"""Closed vocabularies for non-executable strategy decisions."""

from enum import StrEnum


class StrategyStatus(StrEnum):
    ALLOW_RESEARCH_TRADE_PLAN = "ALLOW_RESEARCH_TRADE_PLAN"
    REJECT = "REJECT"
    WAIT = "WAIT"
    NO_DECISION = "NO_DECISION"
    ERROR = "ERROR"


class StrategyQuality(StrEnum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    WEAK = "WEAK"
    REJECTED = "REJECTED"
    WAITING = "WAITING"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"
