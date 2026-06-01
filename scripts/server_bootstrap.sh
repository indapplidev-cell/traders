#!/usr/bin/env bash
set -euo pipefail

echo "== Installing system packages =="
apt update
apt install -y git curl wget ca-certificates gnupg lsb-release ufw python3 python3-venv python3-pip docker.io docker-compose-plugin

systemctl enable docker
systemctl start docker

ufw allow OpenSSH
ufw allow 22/tcp
ufw --force enable

echo "== Server bootstrap completed =="
