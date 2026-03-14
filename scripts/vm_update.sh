#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/anmarrahman/docker/proxima-football-ai}"
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "Created $APP_DIR/.env from .env.docker.example. Edit it before production use."
fi

if grep -q '^DATABASE_PROVIDER=' .env; then
  sed -i 's/^DATABASE_PROVIDER=.*/DATABASE_PROVIDER=postgres/' .env
else
  echo 'DATABASE_PROVIDER=postgres' >> .env
fi

if ! grep -q '^POSTGREST_URL=' .env; then
  echo 'POSTGREST_URL=http://postgrest:3000' >> .env
fi

if ! grep -q '^ADMIN_COOKIE_SECURE=' .env; then
  echo 'ADMIN_COOKIE_SECURE=false' >> .env
fi

if ! grep -q '^POSTGRES_DATA_DIR=' .env; then
  echo 'POSTGRES_DATA_DIR=/home/anmarrahman/docker/proxima-football-ai/proxima_postgres_data' >> .env
fi

POSTGRES_DATA_DIR="$(grep '^POSTGRES_DATA_DIR=' .env | tail -n1 | cut -d'=' -f2- | tr -d '\r')"
if [ -z "$POSTGRES_DATA_DIR" ]; then
  POSTGRES_DATA_DIR="$APP_DIR/proxima_postgres_data"
fi

mkdir -p "$POSTGRES_DATA_DIR"

echo "Updating images and rebuilding app..."
docker compose pull postgres postgrest || true
docker compose build --pull app

echo "Starting Postgres + PostgREST..."
docker compose up -d postgres postgrest

echo "Applying Postgres migrations + importing player JSON data..."
docker compose run --rm postgres-seed

echo "Running predictor to populate player_predictions..."
docker compose run --rm predictor

echo "Starting app container..."
docker compose up -d app --remove-orphans

PRED_COUNT=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-proxima}" -d "${POSTGRES_DB:-proxima_ai}" -t -A -c "select count(*) from player_predictions;" | tr -d '\r')
if [ -z "$PRED_COUNT" ] || [ "$PRED_COUNT" = "0" ]; then
  echo "[ERROR] player_predictions is empty after predictor run."
  exit 1
fi

echo "player_predictions count: $PRED_COUNT"

echo "Current containers:"
docker compose ps
