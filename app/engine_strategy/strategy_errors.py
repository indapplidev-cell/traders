"""Strategy-layer exceptions."""


class StrategyError(Exception):
    """Base strategy-layer error."""


class StrategyContractError(StrategyError, ValueError):
    """Raised when a strategy decision violates its non-execution contract."""
