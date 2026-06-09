from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MlReplayResults, MlReplaySessions


class ReplayRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_session(self, payload: dict[str, Any]) -> MlReplaySessions:
        row = MlReplaySessions(**payload)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_session(self, session_id: str, **values: Any) -> None:
        row = self.get_session(session_id)
        if row is None:
            raise ValueError(f"Unknown replay session_id: {session_id}")
        for key, value in values.items():
            setattr(row, key, value)
        self._session.commit()

    def add_results(self, payloads: list[dict[str, Any]]) -> int:
        if not payloads:
            return 0
        rows = [MlReplayResults(**payload) for payload in payloads]
        self._session.add_all(rows)
        self._session.commit()
        return len(rows)

    def get_session(self, session_id: str) -> MlReplaySessions | None:
        statement = select(MlReplaySessions).where(MlReplaySessions.session_id == session_id)
        return self._session.scalar(statement)

    def list_sessions(self) -> list[dict[str, Any]]:
        statement = select(MlReplaySessions).order_by(MlReplaySessions.created_at.desc(), MlReplaySessions.id.desc())
        rows = list(self._session.scalars(statement))
        return [
            {
                "session_id": row.session_id,
                "model_version": row.model_version,
                "symbol": row.symbol,
                "interval": row.interval,
                "start_at": row.start_at.isoformat(),
                "end_at": row.end_at.isoformat(),
                "status": row.status,
                "metrics_json": row.metrics_json,
                "created_at": row.created_at.isoformat() if row.created_at is not None else None,
            }
            for row in rows
        ]
