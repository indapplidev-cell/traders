"""Configuration for research risk policy, never account/execution risk."""

from dataclasses import dataclass, field


_QUALITY_RANK = {"GOOD": 0, "ACCEPTABLE": 1, "WEAK": 2, "REJECTED": 3,
                 "WAITING": 4, "UNKNOWN": 5, "ERROR": 6}


@dataclass(frozen=True, slots=True)
class RiskConfig:
    policy_version: str = "ENGINE_RISK_01_RESEARCH_POLICY_V1"
    allow_only_strategy_status: frozenset[str] = field(
        default_factory=lambda: frozenset({"ALLOW_RESEARCH_TRADE_PLAN"}))
    minimum_strategy_quality: str = "ACCEPTABLE"
    minimum_strategy_score: float | None = 65.0
    allowed_strategy_types: frozenset[str] = field(default_factory=lambda: frozenset({
        "BREAKOUT_CONTINUATION_RESEARCH", "TREND_CONTINUATION_RESEARCH",
    }))
    require_risk_review_flag: bool = True
    reject_if_source_trade_signal: bool = True
    reject_if_source_executable: bool = True
    reject_if_future_bars_used: bool = True
    max_research_preapprovals_per_symbol_per_day: int = 20
    max_research_preapprovals_total_per_day: int = 50
    max_research_preapprovals_per_direction_per_day: int = 30
    enforce_research_preapproval_limits: bool = True
    allow_medium_risk: bool = False

    def __post_init__(self) -> None:
        quality = str(self.minimum_strategy_quality).upper()
        statuses = frozenset(str(value).upper() for value in self.allow_only_strategy_status)
        types = frozenset(str(value).upper() for value in self.allowed_strategy_types)
        if quality not in {"GOOD", "ACCEPTABLE"}:
            raise ValueError("minimum_strategy_quality must be GOOD or ACCEPTABLE")
        if not statuses or not types:
            raise ValueError("allowed statuses and strategy types must not be empty")
        if self.minimum_strategy_score is not None and not 0 <= float(self.minimum_strategy_score) <= 100:
            raise ValueError("minimum_strategy_score must be in the 0..100 range")
        limits = (self.max_research_preapprovals_per_symbol_per_day,
                  self.max_research_preapprovals_total_per_day,
                  self.max_research_preapprovals_per_direction_per_day)
        if any(value < 1 for value in limits):
            raise ValueError("research preapproval limits must be positive")
        object.__setattr__(self, "minimum_strategy_quality", quality)
        object.__setattr__(self, "allow_only_strategy_status", statuses)
        object.__setattr__(self, "allowed_strategy_types", types)

    def quality_meets_minimum(self, quality: str) -> bool:
        return quality in _QUALITY_RANK and _QUALITY_RANK[quality] <= _QUALITY_RANK[self.minimum_strategy_quality]
