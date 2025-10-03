import json
import os

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import GRU, Dense
from tensorflow.keras.models import Sequential

app = FastAPI()

# Allow Next.js dev server to call this API
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature names (must match the order in flatten_season)
feature_names = [
    'appearances','goals','assists','minutes','rating','xG','xA',
    'key_passes','successful_dribbles','duels_won','shots_per_game',
    'tackles_per_game','fouls_drawn','days_lost',
    'sprint_speed_kmh','acceleration','stamina','recovery_rate',
    'contribution_to_build_up','defensive_transitions'
]

# Map player_id to json filename
PLAYER_JSON_MAP = {
    "mbappe": "kylian-mbappe.json",
    "haaland": "erling-haaland.json",
    "messi": "lionel-messi.json",
    "ronaldo": "cristiano-ronaldo.json",
    "neymar": "neymar-jr.json"
}

# -----------------------------
# Flatten one season into numeric features
# -----------------------------
def flatten_season(season):
    flat = {k: 0.0 for k in feature_names}

    # Iterate all teams and competitions
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
# FastAPI Endpoint
# -----------------------------
@app.get("/predict")
def predict_player(player_id: str = Query(..., description="Player ID (e.g. mbappe, messi)")):
    try:
        player_file = PLAYER_JSON_MAP.get(player_id.lower())
        if not player_file:
            return {"error": f"No JSON file found for player_id '{player_id}'"}

        filepath = os.path.join("data", "players", player_file)
        if not os.path.exists(filepath):
            return {"error": f"File '{player_file}' does not exist on the server"}

        # Load JSON
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        seasons = data.get('seasons', [])

        # Flatten seasons for GRU input
        flat_seasons = [flatten_season(s) for s in seasons]
        df = pd.DataFrame(flat_seasons)

        # Normalize
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(df.values)

        # Prepare GRU input
        X_gru = X_scaled.reshape((1, X_scaled.shape[0], X_scaled.shape[1]))
        y_gru = X_scaled[-1].reshape((1, X_scaled.shape[1]))

        # Build GRU
        model = Sequential()
        model.add(GRU(64, activation='relu', input_shape=(X_gru.shape[1], X_gru.shape[2])))
        model.add(Dense(X_gru.shape[2]))
        model.compile(optimizer='adam', loss='mse')

        # Train
        model.fit(X_gru, y_gru, epochs=500, verbose=0)

        # Predict next season
        predicted = model.predict(X_gru)
        predicted_next_season = scaler.inverse_transform(predicted)
        predicted_next_season_list = predicted_next_season.tolist()[0]

        # Map numbers to feature names
        readable_prediction = dict(zip(feature_names, predicted_next_season_list))

        return {
            "player": data.get("player", {}),
            "teams": data.get("teams", []),
            "predicted_next_season": readable_prediction
        }

    except Exception as e:
        return {"error": str(e)}
