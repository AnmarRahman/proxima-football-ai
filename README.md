# Proxima Football AI

Proxima Football AI predicts the future season-by-season career trajectory of football players. The production deployment uses a Next.js frontend on Vercel, Supabase Postgres for player data and predictions, and GitHub Actions for scheduled or manually triggered model runs.

## Production Architecture

- `frontend/`: Next.js website, API routes, prediction dashboard, and admin dashboard.
- `backend/python/`: player import, database migrations, model training, inference, and evaluation.
- Supabase Postgres: historical player seasons, prediction runs, and generated predictions.
- GitHub Actions: imports seed data when required, restores or trains the model, and writes predictions to Supabase.
- Vercel: serves the website and reads the latest predictions through server-side API routes.

The frontend never trains the model inside a Vercel request. Training is a background GitHub Actions job because it can take longer than a serverless request and requires access to the complete training dataset.

## Model Lifecycle

The predictor uses a position-aware multi-output random forest. It forecasts the next season from a rolling four-season window and recursively generates later seasons.

1. GitHub Actions calculates a fingerprint from normalized Supabase training data.
2. A model artifact is restored from the GitHub Actions cache when the data and model code are unchanged.
3. If no matching artifact exists, the model is trained with entire players held out for validation.
4. The artifact is cached under `backend/python/artifacts/career_model.joblib`.
5. Predictions are written to `player_predictions`; historical `player_seasons` rows are never modified by inference.

The model retrains automatically after player data, feature definitions, dependencies, or predictor code changes. Use `--force-retrain` to bypass a local artifact manually.

## Player Data

Source JSON files live in `backend/python/data/players/`. The planned balanced collection roster is documented in `backend/python/data/PLAYER_SCRAPE_ROSTER.md`.

Import local JSON files into the configured database:

```powershell
python backend/python/migrate_db.py
python backend/python/import_players_to_db.py
```

The importer upserts players and seasons, so unchanged rows are updated rather than duplicated.

## Local Setup

Use Python 3.11:

```powershell
py -3.11 -m venv .venv311
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Set the Supabase Postgres connection string:

```powershell
$env:DATABASE_URL="postgresql://..."
```

Run all eligible predictions:

```powershell
python backend/python/main.py --data-source db --output-target db --all-active --window-size 4 --retirement-age 40 --run-type manual --triggered-by local --model-version random-forest-v4-position-aware-blend
```

Force model retraining:

```powershell
python backend/python/main.py --data-source db --output-target db --all-active --force-retrain
```

Run tests and model comparison:

```powershell
python -m unittest discover -s backend/python/tests -v
python backend/python/evaluate_models.py
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Vercel Configuration

Set the Vercel project root to `frontend` and configure:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ADMIN_DASHBOARD_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `GITHUB_ACTIONS_TOKEN`
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `GITHUB_WORKFLOW_ID=weekly-predictions.yml`
- `GITHUB_WORKFLOW_REF=codex/prediction-pipeline-refactor` while deploying this branch, or `main` after merge

Do not expose `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, admin secrets, or the GitHub token through `NEXT_PUBLIC_*` variables.

## GitHub Actions

Add `DATABASE_URL` under repository **Settings > Secrets and variables > Actions**. Run **Weekly Predictions** manually after the first database import. The workflow also runs every Monday at 04:00 UTC.

The admin dashboard can dispatch the same workflow when its GitHub variables and token are configured in Vercel.

## Data Limitations

The current dataset is small and attacker-heavy. Treat displayed confidence as model validation information, not a guarantee. A reliable general career model requires substantially more players, goalkeeper-specific modeling, consistent season definitions, and source-backed statistics.
