from datetime import datetime, timezone

import pytest

from app.training.training_service import TrainingService


class StopAfterBuildRows(Exception):
    pass


def test_training_service_passes_date_range_to_dataset_builder() -> None:
    dataset_builder = CapturingDatasetBuilder()
    training_run_repository = FakeTrainingRunRepository()
    service = TrainingService(
        dataset_builder=dataset_builder,
        model_registry=object(),
        training_run_repository=training_run_repository,
        artifact_storage=object(),
    )

    start_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 6, 16, tzinfo=timezone.utc)

    with pytest.raises(StopAfterBuildRows):
        service.train(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            feature_version="fv3_candle_ta_context",
            label_version="lv2_h08_thr03_tp10_sl10",
            model_name="candle_mlp",
            start_at=start_at,
            end_at=end_at,
        )

    assert dataset_builder.received_start_at == start_at
    assert dataset_builder.received_end_at == end_at
    assert training_run_repository.created_payloads
    assert training_run_repository.finished_status == "failed"


class CapturingDatasetBuilder:
    def __init__(self) -> None:
        self.received_start_at = None
        self.received_end_at = None

    def build_rows(self, **kwargs):
        self.received_start_at = kwargs.get("start_at")
        self.received_end_at = kwargs.get("end_at")
        raise StopAfterBuildRows("stop after capturing date range")


class FakeTrainingRunRepository:
    def __init__(self) -> None:
        self.created_payloads = []
        self.finished_status = None

    def create(self, payload):
        self.created_payloads.append(payload)
        return payload

    def finish(self, run_id, status, finished_at, metrics_json, error_message):
        self.finished_status = status


# ВАЖНО:
# Если существующие fake-классы из tests/test_training_service.py удобнее переиспользовать,
# можно импортировать/скопировать их оттуда. Главное — assert на received_start_at/end_at.
