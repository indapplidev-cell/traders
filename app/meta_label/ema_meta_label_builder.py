from __future__ import annotations

from collections import Counter
from typing import Any

from app.meta_label.meta_label_models import (
    EMA_DIRECTION_FLAT,
    EMA_DIRECTION_LONG,
    EMA_DIRECTION_SHORT,
    META_LABEL_AMBIGUOUS,
    META_LABEL_LOSS,
    META_LABEL_NO_EXIT,
    META_LABEL_NO_TRADE,
    META_LABEL_WIN,
    MetaLabelRecord,
)


class EmaMetaLabelBuilder:
    def build(
        self,
        feature_rows: list[Any],
        candles: list[Any],
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        horizon_candles: int,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        flat_epsilon_atr: float = 0.05,
    ) -> list[MetaLabelRecord]:
        candles_by_open_time = {row.open_time: row for row in candles}
        index_by_open_time = {row.open_time: index for index, row in enumerate(candles)}
        records: list[MetaLabelRecord] = []

        for feature_row in feature_rows:
            candle_index = index_by_open_time.get(feature_row.candle_open_time)
            if candle_index is None or candle_index + horizon_candles >= len(candles):
                continue

            ema_9 = feature_row.features_json.get("ema_9")
            ema_21 = feature_row.features_json.get("ema_21")
            atr_14 = feature_row.features_json.get("atr_14")
            if ema_9 is None or ema_21 is None or atr_14 is None or float(atr_14) == 0.0:
                continue

            strength_atr = (float(ema_9) - float(ema_21)) / float(atr_14)
            if abs(strength_atr) < flat_epsilon_atr:
                records.append(
                    MetaLabelRecord(
                        symbol=symbol,
                        interval=interval,
                        candle_open_time=feature_row.candle_open_time,
                        feature_version=feature_version,
                        label_version=label_version,
                        horizon_candles=horizon_candles,
                        ema_signal_direction=EMA_DIRECTION_FLAT,
                        ema_signal_strength_atr=strength_atr,
                        meta_label=META_LABEL_NO_TRADE,
                        meta_target_win=None,
                        meta_trade_r=None,
                        meta_same_candle_ambiguous=False,
                    )
                )
                continue

            signal_direction = EMA_DIRECTION_LONG if strength_atr > 0 else EMA_DIRECTION_SHORT
            current_candle = candles_by_open_time[feature_row.candle_open_time]
            future_window = candles[candle_index + 1 : candle_index + 1 + horizon_candles]
            current_close = float(current_candle.close)
            trade_result = self._resolve_trade(
                signal_direction=signal_direction,
                current_close=current_close,
                atr_14=float(atr_14),
                future_candles=future_window,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            records.append(
                MetaLabelRecord(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=feature_row.candle_open_time,
                    feature_version=feature_version,
                    label_version=label_version,
                    horizon_candles=horizon_candles,
                    ema_signal_direction=signal_direction,
                    ema_signal_strength_atr=strength_atr,
                    meta_label=trade_result["meta_label"],
                    meta_target_win=trade_result["meta_target_win"],
                    meta_trade_r=trade_result["meta_trade_r"],
                    meta_same_candle_ambiguous=trade_result["meta_same_candle_ambiguous"],
                )
            )

        return records

    def summarize(self, records: list[MetaLabelRecord]) -> dict[str, Any]:
        meta_counts = Counter(record.meta_label for record in records)
        direction_counts = Counter(record.ema_signal_direction for record in records)
        win_rows = [record for record in records if record.meta_label == META_LABEL_WIN]
        loss_rows = [record for record in records if record.meta_label == META_LABEL_LOSS]
        valid_trade_rows = [record for record in records if record.meta_trade_r is not None]
        long_trade_rows = [record for record in records if record.ema_signal_direction == EMA_DIRECTION_LONG and record.meta_target_win is not None]
        short_trade_rows = [record for record in records if record.ema_signal_direction == EMA_DIRECTION_SHORT and record.meta_target_win is not None]
        return {
            "total_rows": len(records),
            "ema_long_count": direction_counts.get(EMA_DIRECTION_LONG, 0),
            "ema_short_count": direction_counts.get(EMA_DIRECTION_SHORT, 0),
            "ema_flat_count": direction_counts.get(EMA_DIRECTION_FLAT, 0),
            "meta_win_count": meta_counts.get(META_LABEL_WIN, 0),
            "meta_loss_count": meta_counts.get(META_LABEL_LOSS, 0),
            "ambiguous_count": meta_counts.get(META_LABEL_AMBIGUOUS, 0),
            "no_exit_count": meta_counts.get(META_LABEL_NO_EXIT, 0),
            "no_trade_count": meta_counts.get(META_LABEL_NO_TRADE, 0),
            "win_rate": (len(win_rows) / (len(win_rows) + len(loss_rows))) if (win_rows or loss_rows) else None,
            "long_win_rate": self._win_rate(long_trade_rows),
            "short_win_rate": self._win_rate(short_trade_rows),
            "avg_meta_trade_r": (sum(float(row.meta_trade_r) for row in valid_trade_rows) / len(valid_trade_rows)) if valid_trade_rows else None,
            "total_meta_trade_r": sum(float(row.meta_trade_r) for row in valid_trade_rows),
        }

    def _resolve_trade(
        self,
        signal_direction: str,
        current_close: float,
        atr_14: float,
        future_candles: list[Any],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if signal_direction == EMA_DIRECTION_LONG:
            take_profit = current_close + (take_profit_atr * atr_14)
            stop_loss = current_close - (stop_loss_atr * atr_14)
            for candle in future_candles:
                tp_hit = float(candle.high) >= take_profit
                sl_hit = float(candle.low) <= stop_loss
                if tp_hit and sl_hit:
                    return self._resolve_ambiguous(take_profit_atr, stop_loss_atr, fee_r, slippage_r, same_candle_policy)
                if tp_hit:
                    return self._trade_payload(META_LABEL_WIN, 1, (take_profit_atr / stop_loss_atr) - fee_r - slippage_r, False)
                if sl_hit:
                    return self._trade_payload(META_LABEL_LOSS, 0, -1.0 - fee_r - slippage_r, False)
            final_close = float(future_candles[-1].close)
            raw_r = (final_close - current_close) / (stop_loss_atr * atr_14)
            return self._trade_payload(META_LABEL_NO_EXIT, None, raw_r - fee_r - slippage_r, False)

        take_profit = current_close - (take_profit_atr * atr_14)
        stop_loss = current_close + (stop_loss_atr * atr_14)
        for candle in future_candles:
            tp_hit = float(candle.low) <= take_profit
            sl_hit = float(candle.high) >= stop_loss
            if tp_hit and sl_hit:
                return self._resolve_ambiguous(take_profit_atr, stop_loss_atr, fee_r, slippage_r, same_candle_policy)
            if tp_hit:
                return self._trade_payload(META_LABEL_WIN, 1, (take_profit_atr / stop_loss_atr) - fee_r - slippage_r, False)
            if sl_hit:
                return self._trade_payload(META_LABEL_LOSS, 0, -1.0 - fee_r - slippage_r, False)
        final_close = float(future_candles[-1].close)
        raw_r = (current_close - final_close) / (stop_loss_atr * atr_14)
        return self._trade_payload(META_LABEL_NO_EXIT, None, raw_r - fee_r - slippage_r, False)

    @staticmethod
    def _resolve_ambiguous(
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if same_candle_policy == "conservative":
            return EmaMetaLabelBuilder._trade_payload(META_LABEL_LOSS, 0, -1.0 - fee_r - slippage_r, True)
        if same_candle_policy == "optimistic":
            return EmaMetaLabelBuilder._trade_payload(
                META_LABEL_WIN,
                1,
                (take_profit_atr / stop_loss_atr) - fee_r - slippage_r,
                True,
            )
        if same_candle_policy == "skip":
            return EmaMetaLabelBuilder._trade_payload(META_LABEL_AMBIGUOUS, None, None, True)
        raise ValueError(f"Unsupported same_candle_policy: {same_candle_policy}")

    @staticmethod
    def _trade_payload(meta_label: str, meta_target_win: int | None, meta_trade_r: float | None, ambiguous: bool) -> dict[str, Any]:
        return {
            "meta_label": meta_label,
            "meta_target_win": meta_target_win,
            "meta_trade_r": meta_trade_r,
            "meta_same_candle_ambiguous": ambiguous,
        }

    @staticmethod
    def _win_rate(rows: list[MetaLabelRecord]) -> float | None:
        if not rows:
            return None
        wins = sum(1 for row in rows if row.meta_target_win == 1)
        return wins / len(rows)
