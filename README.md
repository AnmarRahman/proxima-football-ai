# Proxima Football AI

Proxima Football AI provides evidence-backed forecasts for a player's next domestic-league season. The production application runs on Vercel, stores canonical data and current predictions in Supabase Postgres, and runs approved Python inference through GitHub Actions.

The production model is intentionally limited to:

- expected league appearances next season;
- expected league goals next season;
- uncertainty intervals when the validated interval policy supports them.

It does not claim to predict a complete career, retirement age, assists, ratings, injuries, or tactical attributes.

## Architecture

- `frontend/`: Next.js website, server API routes, prediction UI, and admin dashboard.
- `backend/python/model_artifacts/tier_a_v1/`: approved, immutable Tier A model artifact.
- `backend/python/data/collected_player_seasons.csv`: reviewed Tier A release dataset.
- `backend/db/migrations/003_tier_a_prediction_pipeline.sql`: isolated production ML tables.
- Supabase Postgres: canonical ML inputs, model registry, prediction runs, and current predictions.
- GitHub Actions: weekly or manually triggered inference and separate candidate-model training.
- Vercel: reads stored predictions; it never trains or executes the Python model.

## Data Isolation

The rich historical dataset and production Tier A dataset are deliberately separate:

- `players` and `player_seasons`: legacy detailed player records used by the admin data viewer.
- `ml_players` and `ml_player_seasons`: normalized domestic-league appearances/goals used by `tier-a-v1`.
- `next_season_predictions`: one current forecast per player.
- `tier_a_prediction_runs`: inference audit trail.
- `model_versions`: model manifest, digest, metrics, and approval state.

Inference only upserts `next_season_predictions`. It never creates or edits historical season rows. Running a player again replaces that player's previous current forecast.

## Model Lifecycle

`tier-a-v1` is trained once and committed as an approved release artifact. Normal prediction runs load that artifact and do not retrain it.

1. Edit or import reviewed rows in `ml_players` and `ml_player_seasons`.
2. Run the approved artifact to refresh predictions.
3. If the training dataset or feature code changes, run the candidate-training workflow.
4. Review its metrics and artifact before explicitly promoting a new model version.

The current one-step appearances and goals models passed the Phase 3 validation gates. Full recursive career trajectories did not, so they are not exposed as production predictions.

## First Supabase Setup

Use Python 3.11 and install dependencies:

```powershell
py -3.11 -m venv .venv311
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Set the Supabase Postgres connection string, apply migrations, and import the reviewed Tier A release:

```powershell
$env:DATABASE_URL="postgresql://...?...sslmode=require"
python backend/python/migrate_db.py
python backend/python/import_tier_a_to_db.py
python backend/python/run_tier_a_predictions.py --run-type manual --triggered-by local
```

The import replaces each included player's ML season rows and registers the exact committed `tier-a-v1` manifest as approved. It does not modify the legacy detailed season tables.

## GitHub Actions

Add `DATABASE_URL` under **Repository Settings > Secrets and variables > Actions**.

- **Tier A Next-Season Predictions** (`tier-a-predictions.yml`): runs every Monday at 04:00 UTC and can be dispatched manually for all players or one player.
- **Train Tier A Candidate Model** (`train-tier-a-model.yml`): manually exports deterministic Supabase training data and creates an unapproved downloadable candidate artifact.
- **Legacy Career Predictions** (`weekly-predictions.yml`): manual-only compatibility workflow; do not use it for production forecasts.

Set repository variable `IMPORT_TIER_A_FROM_REPO=true` only when the reviewed committed CSV should replace the current Supabase ML input tables on a prediction run. Leave it unset for normal database-first operation.

## Vercel Configuration

Set the Vercel project root to `frontend` and configure:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ADMIN_DASHBOARD_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `GITHUB_ACTIONS_TOKEN`
- `GITHUB_REPO_OWNER=AnmarRahman`
- `GITHUB_REPO_NAME=proxima-football-ai`
- `GITHUB_WORKFLOW_ID=tier-a-predictions.yml`
- `GITHUB_WORKFLOW_REF=main` after merge

Never expose `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, admin secrets, or the GitHub token through `NEXT_PUBLIC_*` variables.

## Development

Run all Python tests:

```powershell
python backend/python/run_tests.py
```

Run the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Useful API checks after predictions exist:

- `/api/players`
- `/api/predictions/erling-haaland`
- `/api/admin/prediction-status` while authenticated as an administrator

## Data Limitations

Tier A uses free, provenance-backed domestic-league appearances and goals. It lacks consistent minutes, shots, xG, assists, and injury data. The UI therefore presents a one-season statistical estimate with explicit uncertainty and does not describe it as a complete career forecast.
