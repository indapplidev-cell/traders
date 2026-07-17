# ENGINE-ORCHESTRATOR-01 with systemd

Docker Compose is preferred for this deployment. A host deployment may use:

```ini
[Unit]
Description=traders-ml online closed-candle orchestrator
Wants=network-online.target
After=network-online.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/opt/traders-ml
EnvironmentFile=/opt/traders-ml/.env
ExecStart=/opt/traders-ml/.venv/bin/python scripts/engine_orchestrator_online_pipeline.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --continuous --poll-interval-seconds 10 --max-catchup-windows 4 --health-report reports/engine_orchestrator/latest_health.json
Restart=always
RestartSec=5
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
```

Run `alembic upgrade head` and once-mode smoke before enabling the unit. `SIGTERM` stops new window acceptance, lets the current synchronous module call finish, writes final health, and exits.
