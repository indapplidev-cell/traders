FROM python:3.11-slim

WORKDIR /service

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .
