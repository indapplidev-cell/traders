from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import MlModelVersions


class ModelRegistryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: dict[str, Any]) -> MlModelVersions:
        row = MlModelVersions(**payload)
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError:
            # Важно: после ошибки unique constraint SQLAlchemy session остаётся в broken state.
            # Rollback обязателен, иначе последующие записи training_run тоже могут упасть.
            self._session.rollback()
            raise
        self._session.refresh(row)
        return row

    def list_all(self) -> list[dict[str, Any]]:
        statement = select(MlModelVersions).order_by(MlModelVersions.created_at.desc(), MlModelVersions.id.desc())
        rows = list(self._session.scalars(statement))
        return [
            {
                "model_version": row.model_version,
                "model_name": row.model_name,
                "symbol": row.symbol,
                "interval": row.interval,
                "horizon_candles": row.horizon_candles,
                "feature_version": row.feature_version,
                "label_version": row.label_version,
                "accuracy": float(row.accuracy) if row.accuracy is not None else None,
                "brier_score": float(row.brier_score) if row.brier_score is not None else None,
                "is_active": bool(row.is_active),
                "artifact_path": row.artifact_path,
                "created_at": row.created_at.isoformat() if row.created_at is not None else None,
            }
            for row in rows
        ]

    def get_by_model_version(self, model_version: str) -> MlModelVersions | None:
        statement = select(MlModelVersions).where(MlModelVersions.model_version == model_version)
        return self._session.scalar(statement)

    def get_active_model(self, symbol: str, interval: str, horizon_candles: int) -> MlModelVersions | None:
        statement = (
            select(MlModelVersions)
            .where(MlModelVersions.symbol == symbol)
            .where(MlModelVersions.interval == interval)
            .where(MlModelVersions.horizon_candles == horizon_candles)
            .where(MlModelVersions.is_active.is_(True))
            .order_by(MlModelVersions.created_at.desc(), MlModelVersions.id.desc())
        )
        return self._session.scalar(statement)

    def deactivate_scope(self, symbol: str, interval: str, horizon_candles: int) -> None:
        statement = (
            update(MlModelVersions)
            .where(MlModelVersions.symbol == symbol)
            .where(MlModelVersions.interval == interval)
            .where(MlModelVersions.horizon_candles == horizon_candles)
            .values(is_active=False)
        )
        self._session.execute(statement)
        self._session.commit()

    def set_active(self, model_version: str, is_active: bool) -> None:
        statement = (
            update(MlModelVersions)
            .where(MlModelVersions.model_version == model_version)
            .values(is_active=is_active)
        )
        self._session.execute(statement)
        self._session.commit()
