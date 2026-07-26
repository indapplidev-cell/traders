FROM python:3.11-slim AS production-base

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

FROM python:3.11-slim AS readonly-api

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRADERS_READONLY_API_HOST=0.0.0.0 \
    TRADERS_READONLY_API_PORT=8080

WORKDIR /service

COPY requirements/api-runtime.lock.txt ./requirements/api-runtime.lock.txt
RUN python -m pip install --no-cache-dir --require-hashes \
        -r requirements/api-runtime.lock.txt

COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m pip install --no-cache-dir --no-deps . \
    && rm -rf build *.egg-info \
    && useradd --system --uid 10001 --create-home traders

USER traders

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=2).read()"]

CMD ["traders-readonly-api"]

FROM production-base AS production
