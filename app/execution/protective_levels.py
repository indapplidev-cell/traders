"""Расчёт и проверка stop-loss / take-profit."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.db.models import Candle


@dataclass(slots=True)
class ProtectiveLevels:
    """Набор защитных уровней для LONG-позиции."""

    stop_loss: Decimal
    take_profit: Decimal


def calculate_long_protective_levels(entry_price: Decimal, atr_14: Decimal | None) -> ProtectiveLevels:
    """Считает базовые SL/TP для LONG через ATR.

    Это грубая MVP-модель. Она не моделирует проскальзывание и не заменяет
    полноценный риск-движок, но даёт простой воспроизводимый контур защиты.
    """

    if atr_14 is None or atr_14 <= 0:
        raise ValueError("Нельзя открыть BUY без ATR14: недоступны уровни stop-loss / take-profit.")

    return ProtectiveLevels(
        stop_loss=entry_price - atr_14 * Decimal("1.5"),
        take_profit=entry_price + atr_14 * Decimal("2.0"),
    )


def detect_long_protective_exit(
    candle: Candle,
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
) -> tuple[str, Decimal] | None:
    """Проверяет, сработал ли SL/TP на закрытой свече.

    Порядок внутри свечи нам неизвестен, поэтому при одновременном достижении
    обоих уровней используется консервативное правило: сначала считаем stop-loss.
    """

    if stop_loss is None or take_profit is None:
        return None

    if candle.low <= stop_loss:
        return ("STOP_LOSS", stop_loss)
    if candle.high >= take_profit:
        return ("TAKE_PROFIT", take_profit)
    return None
