"""Configuration for deterministic, outcome-free strategy gates."""

from dataclasses import dataclass, field

from app.engine_setup.setup_status import SetupQuality


_QUALITY_RANK = {"GOOD": 0, "ACCEPTABLE": 1, "WEAK": 2, "POOR": 3, "INVALID": 4, "UNKNOWN": 5}


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    minimum_allowed_quality: str = SetupQuality.ACCEPTABLE.value
    allow_weak_candidates: bool = False
    allow_weak_to_wait: bool = True
    allowed_setup_types: frozenset[str] = field(default_factory=lambda: frozenset({
        "BREAKOUT_CONTINUATION", "TREND_CONTINUATION",
    }))
    require_confirmed_by_analysis: bool = True
    reject_on_invalidation_reasons: bool = True
    reject_on_future_bars: bool = True
    reject_if_source_is_trade_signal: bool = True
    require_directional_hint: bool = True

    def __post_init__(self) -> None:
        quality = SetupQuality(str(self.minimum_allowed_quality).upper()).value
        allowed = frozenset(str(value).upper() for value in self.allowed_setup_types)
        if quality not in {"GOOD", "ACCEPTABLE", "WEAK"}:
            raise ValueError("minimum_allowed_quality must be GOOD, ACCEPTABLE, or WEAK")
        if not allowed:
            raise ValueError("allowed_setup_types must not be empty")
        object.__setattr__(self, "minimum_allowed_quality", quality)
        object.__setattr__(self, "allowed_setup_types", allowed)

    def quality_meets_minimum(self, quality: str) -> bool:
        return _QUALITY_RANK[quality] <= _QUALITY_RANK[self.minimum_allowed_quality]
