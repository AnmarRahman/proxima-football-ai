# Tier-A Model Feasibility (Phase 2A)

Experimental package that answers one question: **can the freely obtainable
Tier-A fields (domestic-league appearances + goals + identity) predict future
outfield-player seasons meaningfully better than naive baselines?**

It does **not** replace the production predictor and does **not** touch
`data/players/`, Supabase, the frontend, or deployment.

## Pipeline

```
build_dataset.py   Collect Tier A via the approved Wikimedia adapter
                   (backend/python/data/acquisition/sources/wikipedia_source.py),
                   exclude youth/reserve seasons, aggregate per season-year as
                   domestic_league, keep provenance + coverage. Writes to
                   backend/python/data/acquisition/model_feasibility_data/.
features.py        Leakage-safe features (age, position, career-to-date, lag 1-5,
                   rolling rates/trends, deltas, experience) and 5 targets.
                   Missing is kept distinct from zero via *_missing indicators.
baselines.py       Mandatory baselines: naive persistence, age+position average,
                   continuation base-rate.
train.py           Lightweight tabular models (Ridge, ElasticNet, Poisson, RF,
                   HistGradientBoosting, Logistic). No GRU/TensorFlow. Seed 42.
evaluate.py        Chronological + leave-one-player-out evaluation, by position
                   and age, MAE / ROC-AUC / calibration / quantile intervals,
                   non-negativity audit. Writes results.json.
```

## Run

```
# from backend/python/model_feasibility/
python build_dataset.py      # one-time, cached & rate-limited via the pipeline
python evaluate.py           # trains + evaluates, writes results.json
python -m unittest discover -s tests
```

## Targets (separate, not one vector)

1. `y_next_apps`  next-season domestic-league appearances (count)
2. `y_next_goals` next-season domestic-league goals (count)
3. `y_next_gpa`   next-season goals per appearance
4. `y_continue`   P(player records another senior season) — probabilistic
5. `y_remaining`  remaining-career season count (experimental; retired only)

All count predictions are clipped to be non-negative. See
`TIER_A_MODEL_REPORT.md` for the full write-up and the GO/NO-GO decision.

## Data scope

Wikipedia figures are **domestic-league only** (`stat_scope: "domestic_league"`);
they are never mixed with cup/continental/all-competition totals. No assists,
minutes, xG, ratings, or physical/tactical fields are used or invented; missing
values stay null.
