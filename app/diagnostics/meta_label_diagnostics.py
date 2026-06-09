from __future__ import annotations

from typing import Any

from app.meta_label.meta_label_models import (
    EMA_DIRECTION_LONG,
    EMA_DIRECTION_SHORT,
    META_LABEL_LOSS,
    META_LABEL_WIN,
)


class MetaLabelDiagnostics:
    REGIME_KEYS = [
        "regime_trend_up",
        "regime_trend_down",
        "regime_range",
        "regime_high_volatility",
        "regime_low_volatility",
        "regime_volatility_expanding",
        "regime_volatility_contracting",
        "ema_stack_bullish",
        "ema_stack_bearish",
        "close_above_ema_200",
        "close_below_ema_200",
    ]

    def build_report(self, feature_rows: list[Any], meta_labels: list[Any], feature_version: str, label_version: str) -> dict[str, Any]:
        meta_by_open_time = {row.candle_open_time: row for row in meta_labels}
        valid_pairs = [
            (feature_row, meta_by_open_time[feature_row.candle_open_time])
            for feature_row in feature_rows
            if feature_row.candle_open_time in meta_by_open_time
        ]
        win_rows = [(feature_row, meta_row) for feature_row, meta_row in valid_pairs if meta_row.meta_label == META_LABEL_WIN]
        loss_rows = [(feature_row, meta_row) for feature_row, meta_row in valid_pairs if meta_row.meta_label == META_LABEL_LOSS]
        long_valid_rows = [meta_row for _, meta_row in valid_pairs if meta_row.meta_target_win is not None and meta_row.ema_signal_direction == EMA_DIRECTION_LONG]
        short_valid_rows = [meta_row for _, meta_row in valid_pairs if meta_row.meta_target_win is not None and meta_row.ema_signal_direction == EMA_DIRECTION_SHORT]
        top_separation = self._top_feature_separation(win_rows, loss_rows)
        warnings: list[str] = []
        valid_count = len(win_rows) + len(loss_rows)
        positive_ratio = (len(win_rows) / valid_count) if valid_count else 0.0
        if valid_count and (positive_ratio < 0.25 or positive_ratio > 0.75):
            warnings.append("meta_labels_too_imbalanced")
        if len(win_rows) < 50:
            warnings.append("too_few_wins")
        if len(loss_rows) < 50:
            warnings.append("too_few_losses")
        if not short_valid_rows:
            warnings.append("no_short_meta_signals")
        if not long_valid_rows:
            warnings.append("no_long_meta_signals")
        if top_separation and float(top_separation[0]["win_loss_separation"]) < 0.05:
            warnings.append("weak_feature_separation")
        regime_stats = {
            regime_key: self._regime_stats(regime_key, valid_pairs)
            for regime_key in self.REGIME_KEYS
        }
        return {
            "feature_version": feature_version,
            "label_version": label_version,
            "meta_label_distribution": self._count_by_label(meta_labels),
            "win_loss_balance": {
                "win_count": len(win_rows),
                "loss_count": len(loss_rows),
                "positive_class_ratio": positive_ratio if valid_count else None,
                "negative_class_ratio": (len(loss_rows) / valid_count) if valid_count else None,
            },
            "long_short_win_rates": {
                "long_win_rate": self._win_rate(long_valid_rows),
                "short_win_rate": self._win_rate(short_valid_rows),
            },
            "win_rate_by_regime": {key: value["win_rate"] for key, value in regime_stats.items()},
            "loss_rate_by_regime": {key: value["loss_rate"] for key, value in regime_stats.items()},
            "avg_trade_r_by_regime": {key: value["avg_trade_r"] for key, value in regime_stats.items()},
            "top_features_by_win_loss_separation": top_separation,
            "warnings": warnings,
        }

    @staticmethod
    def _count_by_label(meta_labels: list[Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in meta_labels:
            counts[row.meta_label] = counts.get(row.meta_label, 0) + 1
        return counts

    def _regime_stats(self, regime_key: str, pairs: list[tuple[Any, Any]]) -> dict[str, float | int | None]:
        filtered = [
            meta_row
            for feature_row, meta_row in pairs
            if meta_row.meta_target_win is not None and self._segment_match(feature_row.features_json, regime_key)
        ]
        if not filtered:
            return {"row_count": 0, "win_rate": None, "loss_rate": None, "avg_trade_r": None}
        wins = sum(1 for row in filtered if row.meta_target_win == 1)
        losses = sum(1 for row in filtered if row.meta_target_win == 0)
        return {
            "row_count": len(filtered),
            "win_rate": wins / len(filtered),
            "loss_rate": losses / len(filtered),
            "avg_trade_r": sum(float(row.meta_trade_r) for row in filtered if row.meta_trade_r is not None) / len(filtered),
        }

    def _top_feature_separation(self, win_rows: list[tuple[Any, Any]], loss_rows: list[tuple[Any, Any]]) -> list[dict[str, Any]]:
        if not win_rows or not loss_rows:
            return []
        sample_keys = sorted(set(win_rows[0][0].features_json) & set(loss_rows[0][0].features_json))
        scored = []
        for key in sample_keys:
            win_values = [float(feature_row.features_json[key]) for feature_row, _ in win_rows if feature_row.features_json.get(key) is not None]
            loss_values = [float(feature_row.features_json[key]) for feature_row, _ in loss_rows if feature_row.features_json.get(key) is not None]
            if not win_values or not loss_values:
                continue
            win_mean = sum(win_values) / len(win_values)
            loss_mean = sum(loss_values) / len(loss_values)
            scored.append(
                {
                    "feature_name": key,
                    "win_mean": win_mean,
                    "loss_mean": loss_mean,
                    "win_loss_separation": abs(win_mean - loss_mean),
                }
            )
        return sorted(scored, key=lambda item: float(item["win_loss_separation"]), reverse=True)[:10]

    @staticmethod
    def _segment_match(features_json: dict[str, float | None], regime_key: str) -> bool:
        if regime_key == "close_below_ema_200":
            value = features_json.get("close_above_ema_200")
            return value is not None and float(value) == 0.0
        value = features_json.get(regime_key)
        return value is not None and float(value) == 1.0

    @staticmethod
    def _win_rate(rows: list[Any]) -> float | None:
        if not rows:
            return None
        wins = sum(1 for row in rows if row.meta_target_win == 1)
        return wins / len(rows)
