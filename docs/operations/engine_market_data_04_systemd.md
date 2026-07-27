# ENGINE-MARKET-DATA-04 with systemd

Example `/etc/systemd/system/traders-ml-market-data-sync.service`:

```ini
[Unit]
Description=traders-ml market data continuous sync
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/traders-ml
EnvironmentFile=/etc/traders-ml/market-data.env
ExecStart=/opt/traders-ml/.venv/bin/python scripts/engine_market_data_continuous_sync.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1m,5m,15m,1h,4h,1d --warmup --continuous --health-report reports/engine_market_data/continuous_sync/latest_health.json
Restart=always
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable traders-ml-market-data-sync
sudo systemctl start traders-ml-market-data-sync
sudo systemctl status traders-ml-market-data-sync
journalctl -u traders-ml-market-data-sync -f
```

Run `alembic upgrade head` during deployment. `Restart=always` restores the
process after failure or reboot; startup warmup then catches up exact closed
candle gaps. Codex, VSCode, notebooks, and an interactive developer session are
not part of the service architecture.
