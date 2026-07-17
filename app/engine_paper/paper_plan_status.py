"""Closed status vocabulary for ENGINE-PAPER-01."""

from enum import StrEnum


class PaperPlanStatus(StrEnum):
    PAPER_PLAN_READY = "PAPER_PLAN_READY"
    REJECT = "REJECT"
    WAIT = "WAIT"
    NO_PLAN = "NO_PLAN"
    ERROR = "ERROR"
