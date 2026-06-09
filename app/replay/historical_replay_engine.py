from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.labels.label_builder import LabelBuilder
from app.replay.replay_models import ReplayResultRecord


class HistoricalReplayEngine:
    def __init__(self, candle_repository, predictor, replay_repository, reports_dir: Path | None = None) -> None:
        self._candle_repository = candle_repository
        self._predictor = predictor
        self._replay_repository = replay_repository
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        model_version: str,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
        horizon_candles: int,
    ) -> dict[str, Any]:
        session_id = f"replay_{model_version}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self._replay_repository.create_session(
            {
                "session_id": session_id,
                "model_version": model_version,
                "symbol": symbol,
                "interval": interval,
                "start_at": start_at,
                "end_at": end_at,
                "status": "running",
                "metrics_json": None,
            }
        )

        candles = self._candle_repository.get_all(symbol=symbol, interval=interval)
        labels = LabelBuilder().build(
            candles=candles,
            symbol=symbol,
            interval=interval,
            horizon_candles=horizon_candles,
            label_version="replay",
        )
        labels_by_open_time = {label.candle_open_time: label for label in labels}
        prepared_runtime = None
        feature_records_by_open_time: dict[datetime, Any] = {}
        if all(
            hasattr(self._predictor, attribute)
            for attribute in ("prepare_runtime", "build_feature_records", "predict_from_feature_record")
        ):
            prepared_runtime = self._predictor.prepare_runtime(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
                model_version=model_version,
            )
            if prepared_runtime is not None:
                feature_records = self._predictor.build_feature_records(
                    candles=candles,
                    symbol=symbol,
                    interval=interval,
                    feature_version=prepared_runtime.model_row.feature_version,
                )
                feature_records_by_open_time = {record.candle_open_time: record for record in feature_records}

        results: list[ReplayResultRecord] = []
        for index, candle in enumerate(candles):
            open_time = candle.open_time.astimezone(timezone.utc) if candle.open_time.tzinfo else candle.open_time.replace(tzinfo=timezone.utc)
            if open_time < start_at or open_time >= end_at:
                continue
            label = labels_by_open_time.get(candle.open_time)
            if label is None:
                continue

            if prepared_runtime is not None:
                feature_record = feature_records_by_open_time.get(candle.open_time)
                if feature_record is None:
                    continue
                prediction = self._predictor.predict_from_feature_record(
                    symbol=symbol,
                    interval=interval,
                    horizon_candles=horizon_candles,
                    feature_record=feature_record,
                    runtime=prepared_runtime,
                    candles=None,
                    context=None,
                    log_prediction=False,
                )
            else:
                prediction = self._predictor.predict(
                    symbol=symbol,
                    interval=interval,
                    horizon_candles=horizon_candles,
                    candles=self._serialize_candles(candles[: index + 1]),
                    context={},
                    model_version=model_version,
                )
            if not prediction.get("ml_available"):
                continue

            actual_direction = label.direction_label
            error_score = 1.0 - prediction[f"prob_{actual_direction.lower()}"]
            results.append(
                ReplayResultRecord(
                    session_id=session_id,
                    model_version=model_version,
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=candle.open_time,
                    predicted_direction=prediction["direction"],
                    actual_direction=actual_direction,
                    prob_up=prediction["prob_up"],
                    prob_down=prediction["prob_down"],
                    prob_flat=prediction["prob_flat"],
                    was_correct=prediction["direction"] == actual_direction,
                    error_score=error_score,
                )
            )

        inserted = self._replay_repository.add_results([record.to_dict() for record in results])
        metrics = self._build_metrics(results)
        report_path = self._write_report(
            session_id=session_id,
            model_version=model_version,
            symbol=symbol,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
            horizon_candles=horizon_candles,
            metrics=metrics,
        )
        metrics["results_written"] = inserted
        metrics["report_path"] = str(report_path)
        self._replay_repository.update_session(session_id, status="completed", metrics_json=metrics)
        return {
            "session_id": session_id,
            "model_version": model_version,
            "symbol": symbol,
            "interval": interval,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "horizon_candles": horizon_candles,
            "results_written": inserted,
            "metrics": metrics,
        }

    @staticmethod
    def _serialize_candles(candles: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "open_time": candle.open_time.isoformat(),
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": str(candle.volume),
                "taker_buy_base_volume": str(candle.taker_buy_base_volume),
            }
            for candle in candles
        ]

    @staticmethod
    def _build_metrics(results: list[ReplayResultRecord]) -> dict[str, Any]:
        total = len(results)
        correct = sum(int(result.was_correct) for result in results)
        label_counts = Counter(result.actual_direction for result in results)
        predicted_counts = Counter(result.predicted_direction for result in results)
        return {
            "rows": total,
            "accuracy": (correct / total) if total else 0.0,
            "average_error_score": (sum(result.error_score for result in results) / total) if total else 0.0,
            "actual_counts": dict(label_counts),
            "predicted_counts": dict(predicted_counts),
        }

    def _write_report(
        self,
        session_id: str,
        model_version: str,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
        horizon_candles: int,
        metrics: dict[str, Any],
    ) -> Path:
        output_path = self._reports_dir / f"{session_id}.md"
        output_path.write_text(
            "\n".join(
                [
                    f"# Replay Report `{session_id}`",
                    "",
                    f"- model_version: `{model_version}`",
                    f"- symbol: `{symbol}`",
                    f"- interval: `{interval}`",
                    f"- horizon_candles: `{horizon_candles}`",
                    f"- start_at: `{start_at.isoformat()}`",
                    f"- end_at: `{end_at.isoformat()}`",
                    f"- rows: `{metrics['rows']}`",
                    f"- accuracy: `{metrics['accuracy']}`",
                    f"- average_error_score: `{metrics['average_error_score']}`",
                ]
            ),
            encoding="utf-8",
        )
        return output_path
