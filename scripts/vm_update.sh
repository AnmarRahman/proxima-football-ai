#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/anmarrahman/docker/proxima-football-ai}"
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "Created $APP_DIR/.env from .env.docker.example. Edit it before production use."
fi

echo "Updating images and restarting containers..."
docker compose pull postgres || true
docker compose build --pull app
docker compose up -d --remove-orphans

echo "Current containers:"
docker compose ps
