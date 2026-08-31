"""Configuration for causal, paper-only plan construction."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PaperConfig:
    plan_policy_version: str = "ENGINE_PAPER_01_PLAN_POLICY_V1"
    allow_only_risk_status: frozenset[str] = field(
        default_factory=lambda: frozenset({"RISK_PRE_APPROVED_RESEARCH"}))
    allowed_risk_levels: frozenset[str] = field(default_factory=lambda: frozenset({"LOW"}))
    allowed_strategy_types: frozenset[str] = field(default_factory=lambda: frozenset({
        "BREAKOUT_CONTINUATION_RESEARCH", "TREND_CONTINUATION_RESEARCH",
    }))
    require_risk_pre_approved: bool = True
    require_execution_review_flag: bool = True
    minimum_planned_rr: float = 1.5
    entry_fee_bps: float = 10.0
    exit_fee_bps: float = 10.0
    entry_slippage_bps: float = 2.0
    exit_slippage_bps: float = 2.0
    cost_safety_margin_bps: float = 3.0
    minimum_net_edge_bps: float = 1.0
    economic_policy_version: str = "PAPER_CANONICAL_NET_COST_V1"
    maximum_stop_distance_pct: float | None = None
    maximum_target_distance_pct: float | None = None
    allow_fallback_target: bool = False
    allow_fallback_stop: bool = False
    default_stop_buffer_pct: float = 0.001
    default_target_rr: float = 1.5
    reject_if_source_trade_signal: bool = True
    reject_if_source_executable: bool = True
    reject_if_source_order_approved: bool = True
    reject_if_source_execution_approved: bool = True
    reject_if_position_size_approved: bool = True
    reject_if_future_bars_used: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "allow_only_risk_status", self._normalized(self.allow_only_risk_status))
        object.__setattr__(self, "allowed_risk_levels", self._normalized(self.allowed_risk_levels))
        object.__setattr__(self, "allowed_strategy_types", self._normalized(self.allowed_strategy_types))
        if not self.plan_policy_version or not self.allow_only_risk_status:
            raise ValueError("paper policy version and allowed statuses must not be empty")
        if float(self.minimum_planned_rr) <= 0 or float(self.default_target_rr) <= 0:
            raise ValueError("RR values must be positive")
        if float(self.default_stop_buffer_pct) < 0:
            raise ValueError("default_stop_buffer_pct must not be negative")
        costs = (
            self.entry_fee_bps, self.exit_fee_bps, self.entry_slippage_bps,
            self.exit_slippage_bps, self.cost_safety_margin_bps,
            self.minimum_net_edge_bps,
        )
        if any(float(value) < 0 for value in costs):
            raise ValueError("economic gate inputs must not be negative")
        if not self.economic_policy_version:
            raise ValueError("economic policy version must not be empty")
        for value in (self.maximum_stop_distance_pct, self.maximum_target_distance_pct):
            if value is not None and float(value) <= 0:
                raise ValueError("maximum distance percentages must be positive")

    @staticmethod
    def _normalized(values) -> frozenset[str]:
        return frozenset(str(value).upper() for value in values)
