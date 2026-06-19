from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.dataset.dataset_exporter import DatasetExporter
from app.dataset.dataset_models import DatasetRow
from app.dataset.dataset_splitter import DatasetSplitter
from app.dataset.gap_aware_dataset_filter import GapAwareDatasetFilter
from app.labels.opportunity_label_builder import OpportunityLabelBuilder
from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository


class DatasetBuilder:
    def __init__(
        self,
        feature_repository: FeatureRepository,
        label_repository: LabelRepository,
        dataset_splitter: DatasetSplitter | None = None,
        dataset_exporter: DatasetExporter | None = None,
        gap_aware_filter: GapAwareDatasetFilter | None = None,
    ) -> None:
        self._feature_repository = feature_repository
        self._label_repository = label_repository
        self._dataset_splitter = dataset_splitter or DatasetSplitter()
        self._dataset_exporter = dataset_exporter or DatasetExporter()
        self._gap_aware_filter = gap_aware_filter or GapAwareDatasetFilter()
        self._opportunity_label_builder = OpportunityLabelBuilder()

    def build(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        train_end: date | None = None,
        validation_end: date | None = None,
        apply_gap_filter: bool = False,
        gap_count: int = 0,
        missing_open_times: list[str] | None = None,
        gap_lookback_bars: int = 3,
        gap_lookahead_bars: int = 3,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> dict[str, Any]:
        dataset_rows, summary = self.build_rows(
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
            apply_gap_filter=apply_gap_filter,
            gap_count=gap_count,
            missing_open_times=missing_open_times,
            gap_lookback_bars=gap_lookback_bars,
            gap_lookahead_bars=gap_lookahead_bars,
            start_at=start_at,
            end_at=end_at,
        )
        splits = self.split_rows(dataset_rows, train_end=train_end, validation_end=validation_end)
        summary.update(
            {
                "start_at": start_at.isoformat() if start_at is not None else None,
                "end_at": end_at.isoformat() if end_at is not None else None,
                "date_range_limited": start_at is not None and end_at is not None,
                "train_end": train_end.isoformat() if train_end is not None else None,
                "validation_end": validation_end.isoformat() if validation_end is not None else None,
                "train_rows": len(splits["train"]),
                "validation_rows": len(splits["validation"]),
                "test_rows": len(splits["test"]),
                "train_first_open_time": self._first_open_time(splits["train"]),
                "train_last_open_time": self._last_open_time(splits["train"]),
                "validation_first_open_time": self._first_open_time(splits["validation"]),
                "validation_last_open_time": self._last_open_time(splits["validation"]),
                "test_first_open_time": self._first_open_time(splits["test"]),
                "test_last_open_time": self._last_open_time(splits["test"]),
            }
        )
        summary_path = self._dataset_exporter.export_summary(
            summary=summary,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            feature_version=feature_version,
            label_version=label_version,
        )
        summary["summary_path"] = summary_path
        return summary

    def build_rows(
        self,
        symbol: str,
        interval: str,
        horizon_candles: int,
        feature_version: str,
        label_version: str,
        apply_gap_filter: bool = False,
        gap_count: int = 0,
        missing_open_times: list[str] | None = None,
        gap_lookback_bars: int = 3,
        gap_lookahead_bars: int = 3,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> tuple[list[DatasetRow], dict[str, Any]]:
        if start_at is not None and end_at is not None:
            feature_rows = self._feature_repository.get_range(
                symbol=symbol,
                interval=interval,
                feature_version=feature_version,
                start_at=start_at,
                end_at=end_at,
            )
            label_rows = self._label_repository.get_range(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                label_version=label_version,
                start_at=start_at,
                end_at=end_at,
            )
        else:
            feature_rows = self._feature_repository.get_all(
                symbol=symbol,
                interval=interval,
                feature_version=feature_version,
            )
            label_rows = self._label_repository.get_all(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                label_version=label_version,
            )

        labels_by_open_time = {row.candle_open_time: row for row in label_rows}

        dataset_rows: list[DatasetRow] = []
        dropped_incomplete_features = 0
        dropped_missing_labels = 0

        for feature_row in feature_rows:
            if any(value is None for value in feature_row.features_json.values()):
                dropped_incomplete_features += 1
                continue

            label_row = labels_by_open_time.get(feature_row.candle_open_time)
            if label_row is None:
                dropped_missing_labels += 1
                continue
            computed_opportunity_payload = self._opportunity_label_builder.build(
                features_json=feature_row.features_json,
                direction_label=label_row.direction_label,
                tp_before_sl=label_row.tp_before_sl,
                future_move_atr=float(label_row.future_move_atr),
                max_favorable_move_atr=float(label_row.max_favorable_move_atr),
                max_adverse_move_atr=float(label_row.max_adverse_move_atr),
            )
            opportunity_values = self._resolve_opportunity_values(
                label_row=label_row,
                computed_payload=computed_opportunity_payload,
            )

            opportunity_payload = self._resolve_opportunity_payload(
                label_row=label_row,
                features_json=feature_row.features_json,
            )

            dataset_rows.append(
                DatasetRow(
                    symbol=feature_row.symbol,
                    interval=feature_row.interval,
                    candle_open_time=feature_row.candle_open_time,
                    feature_version=feature_row.feature_version,
                    label_version=label_row.label_version,
                    horizon_candles=label_row.horizon_candles,
                    features_json=dict(feature_row.features_json),
                    direction_label=label_row.direction_label,
                    tp_before_sl=label_row.tp_before_sl,
                    future_return=float(label_row.future_return),
                    future_move_atr=float(label_row.future_move_atr),
                    max_favorable_move_atr=float(label_row.max_favorable_move_atr),
                    max_adverse_move_atr=float(label_row.max_adverse_move_atr),
                    opportunity_label=int(opportunity_payload["opportunity_label"]),
                    opportunity_direction=str(opportunity_payload["opportunity_direction"]),
                    opportunity_reason=str(opportunity_payload["opportunity_reason"]),
                    opportunity_score=float(opportunity_payload["opportunity_score"]),
                    setup_type=str(opportunity_payload["setup_type"]),
                    setup_quality_score=float(opportunity_payload["setup_quality_score"]),
                    setup_invalidation_distance_atr=float(opportunity_payload["setup_invalidation_distance_atr"]),
                    setup_expected_move_atr=float(opportunity_payload["setup_expected_move_atr"]),
                    label_ambiguity_score=float(opportunity_payload["label_ambiguity_score"]),
                )
            )

        summary = {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "feature_version": feature_version,
            "label_version": label_version,
            "start_at": start_at.isoformat() if start_at is not None else None,
            "end_at": end_at.isoformat() if end_at is not None else None,
            "date_range_limited": start_at is not None and end_at is not None,
            "feature_rows": len(feature_rows),
            "label_rows": len(label_rows),
            "dataset_rows": len(dataset_rows),
            "dropped_incomplete_features": dropped_incomplete_features,
            "dropped_missing_labels": dropped_missing_labels,
            "opportunity_rows": sum(int(row.opportunity_label) for row in dataset_rows),
            "no_trade_rows": sum(int(not row.opportunity_label) for row in dataset_rows),
        }
        if apply_gap_filter or gap_count > 0 or missing_open_times:
            dataset_rows, gap_filter_summary = self._gap_aware_filter.apply(
                rows=dataset_rows,
                symbol=symbol,
                interval=interval,
                gap_count=gap_count,
                missing_open_times=missing_open_times,
                lookback_bars=gap_lookback_bars,
                lookahead_bars=gap_lookahead_bars,
            )
            summary["dataset_rows"] = len(dataset_rows)
            summary["gap_filter_summary"] = gap_filter_summary
        return dataset_rows, summary

    @staticmethod
    def _resolve_opportunity_values(label_row: Any, computed_payload: Any) -> dict[str, Any]:
        if not DatasetBuilder._has_persisted_opportunity_payload(label_row):
            return computed_payload.to_dict()

        return {
            "opportunity_label": int(getattr(label_row, "opportunity_label", computed_payload.opportunity_label) or 0),
            "opportunity_direction": str(
                getattr(label_row, "opportunity_direction", computed_payload.opportunity_direction) or "NONE"
            ),
            "opportunity_reason": str(
                getattr(label_row, "opportunity_reason", computed_payload.opportunity_reason) or "no_setup"
            ),
            "opportunity_score": float(
                getattr(label_row, "opportunity_score", computed_payload.opportunity_score) or 0.0
            ),
            "setup_type": str(getattr(label_row, "setup_type", computed_payload.setup_type) or "no_setup"),
            "setup_quality_score": float(
                getattr(label_row, "setup_quality_score", computed_payload.setup_quality_score) or 0.0
            ),
            "setup_invalidation_distance_atr": float(
                getattr(
                    label_row,
                    "setup_invalidation_distance_atr",
                    computed_payload.setup_invalidation_distance_atr,
                )
                or 0.0
            ),
            "setup_expected_move_atr": float(
                getattr(label_row, "setup_expected_move_atr", computed_payload.setup_expected_move_atr) or 0.0
            ),
            "label_ambiguity_score": float(
                getattr(label_row, "label_ambiguity_score", computed_payload.label_ambiguity_score) or 1.0
            ),
        }

    @staticmethod
    def _has_persisted_opportunity_payload(label_row: Any) -> bool:
        required_fields = (
            "opportunity_label",
            "opportunity_direction",
            "opportunity_reason",
            "opportunity_score",
            "setup_type",
            "setup_quality_score",
            "setup_invalidation_distance_atr",
            "setup_expected_move_atr",
            "label_ambiguity_score",
        )
        if not all(hasattr(label_row, field_name) for field_name in required_fields):
            return False

        opportunity_label = int(getattr(label_row, "opportunity_label", 0) or 0)
        opportunity_direction = str(getattr(label_row, "opportunity_direction", "NONE") or "NONE")
        setup_type = str(getattr(label_row, "setup_type", "no_setup") or "no_setup")
        opportunity_score = float(getattr(label_row, "opportunity_score", 0.0) or 0.0)
        setup_quality_score = float(getattr(label_row, "setup_quality_score", 0.0) or 0.0)
        label_ambiguity_score = float(getattr(label_row, "label_ambiguity_score", 1.0) or 1.0)

        return any(
            (
                opportunity_label == 1,
                opportunity_direction != "NONE",
                setup_type != "no_setup",
                opportunity_score > 0.0,
                setup_quality_score > 0.0,
                label_ambiguity_score != 1.0,
            )
        )

    def split_rows(
        self,
        dataset_rows: list[DatasetRow],
        train_end: date | None = None,
        validation_end: date | None = None,
    ) -> dict[str, list[DatasetRow]]:
        splitter = self._dataset_splitter
        if train_end is not None or validation_end is not None:
            splitter = DatasetSplitter(train_end=train_end, validation_end=validation_end)
        return splitter.split(dataset_rows)

    def _resolve_opportunity_payload(self, *, label_row: Any, features_json: dict[str, Any]) -> dict[str, Any]:
        if self._has_persisted_opportunity_payload(label_row):
            return {
                "opportunity_label": int(getattr(label_row, "opportunity_label", 0) or 0),
                "opportunity_direction": str(getattr(label_row, "opportunity_direction", "NONE") or "NONE"),
                "opportunity_reason": str(getattr(label_row, "opportunity_reason", "no_setup") or "no_setup"),
                "opportunity_score": float(getattr(label_row, "opportunity_score", 0.0) or 0.0),
                "setup_type": str(getattr(label_row, "setup_type", "no_setup") or "no_setup"),
                "setup_quality_score": float(getattr(label_row, "setup_quality_score", 0.0) or 0.0),
                "setup_invalidation_distance_atr": float(
                    getattr(label_row, "setup_invalidation_distance_atr", 0.0) or 0.0
                ),
                "setup_expected_move_atr": float(getattr(label_row, "setup_expected_move_atr", 0.0) or 0.0),
                "label_ambiguity_score": float(getattr(label_row, "label_ambiguity_score", 1.0) or 1.0),
            }

        return self._opportunity_label_builder.build(
            features_json=features_json,
            direction_label=label_row.direction_label,
            tp_before_sl=label_row.tp_before_sl,
            future_move_atr=float(label_row.future_move_atr),
            max_favorable_move_atr=float(label_row.max_favorable_move_atr),
            max_adverse_move_atr=float(label_row.max_adverse_move_atr),
        ).to_dict()

    @staticmethod
    def _has_persisted_opportunity_payload(label_row: Any) -> bool:
        return all(
            hasattr(label_row, field_name)
            for field_name in (
                "opportunity_label",
                "opportunity_direction",
                "opportunity_reason",
                "opportunity_score",
                "setup_type",
                "setup_quality_score",
                "setup_invalidation_distance_atr",
                "setup_expected_move_atr",
                "label_ambiguity_score",
            )
        )

    @staticmethod
    def _first_open_time(rows: list[DatasetRow]) -> str | None:
        return rows[0].candle_open_time.isoformat() if rows else None

    @staticmethod
    def _last_open_time(rows: list[DatasetRow]) -> str | None:
        return rows[-1].candle_open_time.isoformat() if rows else None
