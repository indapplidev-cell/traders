from __future__ import annotations

from typing import Any

from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


class TpSlLabelBuilder:
    def build(
        self,
        direction_label: str,
        current_close: float,
        atr: float,
        future_candles: list[Any],
        take_profit_atr: float = 1.5,
        stop_loss_atr: float = 1.0,
    ) -> bool | None:
        if direction_label == LABEL_FLAT:
            return None

        if direction_label == LABEL_UP:
            take_profit = current_close + (take_profit_atr * atr)
            stop_loss = current_close - (stop_loss_atr * atr)
            return self._resolve_long_path(take_profit, stop_loss, future_candles)

        if direction_label == LABEL_DOWN:
            take_profit = current_close - (take_profit_atr * atr)
            stop_loss = current_close + (stop_loss_atr * atr)
            return self._resolve_short_path(take_profit, stop_loss, future_candles)

        return None

    @staticmethod
    def _resolve_long_path(take_profit: float, stop_loss: float, future_candles: list[Any]) -> bool | None:
        for candle in future_candles:
            tp_hit = float(candle.high) >= take_profit
            sl_hit = float(candle.low) <= stop_loss
            if tp_hit and sl_hit:
                return None
            if tp_hit:
                return True
            if sl_hit:
                return False
        return None

    @staticmethod
    def _resolve_short_path(take_profit: float, stop_loss: float, future_candles: list[Any]) -> bool | None:
        for candle in future_candles:
            tp_hit = float(candle.low) <= take_profit
            sl_hit = float(candle.high) >= stop_loss
            if tp_hit and sl_hit:
                return None
            if tp_hit:
                return True
            if sl_hit:
                return False
        return None
