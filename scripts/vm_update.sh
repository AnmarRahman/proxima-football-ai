#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/anmarrahman/docker/proxima-football-ai}"
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "Created $APP_DIR/.env from .env.docker.example. Edit it before production use."
fi

# Force VM deployments to use Dockerized Postgres + PostgREST (no SQLite runtime).
if grep -q '^DATABASE_PROVIDER=' .env; then
  sed -i 's/^DATABASE_PROVIDER=.*/DATABASE_PROVIDER=postgres/' .env
else
  echo 'DATABASE_PROVIDER=postgres' >> .env
fi

if ! grep -q '^POSTGREST_URL=' .env; then
  echo 'POSTGREST_URL=http://postgrest:3000' >> .env
fi

sed -i '/^SQLITE_DATABASE_PATH=/d' .env

echo "Updating images and rebuilding app..."
docker compose pull postgres postgrest || true
docker compose build --pull app

echo "Starting Postgres + PostgREST..."
docker compose up -d postgres postgrest

echo "Applying Postgres migrations + importing player JSON data..."
docker compose run --rm postgres-seed

echo "Starting app container..."
docker compose up -d app --remove-orphans

echo "Current containers:"
docker compose ps
