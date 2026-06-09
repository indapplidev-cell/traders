from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MlPredictions


class PredictionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: dict[str, Any]) -> MlPredictions:
        row = MlPredictions(**payload)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_recent(self, limit: int = 100) -> list[MlPredictions]:
        statement = select(MlPredictions).order_by(MlPredictions.created_at.desc(), MlPredictions.id.desc()).limit(limit)
        return list(self._session.scalars(statement))
