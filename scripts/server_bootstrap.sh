#!/usr/bin/env bash
set -euo pipefail

BASE_PACKAGES=(
  git
  curl
  wget
  ca-certificates
  gnupg
  lsb-release
  ufw
  python3
  python3-venv
  python3-pip
  openssl
)

has_command() {
  command -v "$1" >/dev/null 2>&1
}

has_docker_compose() {
  docker compose version >/dev/null 2>&1
}

install_base_packages() {
  echo "== Installing base system packages =="
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y "${BASE_PACKAGES[@]}"
}

configure_docker_repo() {
  local arch codename repo_file

  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
  repo_file="/etc/apt/sources.list.d/docker.list"

  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
  fi

  if [[ ! -f "${repo_file}" ]]; then
    echo \
      "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
      > "${repo_file}"
  fi
}

install_docker_if_missing() {
  if has_command docker; then
    echo "== Docker already installed; enabling service =="
    systemctl enable docker
    systemctl start docker
    return
  fi

  echo "== Installing Docker CE =="
  configure_docker_repo
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
  systemctl enable docker
  systemctl start docker
}

install_compose_if_missing() {
  if has_docker_compose; then
    echo "== docker compose already available =="
    return
  fi

  echo "== Installing docker compose plugin =="
  apt-get update
  apt-get install -y docker-compose-plugin
}

configure_firewall() {
  echo "== Configuring UFW =="
  ufw allow OpenSSH
  ufw allow 22/tcp
  ufw --force enable
}

install_base_packages
install_docker_if_missing
install_compose_if_missing
configure_firewall

echo "== Server bootstrap completed successfully =="
