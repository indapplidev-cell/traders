# Server Deploy Report

## Scope

- Stage 3 was not started.
- `/opt/cosmic_api`, `/opt/cosmic_db`, and `/opt/gamecom` were not touched.
- `scripts/server_bootstrap.sh` was updated locally for idempotent behavior and was not executed on the VPS in this session.

## Local Repository Facts

- commit hash: `73bef45195dc5c8bb25ebdd5acb02391924ccf0e`
- current local changes:
  - `scripts/server_bootstrap.sh` modified
  - `reports/server_deploy_report.md` rewritten
- local cleanup result:
  - `__pycache__` directories remaining: `0`
  - `*.pyc` files remaining: `0`

## Bootstrap Script Facts

`scripts/server_bootstrap.sh` now:

- is idempotent for repeated runs
- installs:
  - `git`
  - `curl`
  - `wget`
  - `ca-certificates`
  - `gnupg`
  - `lsb-release`
  - `ufw`
  - `python3`
  - `python3-venv`
  - `python3-pip`
  - `openssl`
- installs Docker only when `docker` command is missing
- enables and starts Docker only when Docker is already present
- installs `docker compose` plugin only when `docker compose` is unavailable
- uses Docker CE repository and does not install `docker.io` over an existing Docker CE installation

Local validation:

- `bash -n scripts/server_bootstrap.sh`: success

## VPS Connectivity Facts

Attempted target:

- host: `185.216.87.26`
- user: `root`

Connectivity checks:

- `Test-NetConnection 185.216.87.26 -Port 22`
  - `TcpTestSucceeded: True`
  - `PingSucceeded: False`
- raw TCP socket connect to `185.216.87.26:22`
  - TCP connection established
  - no SSH banner received within 10 seconds
- `ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=20 root@185.216.87.26 "hostname"`
  - failed
  - result: `Connection timed out during banner exchange`
- `ssh -i ~/.ssh/cosmic_vps_ed25519 -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=20 root@185.216.87.26 "hostname"`
  - failed
  - result: `Connection timed out during banner exchange`

Result:

- no interactive or non-interactive SSH session was established
- no command from the requested VPS deploy checklist was executed on the VPS
- no remote filesystem changes were made

## Requested Server Facts

- `/opt` state: not checked on VPS
- Docker version: not checked on VPS
- `docker compose` version: not checked on VPS
- PostgreSQL container status: not checked on VPS
- `pg_isready` result: not checked on VPS
- `ss -lntp | grep 5432` result: not checked on VPS
- PostgreSQL listening only on `127.0.0.1:5432`: not verified on VPS
- `alembic upgrade head` result: not checked on VPS
- `alembic current` result: not checked on VPS
- `pytest` result on VPS: not checked on VPS
- `ruff` result on VPS: not checked on VPS
- `health` result on VPS: not checked on VPS
- `async-health` result on VPS: not checked on VPS
- `load-history` result on VPS: not checked on VPS
- `backtest` result on VPS: not checked on VPS

## Repository Runtime Facts Only

These are repository configuration facts, not VPS runtime confirmation:

- [`docker-compose.server.yml`](../docker-compose.server.yml) binds PostgreSQL as `127.0.0.1:5432:5432`

## What Could Not Be Verified

- `hostname` on VPS
- `ls -la /opt` on VPS
- `docker --version` on VPS
- `docker compose version` on VPS
- `systemctl is-active docker` on VPS
- `ufw status` on VPS
- clone or reset state of `/opt/traders`
- server `.env` creation
- `docker compose -f docker-compose.server.yml --env-file .env up -d`
- `docker ps`
- `docker logs traders_postgres --tail=50`
- `docker exec traders_postgres pg_isready -U traders -d traders`
- `ss -lntp | grep 5432`
- `python3 -m venv .venv`
- `pip install -e ".[dev]"`
- `alembic upgrade head`
- `alembic current`
- all requested CLI runtime checks

## Untouched Paths Confirmation

Because no SSH session was established, the following VPS paths were not touched:

- `/opt/cosmic_api`
- `/opt/cosmic_db`
- `/opt/gamecom`
