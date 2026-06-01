#!/usr/bin/env bash
set -euo pipefail

cd /opt/traders

source .venv/bin/activate

python -m pytest
python -m ruff check .
python -m app.cli.commands health
python -m app.cli.commands async-health
python -m app.cli.commands fetch-candles --symbol BTCUSDT --interval 15m --limit 300
python -m app.cli.commands analyze --symbol BTCUSDT --interval 15m
python -m app.cli.commands paper-step --symbol BTCUSDT --interval 15m
python -m app.cli.commands portfolio
python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --limit 1000
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands paper-runner --help

echo "== Server check completed =="
