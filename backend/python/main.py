import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import GRU, Dense
from tensorflow.keras.models import Sequential

# -----------------------------
# Feature names
# -----------------------------
feature_names = [
    'appearances','goals','assists','minutes','rating','xG','xA',
    'key_passes','successful_dribbles','duels_won','shots_per_game',
    'tackles_per_game','fouls_drawn','days_lost',
    'sprint_speed_kmh','acceleration','stamina','recovery_rate',
    'contribution_to_build_up','defensive_transitions'
]

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYERS_DIR = os.path.join(BASE_DIR, "data", "players")
PREDICTIONS_DIR = os.path.join(PLAYERS_DIR, "predictions")
os.makedirs(PREDICTIONS_DIR, exist_ok=True)

# -----------------------------
# Helper: safely convert to float
# -----------------------------
def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0

# -----------------------------
# Flatten one season into numeric features
# -----------------------------
def flatten_season(season):
    flat = {k: 0.0 for k in feature_names}

    # Handle teams and competitions if present
    for team in season.get("teams", []):
        for comp in team.get("competitions", []):
            # Numeric stats
            for key in feature_names[:13]:
                val = comp.get(key, 0)
                flat[key] += safe_float(val)

            # Injuries
            for injury in comp.get("injuries", []):
                flat["days_lost"] += safe_float(injury.get("days_lost", 0))

            # Physical metrics
            physical = comp.get("physical_metrics", {})
            mapping_physical = {"Poor":1,"Low":2,"Medium":3,"High":4,"Very High":4.5,"Elite":5,"Excellent":5}
            flat["sprint_speed_kmh"] += safe_float(physical.get("sprint_speed_kmh", 0))
            flat["acceleration"] += mapping_physical.get(physical.get("acceleration",""),0)
            flat["stamina"] += mapping_physical.get(physical.get("stamina",""),0)
            flat["recovery_rate"] += mapping_physical.get(physical.get("recovery_rate",""),0)

            # Tactical metrics
            tactical = comp.get("tactical_data", {})
            mapping_tactical = {"Low":1,"Medium":2,"High":3,"Very High":4,"World Class":5}
            flat["contribution_to_build_up"] += mapping_tactical.get(tactical.get("contribution_to_build_up",""),0)
            flat["defensive_transitions"] += mapping_tactical.get(tactical.get("defensive_transitions",""),0)

    # Average physical & tactical metrics by number of competitions
    num_comps = sum(len(team.get("competitions", [])) for team in season.get("teams", []))
    if num_comps > 0:
        for key in feature_names[14:]:
            flat[key] /= num_comps

    return flat

# -----------------------------
# Load a single player by id
# -----------------------------
def load_player(player_id):
    player_id = player_id.lower()
    for fname in os.listdir(PLAYERS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(PLAYERS_DIR, fname)
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            if data["player"]["id"].lower() == player_id:
                return data
    raise ValueError(f"{player_id} not found.")

# -----------------------------
# Predict future seasons until age 35
# -----------------------------
def predict_player(player_id):
    try:
        data = load_player(player_id)
        seasons = data.get("seasons", [])
        birth_date = data["player"]["birth_date"]
        birth_year = int(birth_date.split("-")[0])

        # Flatten all seasons
        all_flat = [flatten_season(s) for s in seasons]
        df_all = pd.DataFrame(all_flat)

        # Scale features
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(df_all.values)

        # Prepare GRU input
        X_input = X_scaled.reshape((1, X_scaled.shape[0], X_scaled.shape[1]))
        y_input = X_scaled[-1].reshape((1, X_scaled.shape[1]))

        # Build GRU model
        model = Sequential()
        model.add(GRU(64, activation='relu', input_shape=(X_input.shape[1], X_input.shape[2])))
        model.add(Dense(X_input.shape[2]))
        model.compile(optimizer='adam', loss='mse')

        # Train model
        model.fit(X_input, y_input, epochs=500, verbose=0)

        # Calculate remaining seasons until age 35
        last_season_year = max([s['season'] for s in seasons])
        last_age = last_season_year - birth_year
        remaining_seasons = max(0, 35 - last_age)

        # Predict future seasons
        predicted_seasons = []
        current_input = X_input.copy()
        for _ in range(remaining_seasons):
            pred = model.predict(current_input, verbose=0)
            predicted_seasons.append(pred[0])
            current_input = np.concatenate([current_input[:,1:,:], pred.reshape(1,1,-1)], axis=1)

        # Inverse scale
        predicted_seasons = scaler.inverse_transform(predicted_seasons)

        # Make readable
        readable = []
        for i, season_vals in enumerate(predicted_seasons):
            season_dict = dict(zip(feature_names, season_vals))
            season_dict["season"] = last_season_year + 1 + i
            readable.append(season_dict)

        # Save JSON
        pred_file = os.path.join(PREDICTIONS_DIR, f"{player_id}_predictions.json")
        with open(pred_file, "w", encoding="utf-8") as f:
            json.dump(readable, f, indent=4)

        print(f"Predictions saved to: {pred_file}")
        return readable

    except Exception as e:
        print("Error:", e)
        return None

# -----------------------------
# Run example
# -----------------------------
if __name__ == "__main__":
    predict_player("mbappe")
