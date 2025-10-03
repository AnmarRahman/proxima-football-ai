import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model

app = FastAPI()
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "data/models/player_gru.h5"
SCALER_PATH = BASE_DIR / "data/models/scaler.pkl"

# Load model & scaler once
model = load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

feature_names = [ 'appearances','goals','assists','minutes','rating','xG','xA',
    'key_passes','successful_dribbles','duels_won','shots_per_game','tackles_per_game',
    'fouls_drawn','days_lost','sprint_speed_kmh','acceleration','stamina','recovery_rate',
    'contribution_to_build_up','defensive_transitions' ]

PLAYER_JSON_MAP = {
    "mbappe": "kylian-mbappe.json",
    "haaland": "erling-haaland.json",
    "messi": "lionel-messi.json",
    "ronaldo": "cristiano-ronaldo.json",
    "neymar": "neymar-jr.json"
}

def flatten_season(season):
    # Copy your flatten_season logic here (same as above)
    ...

@app.get("/predict")
def predict_player(player_id: str = Query(..., description="Player ID")):
    player_file = PLAYER_JSON_MAP.get(player_id.lower())
    if not player_file: return {"error": f"No JSON file for {player_id}"}

    filepath = BASE_DIR / "data/players" / player_file
    if not filepath.exists(): return {"error": f"File {player_file} not found"}

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    seasons = data.get("seasons",[])
    flat_seasons = [flatten_season(s) for s in seasons]
    df = pd.DataFrame(flat_seasons)

    # Predict using pre-trained model
    X_scaled = scaler.transform(df.values)
    X_gru = X_scaled.reshape((1,X_scaled.shape[0],X_scaled.shape[1]))
    predicted = model.predict(X_gru)
    predicted_next_season = scaler.inverse_transform(predicted)
    readable_prediction = dict(zip(feature_names, predicted_next_season[0].tolist()))

    return {
        "player": data.get("player",{}),
        "teams": data.get("teams",[]),
        "predicted_next_season": readable_prediction
    }
