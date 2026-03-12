# Backend

Backend now supports two DB paths:

1. Postgres (`*_to_db.py`, `main.py`, `migrate_db.py`)
2. SQLite (`*_to_sqlite.py`, `main_sqlite.py`, `migrate_sqlite.py`)

## SQLite quick start

1. Create schema:

```bash
python backend/python/migrate_sqlite.py --sqlite-path backend/python/data/proxima.sqlite3
```

2. Import players JSON into SQLite:

```bash
python backend/python/import_players_to_sqlite.py --sqlite-path backend/python/data/proxima.sqlite3
```

3. Generate predictions from SQLite and write back to SQLite:

```bash
python backend/python/main_sqlite.py \
  --data-source sqlite \
  --output-target sqlite \
  --all-active \
  --sqlite-path backend/python/data/proxima.sqlite3
```

Optional: also write JSON prediction files for frontend fallback:

```bash
python backend/python/main_sqlite.py \
  --data-source sqlite \
  --output-target both \
  --copy-to-frontend \
  --all-active \
  --sqlite-path backend/python/data/proxima.sqlite3
```

## Postgres mode

### Apply migrations

```bash
python backend/python/migrate_db.py --database-url "<postgres-url>"
```

### Import local JSON data into Postgres

```bash
python backend/python/import_players_to_db.py --database-url "<postgres-url>"
```

### Run predictor

```bash
python backend/python/main.py \
  --data-source db \
  --output-target db \
  --all-active \
  --run-type manual \
  --triggered-by local
```

## Retired Player Overrides

To control active/retired tagging during imports, edit:

- `backend/python/data/players/player_status_overrides.json`

Then rerun import.

Age-threshold override for `over_35`:

```bash
python backend/python/import_players_to_db.py --over-age-threshold 35
python backend/python/import_players_to_sqlite.py --over-age-threshold 35
```
