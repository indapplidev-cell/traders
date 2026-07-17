"""Diagnostic policy levels; these are not monetary risk measurements."""

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"
    WAITING = "WAITING"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"
