import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import GRU, Dense
from tensorflow.keras.models import Sequential

# Feature names
feature_names = [
    'appearances','goals','assists','minutes','rating','xG','xA',
    'key_passes','successful_dribbles','duels_won','shots_per_game',
    'tackles_per_game','fouls_drawn','days_lost',
    'sprint_speed_kmh','acceleration','stamina','recovery_rate',
    'contribution_to_build_up','defensive_transitions'
]

# Flatten season function (copy from main.py)
def flatten_season(season):
    flat = {k: 0.0 for k in feature_names}
    for team in season.get("teams", []):
        for comp in team.get("competitions", []):
            for key in feature_names[:13]:
                flat[key] += float(comp.get(key, 0) or 0)
            flat['days_lost'] += sum(
                float(i.get('days_lost', 0)) if str(i.get('days_lost','0')).replace('.','',1).isdigit() else 0
                for i in comp.get('injuries', [])
            )
            physical = comp.get('physical_metrics', {})
            mapping_physical = {"Poor":1,"Low":2,"Medium":3,"High":4,"Very High":4.5,"Elite":5,"Excellent":5}
            for metric, key_name in zip(feature_names[14:18], ["sprint_speed_kmh","acceleration","stamina","recovery_rate"]):
                v = physical.get(key_name, 0)
                if isinstance(v,str): v = mapping_physical.get(v,0)
                flat[metric] += float(v)
            tactical = comp.get('tactical_data', {})
            mapping_tactical = {"Low":1,"Medium":2,"High":3,"Very High":4,"World Class":5}
            for metric in feature_names[18:]:
                v = tactical.get(metric,0)
                if isinstance(v,str): v = mapping_tactical.get(v,0)
                flat[metric] += float(v)
    num_comps = sum(len(team.get("competitions", [])) for team in season.get("teams", []))
    if num_comps > 0:
        for metric in feature_names[14:]: flat[metric] /= num_comps
        for metric in feature_names[18:]: flat[metric] /= num_comps
    return flat

# Load all JSON data
data_dir = "data/players"
all_features = []
for f in os.listdir(data_dir):
    if f.endswith(".json"):
        with open(os.path.join(data_dir,f),encoding="utf-8") as file:
            data = json.load(file)
        seasons = data.get("seasons",[])
        flat_seasons = [flatten_season(s) for s in seasons]
        all_features.extend(flat_seasons)

df = pd.DataFrame(all_features)

# Normalize
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(df.values)

# Prepare GRU input
X_gru = X_scaled.reshape((1, X_scaled.shape[0], X_scaled.shape[1]))
y_gru = X_scaled[-1].reshape((1, X_scaled.shape[1]))

# Build & train GRU
model = Sequential()
model.add(GRU(64, activation='relu', input_shape=(X_gru.shape[1], X_gru.shape[2])))
model.add(Dense(X_gru.shape[2]))
model.compile(optimizer='adam', loss='mse')
model.fit(X_gru, y_gru, epochs=500, verbose=0)

# Save model & scaler
os.makedirs("data/models", exist_ok=True)
model.save("data/models/player_gru.h5")
joblib.dump(scaler,"data/models/scaler.pkl")
print("Model and scaler saved!")
