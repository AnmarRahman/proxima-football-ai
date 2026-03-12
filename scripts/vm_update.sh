#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/anmarrahman/docker/proxima-football-ai}"
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "Created $APP_DIR/.env from .env.docker.example. Edit it before production use."
fi

DB_PROVIDER="sqlite"
if grep -q '^DATABASE_PROVIDER=' .env; then
  DB_PROVIDER="$(grep '^DATABASE_PROVIDER=' .env | tail -n1 | cut -d'=' -f2 | tr -d ' \r\n\t')"
fi

echo "Updating images and restarting containers..."
docker compose pull postgres || true
docker compose build --pull app

if [ "$DB_PROVIDER" = "sqlite" ]; then
  echo "Seeding SQLite database from backend/python/data/players ..."
  docker compose run --rm sqlite-seed
fi

docker compose up -d --remove-orphans

echo "Current containers:"
docker compose ps
