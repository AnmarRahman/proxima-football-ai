# Backend

Backend uses Postgres for data import and prediction output.

## Apply migrations

```bash
python backend/python/migrate_db.py --database-url "<postgres-url>"
```

## Import local JSON data into Postgres

```bash
python backend/python/import_players_to_db.py --database-url "<postgres-url>"
```

## Run predictor

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
```
