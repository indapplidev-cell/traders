"""ENGINE-RISK-01 contract errors."""


class RiskContractError(ValueError):
    """Raised when a RiskDecision violates its non-execution contract."""
