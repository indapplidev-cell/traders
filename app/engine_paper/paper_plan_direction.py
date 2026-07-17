"""Non-command direction vocabulary for paper plans."""

from enum import StrEnum


class PaperPlanDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    NONE = "NONE"
