import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model

try:
    import joblib
    print("joblib is installed")
except ModuleNotFoundError:
    print("joblib NOT found")

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()
origins = ["http://localhost:3000"]  # adjust if your frontend URL is different
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

# -----------------------------
# Paths to pre-trained model & scaler
# -----------------------------
BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "data/models/player_gru.h5"
SCALER_PATH = BASE_DIR / "data/models/scaler.pkl"

# Load model & scaler once at startup
model = load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

# -----------------------------
# Feature Names & Player Mapping
# -----------------------------
feature_names = [
    'appearances','goals','assists','minutes','rating','xG','xA',
    'key_passes','successful_dribbles','duels_won','shots_per_game','tackles_per_game',
    'fouls_drawn','days_lost','sprint_speed_kmh','acceleration','stamina','recovery_rate',
    'contribution_to_build_up','defensive_transitions'
]

PLAYER_JSON_MAP = {
    "mbappe": "kylian-mbappe.json",
    "haaland": "erling-haaland.json",
    "messi": "lionel-messi.json",
    "ronaldo": "cristiano-ronaldo.json",
    "neymar": "neymar-jr.json"
}

# -----------------------------
# Flatten Season Function
# -----------------------------
def flatten_season(season):
    flat = {k: 0.0 for k in feature_names}

    for team in season.get("teams", []):
        for comp in team.get("competitions", []):
            # Numeric stats
            for key in feature_names[:13]:
                try:
                    flat[key] += float(comp.get(key, 0))
                except:
                    flat[key] += 0.0

            # Injuries
            flat['days_lost'] += sum(
                float(i.get('days_lost', 0)) if str(i.get('days_lost', '0')).replace('.', '', 1).isdigit() else 0
                for i in comp.get('injuries', [])
            )

            # Physical metrics
            physical = comp.get('physical_metrics', {})
            mapping_physical = {"Poor":1,"Low":2,"Medium":3,"High":4,"Very High":4.5,"Elite":5,"Excellent":5}
            for metric, key_name in zip(feature_names[14:18], ["sprint_speed_kmh","acceleration","stamina","recovery_rate"]):
                v = physical.get(key_name, 0)
                if isinstance(v, str):
                    v = mapping_physical.get(v, 0)
                flat[metric] += float(v)

            # Tactical metrics
            tactical = comp.get('tactical_data', {})
            mapping_tactical = {"Low":1,"Medium":2,"High":3,"Very High":4,"World Class":5}
            for metric in feature_names[18:]:
                v = tactical.get(metric, 0)
                if isinstance(v, str):
                    v = mapping_tactical.get(v, 0)
                flat[metric] += float(v)

    # Average physical/tactical metrics by number of competitions
    num_comps = sum(len(team.get("competitions", [])) for team in season.get("teams", []))
    if num_comps > 0:
        for metric in feature_names[14:]:
            flat[metric] /= num_comps
        for metric in feature_names[18:]:
            flat[metric] /= num_comps

    return flat

# -----------------------------
# Predict Endpoint
# -----------------------------
@app.get("/predict")
def predict_player(player_id: str = Query(..., description="Player ID (e.g. mbappe, messi)")):
    player_file = PLAYER_JSON_MAP.get(player_id.lower())
    if not player_file:
        return {"error": f"No JSON file found for player_id '{player_id}'"}

    filepath = BASE_DIR / "data/players" / player_file
    if not filepath.exists():
        return {"error": f"File '{player_file}' does not exist on the server"}

    # Load player JSON
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    seasons = data.get("seasons", [])
    flat_seasons = [flatten_season(s) for s in seasons]
    df = pd.DataFrame(flat_seasons)

    # Predict using pre-trained model
    X_scaled = scaler.transform(df.values)
    X_gru = X_scaled.reshape((1, X_scaled.shape[0], X_scaled.shape[1]))
    predicted = model.predict(X_gru)
    predicted_next_season = scaler.inverse_transform(predicted)
    readable_prediction = dict(zip(feature_names, predicted_next_season[0].tolist()))

    return {
        "player": data.get("player", {}),
        "teams": data.get("teams", []),
        "predicted_next_season": readable_prediction
    }
