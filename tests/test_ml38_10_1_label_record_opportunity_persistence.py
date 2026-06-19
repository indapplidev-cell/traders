from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models import MlLabels
from app.db.repositories.label_repository import LabelRepository
from app.labels.label_models import LabelRecord


REQUIRED_OPPORTUNITY_COLUMNS = {
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
        horizon_candles=8,
        direction_label="UP",
        tp_before_sl=True,
        future_return=0.02,
        future_move_atr=1.25,
        max_favorable_move_atr=1.50,
        max_adverse_move_atr=0.25,
        label_version="lv13_h08_opportunity_ft",
        opportunity_label=1,
        opportunity_direction="UP",
        opportunity_reason="setup_first_touch_long",
        opportunity_score=0.85,
        setup_type="nison_context",
        setup_quality_score=0.75,
        setup_invalidation_distance_atr=0.30,
        setup_expected_move_atr=1.20,
        label_ambiguity_score=0.15,
    )


def test_label_record_to_dict_preserves_opportunity_fields() -> None:
    payload = _label_record().to_dict()

    assert REQUIRED_OPPORTUNITY_COLUMNS.issubset(payload.keys())
    assert payload["opportunity_label"] == 1
    assert payload["opportunity_direction"] == "UP"
    assert payload["opportunity_reason"] == "setup_first_touch_long"
    assert payload["opportunity_score"] == 0.85
    assert payload["setup_type"] == "nison_context"
    assert payload["setup_quality_score"] == 0.75
    assert payload["setup_invalidation_distance_atr"] == 0.30
    assert payload["setup_expected_move_atr"] == 1.20
    assert payload["label_ambiguity_score"] == 0.15


def test_ml_labels_model_exposes_opportunity_columns() -> None:
    model_columns = {column.name for column in MlLabels.__table__.columns}

    assert REQUIRED_OPPORTUNITY_COLUMNS.issubset(model_columns)


def test_label_repository_persists_opportunity_fields_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = LabelRepository(session)
        inserted = repository.upsert_many([_label_record().to_dict()])

        assert inserted == 1

        rows = repository.get_all(
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            label_version="lv13_h08_opportunity_ft",
        )

        assert len(rows) == 1
        row = rows[0]
        assert int(row.opportunity_label) == 1
        assert row.opportunity_direction == "UP"
        assert row.opportunity_reason == "setup_first_touch_long"
        assert float(row.opportunity_score) == 0.85
        assert row.setup_type == "nison_context"
        assert float(row.setup_quality_score) == 0.75
        assert float(row.setup_invalidation_distance_atr) == 0.30
        assert float(row.setup_expected_move_atr) == 1.20
        assert float(row.label_ambiguity_score) == 0.15
