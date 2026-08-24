"""Research-flow context used by frequency gates only."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RiskContext:
    utc_day: str
    trade_profile_id: str = "trade-15m-v1"
    symbol_preapprovals_before: int = 0
    total_preapprovals_before: int = 0
    direction_preapprovals_before: int = 0

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)
