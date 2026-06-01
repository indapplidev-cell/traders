"""Расчёт технических индикаторов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Sequence

import pandas as pd

from app.db.models import Candle


def ensure_utc_datetime(value: datetime) -> datetime:
    """Приводит naive/aware datetime к aware UTC.

    SQLite и некоторые DB-драйверы могут вернуть timezone-naive datetime,
    даже если модель объявлена как DateTime(timezone=True). Внутри проекта
    считаем такие значения UTC, чтобы не ломать сравнения и backtest.
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class IndicatorCalculationError(ValueError):
    """Ошибка расчёта индикаторов при нехватке или некорректности данных."""


@dataclass(slots=True)
class IndicatorSnapshot:
    """Снимок последних значений индикаторов.

    Значения возвращаются как Decimal, чтобы итоговые торговые решения
    не зависели от двоичной погрешности float.
    """

    ema_20: Decimal
    ema_50: Decimal
    ema_200: Decimal
    rsi_14: Decimal
    atr_14: Decimal
    volume_sma_20: Decimal
    last_close: Decimal
    last_volume: Decimal


class IndicatorService:
    """Сервис расчёта индикаторов по закрытым свечам."""

    MIN_CANDLES = 200

    def calculate(self, candles: Sequence[Candle]) -> IndicatorSnapshot:
        """Считает индикаторы по историческим свечам.

        Расчёт идёт только по закрытым свечам. Это важное ограничение:
        незакрытая свеча может резко изменить форму до конца интервала,
        а значит решение на её основе будет нестабильным.
        """

        closed_candles = self._only_closed_candles(candles)
        if len(closed_candles) < self.MIN_CANDLES:
            raise IndicatorCalculationError(
                f"Недостаточно закрытых свечей для расчёта индикаторов: нужно минимум {self.MIN_CANDLES}, "
                f"получено {len(closed_candles)}."
            )

        frame = pd.DataFrame(
            {
                "close": [float(item.close) for item in closed_candles],
                "high": [float(item.high) for item in closed_candles],
                "low": [float(item.low) for item in closed_candles],
                "volume": [float(item.volume) for item in closed_candles],
            }
        )

        frame["ema_20"] = frame["close"].ewm(span=20, adjust=False).mean()
        frame["ema_50"] = frame["close"].ewm(span=50, adjust=False).mean()
        frame["ema_200"] = frame["close"].ewm(span=200, adjust=False).mean()

        delta = frame["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0)
        rsi = 100 - (100 / (1 + rs))

        # Для бокового движения без роста и падения RSI должен быть нейтральным.
        rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50)
        rsi = rsi.mask((avg_gain > 0) & (avg_loss == 0), 100)
        rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)
        frame["rsi_14"] = rsi

        prev_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - prev_close).abs(),
                (frame["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        frame["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        frame["volume_sma_20"] = frame["volume"].rolling(window=20, min_periods=20).mean()

        latest = frame.iloc[-1]
        if latest[["ema_20", "ema_50", "ema_200", "rsi_14", "atr_14", "volume_sma_20"]].isna().any():
            raise IndicatorCalculationError("Не удалось рассчитать индикаторы: часть значений осталась пустой.")

        return IndicatorSnapshot(
            ema_20=self._to_decimal(latest["ema_20"]),
            ema_50=self._to_decimal(latest["ema_50"]),
            ema_200=self._to_decimal(latest["ema_200"]),
            rsi_14=self._to_decimal(latest["rsi_14"]),
            atr_14=self._to_decimal(latest["atr_14"]),
            volume_sma_20=self._to_decimal(latest["volume_sma_20"]),
            last_close=self._to_decimal(latest["close"]),
            last_volume=self._to_decimal(latest["volume"]),
        )

    @staticmethod
    def _only_closed_candles(candles: Sequence[Candle]) -> list[Candle]:
        """Оставляет только закрытые свечи по их времени закрытия."""

        now = datetime.now(UTC)
        return [item for item in candles if ensure_utc_datetime(item.close_time) <= now]

    @staticmethod
    def _to_decimal(value: object) -> Decimal:
        """Аккуратно переводит число из pandas обратно в Decimal."""

        return Decimal(str(round(float(value), 10)))
