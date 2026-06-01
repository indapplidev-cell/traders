"""Базовые объекты SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Общая базовая модель для всех ORM-сущностей."""

