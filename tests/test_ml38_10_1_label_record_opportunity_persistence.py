from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.repositories.label_repository import LabelRepository
from app.labels.label_models import LabelRecord


OPPORTUNITY_FIELDS = {
    "opportunity_label",
    "opportunity_direction",
    "opportunity_reason",
    "opportunity_score",
    "setup_type",
    "setup_quality_score",
    "setup_invalidation_distance_atr",
    "setup_expected_move_atr",
    "label_ambiguity_score",
}


def _label_record() -> LabelRecord:
    return LabelRecord(
        symbol="BTCUSDT",
        interval="15m",
        candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        horizon_candles=12,
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.015,
        future_move_atr=0.75,
        max_favorable_move_atr=1.10,
        max_adverse_move_atr=0.25,
        label_version="lv13_h12_opportunity_ft",
        opportunity_label=1,
        opportunity_direction="UP",
        opportunity_reason="setup_first_touch_long",
        opportunity_score=0.82,
        setup_type="support_retest",
        setup_quality_score=0.77,
        setup_invalidation_distance_atr=0.25,
        setup_expected_move_atr=0.75,
        label_ambiguity_score=0.12,
    )


def test_label_record_to_dict_persists_opportunity_fields() -> None:
    payload = _label_record().to_dict()

    assert OPPORTUNITY_FIELDS.issubset(payload.keys())
    assert payload["opportunity_label"] == 1
    assert payload["opportunity_direction"] == "UP"
    assert payload["opportunity_reason"] == "setup_first_touch_long"
    assert payload["setup_type"] == "support_retest"
    assert payload["label_ambiguity_score"] == 0.12


def test_ml_labels_table_has_opportunity_columns() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("ml_labels")}

    assert OPPORTUNITY_FIELDS.issubset(columns)


def test_label_repository_round_trips_opportunity_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = LabelRepository(session)
        inserted = repository.upsert_many([_label_record().to_dict()])
        assert inserted == 1

        rows = repository.get_all(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=12,
            label_version="lv13_h12_opportunity_ft",
        )

    assert len(rows) == 1
    assert rows[0].opportunity_label == 1
    assert rows[0].opportunity_direction == "UP"
    assert rows[0].opportunity_reason == "setup_first_touch_long"
    assert rows[0].setup_type == "support_retest"
    assert float(rows[0].opportunity_score) == 0.82
    assert float(rows[0].setup_quality_score) == 0.77
    assert float(rows[0].setup_invalidation_distance_atr) == 0.25
    assert float(rows[0].setup_expected_move_atr) == 0.75
    assert float(rows[0].label_ambiguity_score) == 0.12
