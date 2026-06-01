#!/usr/bin/env bash
set -euo pipefail

cd /opt/traders

git pull --ff-only

source .venv/bin/activate

pip install -e ".[dev]"

docker compose -f docker-compose.server.yml --env-file .env up -d

alembic upgrade head

python -m app.cli.commands health
python -m app.cli.commands async-health

echo "== Server update completed =="
