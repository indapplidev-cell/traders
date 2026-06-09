from __future__ import annotations

from datetime import date
from typing import Any

from app.dataset.dataset_splitter import DatasetSplitter
from app.features.feature_models import feature_names_for_version
from app.meta_label.meta_label_models import (
    EMA_DIRECTION_LONG,
    META_LABEL_LOSS,
    META_LABEL_WIN,
    MetaDatasetRow,
    MetaLabelRecord,
)


class MetaDatasetBuilder:
    def __init__(self, dataset_splitter: DatasetSplitter | None = None) -> None:
        self._dataset_splitter = dataset_splitter or DatasetSplitter()

    def build_rows(
        self,
        feature_rows: list[Any],
        meta_labels: list[MetaLabelRecord],
        feature_version: str,
    ) -> tuple[list[MetaDatasetRow], dict[str, Any]]:
        feature_names = feature_names_for_version(feature_version)
        labels_by_open_time = {row.candle_open_time: row for row in meta_labels}
        dataset_rows: list[MetaDatasetRow] = []
        excluded_no_trade = 0
        excluded_ambiguous = 0
        excluded_no_exit = 0

        for feature_row in feature_rows:
            meta_row = labels_by_open_time.get(feature_row.candle_open_time)
            if meta_row is None:
                continue
            if meta_row.meta_label not in {META_LABEL_WIN, META_LABEL_LOSS}:
                if meta_row.meta_label == "NO_TRADE":
                    excluded_no_trade += 1
                elif meta_row.meta_label == "AMBIGUOUS":
                    excluded_ambiguous += 1
                elif meta_row.meta_label == "NO_EXIT":
                    excluded_no_exit += 1
                continue
            if any(feature_row.features_json.get(name) is None for name in feature_names):
                continue
            if meta_row.ema_signal_strength_atr is None or meta_row.meta_trade_r is None:
                continue

            features_json = dict(feature_row.features_json)
            features_json["ema_signal_direction_encoded"] = 1.0 if meta_row.ema_signal_direction == EMA_DIRECTION_LONG else -1.0
            features_json["ema_signal_strength_atr"] = float(meta_row.ema_signal_strength_atr)
            dataset_rows.append(
                MetaDatasetRow(
                    symbol=feature_row.symbol,
                    interval=feature_row.interval,
                    candle_open_time=feature_row.candle_open_time,
                    feature_version=feature_version,
                    label_version=meta_row.label_version,
                    horizon_candles=meta_row.horizon_candles,
                    features_json=features_json,
                    ema_signal_direction=meta_row.ema_signal_direction,
                    ema_signal_strength_atr=float(meta_row.ema_signal_strength_atr),
                    meta_trade_r=float(meta_row.meta_trade_r),
                    meta_target_win=int(meta_row.meta_target_win),
                )
            )

        positives = [row for row in dataset_rows if row.meta_target_win == 1]
        negatives = [row for row in dataset_rows if row.meta_target_win == 0]
        long_rows = [row for row in dataset_rows if row.ema_signal_direction == EMA_DIRECTION_LONG]
        short_rows = [row for row in dataset_rows if row.ema_signal_direction != EMA_DIRECTION_LONG]
        summary = {
            "dataset_rows": len(dataset_rows),
            "positive_class_ratio": (len(positives) / len(dataset_rows)) if dataset_rows else 0.0,
            "negative_class_ratio": (len(negatives) / len(dataset_rows)) if dataset_rows else 0.0,
            "long_rows": len(long_rows),
            "short_rows": len(short_rows),
            "excluded_no_trade": excluded_no_trade,
            "excluded_ambiguous": excluded_ambiguous,
            "excluded_no_exit": excluded_no_exit,
            "meta_dataset_valid": (
                len(dataset_rows) >= 1000
                and 0.25 <= ((len(positives) / len(dataset_rows)) if dataset_rows else 0.0) <= 0.75
                and len(long_rows) > 0
                and len(short_rows) > 0
            ),
        }
        return dataset_rows, summary

    def split_rows(
        self,
        dataset_rows: list[MetaDatasetRow],
        train_end: date | None = None,
        validation_end: date | None = None,
    ) -> dict[str, list[MetaDatasetRow]]:
        splitter = self._dataset_splitter
        if train_end is not None or validation_end is not None:
            splitter = DatasetSplitter(train_end=train_end, validation_end=validation_end)
        return splitter.split(dataset_rows)
