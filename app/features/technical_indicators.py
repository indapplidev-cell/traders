from __future__ import annotations

import math


class TechnicalIndicators:
    @staticmethod
    def ema(values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        if period <= 0 or len(values) < period:
            return result

        seed = sum(values[:period]) / period
        result[period - 1] = seed
        multiplier = 2 / (period + 1)
        previous = seed

        for index in range(period, len(values)):
            previous = (values[index] - previous) * multiplier + previous
            result[index] = previous

        return result

    @staticmethod
    def sma(values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        if period <= 0 or len(values) < period:
            return result

        window_sum = sum(values[:period])
        result[period - 1] = window_sum / period

        for index in range(period, len(values)):
            window_sum += values[index] - values[index - period]
            result[index] = window_sum / period

        return result

    @staticmethod
    def rolling_stddev(values: list[float | None], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        if period <= 0:
            return result

        for index in range(period - 1, len(values)):
            window = values[index - period + 1 : index + 1]
            if any(value is None for value in window):
                continue
            numeric_window = [float(value) for value in window if value is not None]
            mean = sum(numeric_window) / period
            variance = sum((value - mean) ** 2 for value in numeric_window) / period
            result[index] = math.sqrt(variance)

        return result

    @staticmethod
    def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
        result: list[float] = []
        for index in range(len(highs)):
            if index == 0:
                result.append(highs[index] - lows[index])
                continue
            result.append(
                max(
                    highs[index] - lows[index],
                    abs(highs[index] - closes[index - 1]),
                    abs(lows[index] - closes[index - 1]),
                )
            )
        return result

    @staticmethod
    def atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float | None]:
        tr_values = TechnicalIndicators.true_range(highs, lows, closes)
        result: list[float | None] = [None] * len(tr_values)
        if period <= 0 or len(tr_values) < period:
            return result

        seed = sum(tr_values[:period]) / period
        result[period - 1] = seed
        previous = seed

        for index in range(period, len(tr_values)):
            previous = ((previous * (period - 1)) + tr_values[index]) / period
            result[index] = previous

        return result

    @staticmethod
    def rsi(closes: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        if period <= 0 or len(closes) <= period:
            return result

        gains: list[float] = [0.0] * len(closes)
        losses: list[float] = [0.0] * len(closes)
        for index in range(1, len(closes)):
            delta = closes[index] - closes[index - 1]
            gains[index] = max(delta, 0.0)
            losses[index] = abs(min(delta, 0.0))

        average_gain = sum(gains[1 : period + 1]) / period
        average_loss = sum(losses[1 : period + 1]) / period
        result[period] = TechnicalIndicators._compute_rsi_value(average_gain, average_loss)

        for index in range(period + 1, len(closes)):
            average_gain = ((average_gain * (period - 1)) + gains[index]) / period
            average_loss = ((average_loss * (period - 1)) + losses[index]) / period
            result[index] = TechnicalIndicators._compute_rsi_value(average_gain, average_loss)

        return result

    @staticmethod
    def macd(
        closes: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> tuple[list[float | None], list[float | None], list[float | None]]:
        ema_fast = TechnicalIndicators.ema(closes, fast_period)
        ema_slow = TechnicalIndicators.ema(closes, slow_period)

        macd_values: list[float | None] = [None] * len(closes)
        for index in range(len(closes)):
            if ema_fast[index] is None or ema_slow[index] is None:
                continue
            macd_values[index] = ema_fast[index] - ema_slow[index]

        signal_values = TechnicalIndicators._ema_nullable(macd_values, signal_period)
        histogram: list[float | None] = [None] * len(closes)
        for index in range(len(closes)):
            if macd_values[index] is None or signal_values[index] is None:
                continue
            histogram[index] = macd_values[index] - signal_values[index]

        return macd_values, signal_values, histogram

    @staticmethod
    def _ema_nullable(values: list[float | None], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        valid_indices = [index for index, value in enumerate(values) if value is not None]
        if period <= 0 or len(valid_indices) < period:
            return result

        seed_indices = valid_indices[:period]
        seed = sum(float(values[index]) for index in seed_indices if values[index] is not None) / period
        seed_result_index = seed_indices[-1]
        result[seed_result_index] = seed
        multiplier = 2 / (period + 1)
        previous = seed

        for index in valid_indices[period:]:
            current = float(values[index])
            previous = (current - previous) * multiplier + previous
            result[index] = previous

        return result

    @staticmethod
    def _compute_rsi_value(average_gain: float, average_loss: float) -> float:
        if average_loss == 0 and average_gain == 0:
            return 50.0
        if average_loss == 0:
            return 100.0
        rs = average_gain / average_loss
        return 100 - (100 / (1 + rs))
