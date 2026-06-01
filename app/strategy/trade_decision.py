"""Доменные структуры торгового решения."""

from dataclasses import dataclass
from datetime import datetime, UTC
from decimal import Decimal
from enum import StrEnum


class DecisionType(StrEnum):
    """Допустимые торговые решения на текущем этапе."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketRegime(StrEnum):
    """Грубые режимы рынка для MVP-логики."""

    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class TradeDecision:
    """Результат работы стратегии.

    Решение хранится отдельно от механизма исполнения, чтобы не смешивать
    анализ рынка с действиями по открытию или закрытию позиции.
    """

    symbol: str
    interval: str
    decision: DecisionType
    reason: str
    regime: MarketRegime
    price: Decimal
    created_at: datetime

    @classmethod
    def build(
        cls,
        *,
        symbol: str,
        interval: str,
        decision: DecisionType,
        reason: str,
        regime: MarketRegime,
        price: Decimal,
        created_at: datetime | None = None,
    ) -> "TradeDecision":
        """Создаёт решение с текущим UTC-временем."""

        return cls(
            symbol=symbol,
            interval=interval,
            decision=decision,
            reason=reason,
            regime=regime,
            price=price,
            created_at=created_at or datetime.now(UTC),
        )
