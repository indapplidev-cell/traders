from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import MlFeatures


class FeatureRepository:
    UPSERT_BATCH_SIZE = 500

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, features: list[dict[str, Any]]) -> int:
        if not features:
            return 0

        for start in range(0, len(features), self.UPSERT_BATCH_SIZE):
            batch = features[start : start + self.UPSERT_BATCH_SIZE]
            statement = self._build_insert_statement(batch)
            excluded = statement.excluded
            update_columns = {
                column.name: getattr(excluded, column.name)
                for column in MlFeatures.__table__.columns
                if column.name not in {"id", "created_at"}
            }
            upsert_statement = statement.on_conflict_do_update(
                index_elements=["symbol", "interval", "candle_open_time", "feature_version"],
                set_=update_columns,
            )
            self._session.execute(upsert_statement)
        self._session.commit()
        return len(features)

    def get_all(self, symbol: str, interval: str, feature_version: str) -> list[MlFeatures]:
        statement = (
            select(MlFeatures)
            .where(MlFeatures.symbol == symbol)
            .where(MlFeatures.interval == interval)
            .where(MlFeatures.feature_version == feature_version)
            .order_by(MlFeatures.candle_open_time.asc())
        )
        return list(self._session.scalars(statement))

    def _build_insert_statement(self, features: list[dict[str, Any]]):
        dialect_name = self._session.bind.dialect.name if self._session.bind is not None else ""
        if dialect_name == "postgresql":
            return postgresql_insert(MlFeatures).values(features)
        if dialect_name == "sqlite":
            return sqlite_insert(MlFeatures).values(features)
        raise ValueError(f"Unsupported database dialect for feature upsert: {dialect_name}")
