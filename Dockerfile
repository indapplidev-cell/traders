FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /service

COPY pyproject.toml README.md ./

RUN python -c "import subprocess, sys, tomllib; dependencies = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', *dependencies])"

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir --no-deps . \
    && rm -rf build *.egg-info
