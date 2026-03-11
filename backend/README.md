# Backend

This backend now supports two modes for prediction data flow:

1. `files` mode (legacy): read player JSON files and write prediction JSON files.
2. `db` mode (new): read player data from Postgres and write predictions to Postgres.

## Database schema

SQL migrations live in:

- `backend/db/migrations`

Apply migrations:

```bash
python backend/python/migrate_db.py --database-url "<postgres-url>"
```

or set `DATABASE_URL` and run:

```bash
python backend/python/migrate_db.py
```

## Import local JSON data into Postgres

```bash
python backend/python/import_players_to_db.py --database-url "<postgres-url>"
```

## Run predictor

### Legacy files mode

```bash
python backend/python/main.py --all-active --output-target files
```

### DB mode (recommended)

```bash
python backend/python/main.py \
  --data-source db \
  --output-target db \
  --all-active \
  --run-type manual \
  --triggered-by local
```

This writes:

- run metadata to `prediction_runs`
- per-player results to `player_predictions`
- latest results are queryable from `latest_player_predictions` view

## Weekly automation

GitHub Actions workflow:

- `.github/workflows/weekly-predictions.yml`

It runs:

1. migration
2. JSON import
3. prediction generation in DB mode

Required GitHub secret:

- `DATABASE_URL`
