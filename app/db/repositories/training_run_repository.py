from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import MlTrainingRuns


class TrainingRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: dict[str, Any]) -> MlTrainingRuns:
        row = MlTrainingRuns(**payload)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def finish(
        self,
        run_id: str,
        status: str,
        finished_at: datetime,
        metrics_json: dict[str, Any] | None,
        error_message: str | None,
    ) -> None:
        statement = (
            update(MlTrainingRuns)
            .where(MlTrainingRuns.run_id == run_id)
            .values(
                status=status,
                finished_at=finished_at,
                metrics_json=metrics_json,
                error_message=error_message,
            )
        )
        self._session.execute(statement)
        self._session.commit()

    def get_by_run_id(self, run_id: str) -> MlTrainingRuns | None:
        statement = select(MlTrainingRuns).where(MlTrainingRuns.run_id == run_id)
        return self._session.scalar(statement)
