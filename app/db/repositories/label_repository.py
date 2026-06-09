from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import MlLabels


class LabelRepository:
    UPSERT_BATCH_SIZE = 500

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, labels: list[dict[str, Any]]) -> int:
        if not labels:
            return 0

        for start in range(0, len(labels), self.UPSERT_BATCH_SIZE):
            batch = labels[start : start + self.UPSERT_BATCH_SIZE]
            statement = self._build_insert_statement(batch)
            excluded = statement.excluded
            update_columns = {
                column.name: getattr(excluded, column.name)
                for column in MlLabels.__table__.columns
                if column.name not in {"id", "created_at"}
            }
            upsert_statement = statement.on_conflict_do_update(
                index_elements=["symbol", "interval", "candle_open_time", "horizon_candles", "label_version"],
                set_=update_columns,
            )
            self._session.execute(upsert_statement)
        self._session.commit()
        return len(labels)

    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str) -> list[MlLabels]:
        statement = (
            select(MlLabels)
            .where(MlLabels.symbol == symbol)
            .where(MlLabels.interval == interval)
            .where(MlLabels.horizon_candles == horizon_candles)
            .where(MlLabels.label_version == label_version)
            .order_by(MlLabels.candle_open_time.asc())
        )
        return list(self._session.scalars(statement))

    def _build_insert_statement(self, labels: list[dict[str, Any]]):
        dialect_name = self._session.bind.dialect.name if self._session.bind is not None else ""
        if dialect_name == "postgresql":
            return postgresql_insert(MlLabels).values(labels)
        if dialect_name == "sqlite":
            return sqlite_insert(MlLabels).values(labels)
        raise ValueError(f"Unsupported database dialect for label upsert: {dialect_name}")
