import argparse
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import GRU, Dense, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

FEATURE_NAMES = [
    "appearances",
    "goals",
    "assists",
    "minutes",
    "rating",
    "xG",
    "xA",
    "key_passes",
    "successful_dribbles",
    "duels_won",
    "shots_per_game",
    "tackles_per_game",
    "fouls_drawn",
    "days_lost",
    "sprint_speed_kmh",
    "acceleration",
    "stamina",
    "recovery_rate",
    "contribution_to_build_up",
    "defensive_transitions",
    "age",
]

SEASON_BASE_KEYS = [
    "appearances",
    "goals",
    "assists",
    "minutes",
    "rating",
    "xG",
    "xA",
    "key_passes",
    "successful_dribbles",
    "duels_won",
    "shots_per_game",
    "tackles_per_game",
    "fouls_drawn",
]

NUMERIC_CLAMPS = {
    "rating": (4.0, 10.0),
    "days_lost": (0.0, None),
    "sprint_speed_kmh": (20.0, 45.0),
    "acceleration": (0.0, 5.0),
    "stamina": (0.0, 5.0),
    "recovery_rate": (0.0, 5.0),
    "contribution_to_build_up": (0.0, 5.0),
    "defensive_transitions": (0.0, 5.0),
}

PHYSICAL_MAPPING = {
    "poor": 1.0,
    "low": 2.0,
    "medium": 3.0,
    "moderate": 3.0,
    "high": 4.0,
    "very high": 4.5,
    "very fast": 4.5,
    "good": 3.5,
    "improving": 3.5,
    "developing": 2.5,
    "normal": 3.0,
    "fast": 4.0,
    "excellent": 5.0,
    "elite": 5.0,
}

TACTICAL_MAPPING = {
    "low": 1.0,
    "limited": 1.25,
    "below average": 1.5,
    "medium": 2.0,
    "moderate": 2.0,
    "high": 3.0,
    "very high": 4.0,
    "world class": 5.0,
}

BASE_DIR = Path(__file__).resolve().parent
PLAYERS_DIR = BASE_DIR / "data" / "players"
PREDICTIONS_DIR = PLAYERS_DIR / "predictions"
FRONTEND_PREDICTIONS_DIR = BASE_DIR.parent.parent / "frontend" / "public" / "data" / "predictions"
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
PREDICTION_RUN_LOCK_KEY = 91827463


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def normalize_label(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def parse_retired_flag(player: Dict[str, object]) -> bool:
    true_tokens = {"1", "true", "yes", "y", "retired"}

    if "is_retired" in player:
        raw = player.get("is_retired")
    elif "retired" in player:
        raw = player.get("retired")
    else:
        raw = False

    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    return normalize_label(raw) in true_tokens


def map_label(label: object, mapping: Dict[str, float]) -> float:
    key = normalize_label(label)
    return mapping.get(key, 0.0)


def clamp_value(name: str, value: float) -> float:
    bounds = NUMERIC_CLAMPS.get(name)
    if not bounds:
        return value
    low, high = bounds
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(high, value)
    return value


def ensure_py_types(d: Dict[str, object]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for key, value in d.items():
        if isinstance(value, np.integer):
            value = int(value)
        elif isinstance(value, np.floating):
            value = float(value)
        out[key] = value
    return out


def extract_competitions(season: Dict[str, object]) -> List[Dict[str, object]]:
    competitions: List[Dict[str, object]] = []

    # Nested schema: season -> teams[] -> competitions[]
    for team in season.get("teams", []) or []:
        for comp in team.get("competitions", []) or []:
            if isinstance(comp, dict):
                competitions.append(comp)

    # Flat schema: season itself has all base stat keys
    if not competitions and any(key in season for key in SEASON_BASE_KEYS):
        comp = {key: season.get(key) for key in SEASON_BASE_KEYS}
        comp["injuries"] = season.get("injuries", []) or []
        comp["physical_metrics"] = season.get("physical_metrics", {}) or {}
        comp["tactical_data"] = season.get("tactical_data", {}) or {}
        competitions.append(comp)

        # If national team split is available, include it as an additional competition.
        for national_comp in season.get("national_team_stats", []) or []:
            if isinstance(national_comp, dict):
                merged = {key: national_comp.get(key, 0.0) for key in SEASON_BASE_KEYS}
                merged["injuries"] = national_comp.get("injuries", []) or []
                merged["physical_metrics"] = national_comp.get("physical_metrics", season.get("physical_metrics", {})) or {}
                merged["tactical_data"] = national_comp.get("tactical_data", season.get("tactical_data", {})) or {}
                competitions.append(merged)

    return competitions


def flatten_season(season: Dict[str, object], birth_year: int) -> Optional[Dict[str, float]]:
    season_year = season.get("season")
    if season_year is None:
        return None

    flat = {name: 0.0 for name in FEATURE_NAMES}
    ratings: List[float] = []
    competitions = extract_competitions(season)

    for comp in competitions:
        for key in FEATURE_NAMES[:13]:
            value = comp.get(key)
            if key == "rating":
                rating = safe_float(value, default=np.nan)
                if 4 <= rating <= 10:
                    ratings.append(rating)
            else:
                flat[key] += safe_float(value, default=0.0)

        for injury in comp.get("injuries", []) or []:
            flat["days_lost"] += safe_float(injury.get("days_lost", 0.0), default=0.0)

        physical = comp.get("physical_metrics", {}) or {}
        tactical = comp.get("tactical_data", {}) or {}

        flat["sprint_speed_kmh"] += safe_float(physical.get("sprint_speed_kmh", 0.0), default=0.0)
        flat["acceleration"] += map_label(physical.get("acceleration"), PHYSICAL_MAPPING)
        flat["stamina"] += map_label(physical.get("stamina"), PHYSICAL_MAPPING)
        flat["recovery_rate"] += map_label(physical.get("recovery_rate"), PHYSICAL_MAPPING)
        flat["contribution_to_build_up"] += map_label(
            tactical.get("contribution_to_build_up"), TACTICAL_MAPPING
        )
        flat["defensive_transitions"] += map_label(
            tactical.get("defensive_transitions"), TACTICAL_MAPPING
        )

    flat["rating"] = float(np.mean(ratings)) if ratings else float("nan")

    num_comps = len(competitions)
    if num_comps > 0:
        for key in FEATURE_NAMES[14:-1]:
            flat[key] /= num_comps

    flat["age"] = safe_float(season_year, default=0.0) - float(birth_year)
    return flat


def postprocess_loaded_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Training dataframe is empty after loading player seasons.")

    for column in FEATURE_NAMES:
        if column in ["acceleration", "stamina", "recovery_rate", "contribution_to_build_up", "defensive_transitions"]:
            continue
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    # Allow source-only datasets that omit rating by imputing per-player median,
    # then falling back to a global median.
    global_rating = float(df["rating"].median(skipna=True))
    if np.isnan(global_rating):
        global_rating = 6.5

    df["rating"] = df.groupby("player_id")["rating"].transform(lambda s: s.fillna(s.median()))
    df["rating"] = df["rating"].fillna(global_rating)
    df = df.sort_values(["player_id", "season"]).reset_index(drop=True)

    player_count = df["player_id"].nunique()
    retired_count = int(df.groupby("player_id")["is_retired"].max().sum())
    active_count = player_count - retired_count
    print(f"Loaded {len(df)} season rows from {player_count} players ({active_count} active, {retired_count} retired).")
    print(df[["rating", "goals", "assists", "age"]].describe().to_string())
    return df


def load_all_players_df_from_files() -> pd.DataFrame:
    rows: List[Dict[str, object]] = []

    for file_path in PLAYERS_DIR.glob("*.json"):
        with file_path.open(encoding="utf-8") as file:
            data = json.load(file)

        player = data.get("player", {})
        player_id = str(player.get("id", "")).lower().strip()
        player_name = str(player.get("name", "")).strip()
        is_retired = parse_retired_flag(player)
        birth_date = str(player.get("birth_date", "1900-01-01"))
        birth_year = int(birth_date.split("-")[0])

        for season in data.get("seasons", []) or []:
            flat = flatten_season(season, birth_year)
            if not flat:
                continue

            row: Dict[str, object] = {
                "player_id": player_id,
                "player_name": player_name,
                "is_retired": bool(is_retired),
                "season": int(season.get("season", 0)),
            }
            row.update(flat)
            rows.append(row)

    if not rows:
        raise ValueError("No player season rows were loaded from JSON files.")

    return postprocess_loaded_df(pd.DataFrame(rows))


def require_psycopg() -> None:
    if psycopg is None:
        raise RuntimeError("psycopg is required for DB mode. Install backend requirements.")


def load_all_players_df_from_db(conn: Any) -> pd.DataFrame:
    query = """
    select
      p.id as player_id,
      p.name as player_name,
      coalesce(p.is_retired, false) as is_retired,
      s.season,
      coalesce(s.appearances, 0) as appearances,
      coalesce(s.goals, 0) as goals,
      coalesce(s.assists, 0) as assists,
      coalesce(s.minutes, 0) as minutes,
      s.rating as rating,
      coalesce(s.xg, 0) as xg,
      coalesce(s.xa, 0) as xa,
      coalesce(s.key_passes, 0) as key_passes,
      coalesce(s.successful_dribbles, 0) as successful_dribbles,
      coalesce(s.duels_won, 0) as duels_won,
      coalesce(s.shots_per_game, 0) as shots_per_game,
      coalesce(s.tackles_per_game, 0) as tackles_per_game,
      coalesce(s.fouls_drawn, 0) as fouls_drawn,
      coalesce(inj.days_lost, 0) as days_lost,
      coalesce(s.sprint_speed_kmh, 0) as sprint_speed_kmh,
      coalesce(s.acceleration, '') as acceleration,
      coalesce(s.stamina, '') as stamina,
      coalesce(s.recovery_rate, '') as recovery_rate,
      coalesce(s.contribution_to_build_up, '') as contribution_to_build_up,
      coalesce(s.defensive_transitions, '') as defensive_transitions,
      case
        when p.birth_date is not null then extract(year from age(make_date(s.season, 7, 1), p.birth_date))
        else s.season - 20
      end as age
    from player_seasons s
    join players p on p.id = s.player_id
    left join (
      select player_season_id, sum(coalesce(days_lost, 0)) as days_lost
      from injuries
      group by player_season_id
    ) inj on inj.player_season_id = s.id
    order by p.id, s.season
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        columns = [desc.name for desc in cur.description]

    if not rows:
        raise ValueError("No player season rows were loaded from database.")

    df = pd.DataFrame(rows, columns=columns)
    df = df.rename(columns={"xg": "xG", "xa": "xA"})

    # Convert qualitative labels into numeric features used by the model.
    df["acceleration"] = df["acceleration"].apply(lambda v: map_label(v, PHYSICAL_MAPPING))
    df["stamina"] = df["stamina"].apply(lambda v: map_label(v, PHYSICAL_MAPPING))
    df["recovery_rate"] = df["recovery_rate"].apply(lambda v: map_label(v, PHYSICAL_MAPPING))
    df["contribution_to_build_up"] = df["contribution_to_build_up"].apply(
        lambda v: map_label(v, TACTICAL_MAPPING)
    )
    df["defensive_transitions"] = df["defensive_transitions"].apply(
        lambda v: map_label(v, TACTICAL_MAPPING)
    )

    return postprocess_loaded_df(df)


def build_training_sequences(df: pd.DataFrame, window_size: int) -> Tuple[np.ndarray, np.ndarray]:
    x_rows: List[np.ndarray] = []
    y_rows: List[np.ndarray] = []

    for _, group in df.groupby("player_id", sort=False):
        group = group.sort_values("season")
        values = group[FEATURE_NAMES].values.astype(np.float32)

        if len(values) < 2:
            continue

        if len(values) <= window_size:
            # Short-career players still contribute one sample via left-padding.
            history = values[:-1]
            pad_count = window_size - len(history)
            padded = np.repeat(values[:1], pad_count, axis=0) if pad_count > 0 else np.empty((0, values.shape[1]))
            padded_window = np.vstack([padded, history]) if len(history) > 0 else padded
            x_rows.append(padded_window.astype(np.float32))
            y_rows.append(values[-1])
            continue

        for idx in range(window_size, len(values)):
            x_rows.append(values[idx - window_size : idx])
            y_rows.append(values[idx])

    if not x_rows:
        raise ValueError("No training windows could be built. Reduce window size or add more seasons.")

    x = np.array(x_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.float32)
    print(f"Built {len(x)} training windows (window_size={window_size}).")
    return x, y


def build_model(window_size: int, num_features: int) -> Sequential:
    model = Sequential(
        [
            GRU(96, input_shape=(window_size, num_features)),
            Dropout(0.2),
            Dense(64, activation="relu"),
            Dense(num_features),
        ]
    )
    model.compile(optimizer=Adam(learning_rate=1e-3), loss="mse", metrics=["mae"])
    return model


def train_global_model(
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    window_size: int,
    epochs: int,
    batch_size: int,
    seed: int,
) -> Tuple[Sequential, MinMaxScaler, Dict[str, float]]:
    num_features = x_raw.shape[2]
    scaler = MinMaxScaler()

    stacked = np.vstack([x_raw.reshape(-1, num_features), y_raw])
    scaler.fit(stacked)

    x_scaled = scaler.transform(x_raw.reshape(-1, num_features)).reshape(x_raw.shape)
    y_scaled = scaler.transform(y_raw)

    x_train, x_val, y_train, y_val = train_test_split(
        x_scaled, y_scaled, test_size=0.2, random_state=seed
    )

    model = build_model(window_size=window_size, num_features=num_features)
    callbacks = [EarlyStopping(monitor="val_loss", patience=35, restore_best_weights=True)]

    history = model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
        callbacks=callbacks,
    )

    val_pred_scaled = model.predict(x_val, verbose=0)
    val_pred = scaler.inverse_transform(val_pred_scaled)
    val_true = scaler.inverse_transform(y_val)

    mae_all = float(np.mean(np.abs(val_pred - val_true)))
    rating_idx = FEATURE_NAMES.index("rating")
    mae_rating = float(np.mean(np.abs(val_pred[:, rating_idx] - val_true[:, rating_idx])))

    metrics = {
        "epochs_ran": float(len(history.history.get("loss", []))),
        "val_mae_all_features": mae_all,
        "val_mae_rating": mae_rating,
    }
    print(
        f"Model trained. Validation MAE (all features): {mae_all:.4f}, "
        f"rating MAE: {mae_rating:.4f}"
    )
    return model, scaler, metrics


def make_player_window(player_df: pd.DataFrame, window_size: int) -> np.ndarray:
    values = player_df[FEATURE_NAMES].values.astype(np.float32)

    if len(values) >= window_size:
        return values[-window_size:]

    pad_count = window_size - len(values)
    pad = np.repeat(values[:1], pad_count, axis=0)
    return np.vstack([pad, values])


def postprocess_prediction(values: Sequence[float], age: int) -> Dict[str, float]:
    out = dict(zip(FEATURE_NAMES, [float(v) for v in values]))
    out["age"] = float(age)

    for key, value in out.items():
        out[key] = clamp_value(key, float(value))

    return out


def predict_for_player(
    player_id: str,
    full_df: pd.DataFrame,
    model: Sequential,
    scaler: MinMaxScaler,
    window_size: int,
    retirement_age: int,
) -> List[Dict[str, object]]:
    player_df = full_df[full_df["player_id"] == player_id].sort_values("season")
    if player_df.empty:
        raise ValueError(f"Player '{player_id}' has no usable seasons in training dataframe.")

    last_season = int(player_df["season"].max())
    last_age = int(round(float(player_df["age"].iloc[-1])))
    remaining = max(0, retirement_age - last_age)

    if remaining == 0:
        return []

    window = make_player_window(player_df, window_size=window_size)
    predictions: List[Dict[str, object]] = []

    for step in range(remaining):
        x_scaled = scaler.transform(window).reshape(1, window_size, len(FEATURE_NAMES))
        pred_scaled = model.predict(x_scaled, verbose=0)[0]
        pred = scaler.inverse_transform(pred_scaled.reshape(1, -1))[0]

        season = last_season + step + 1
        age = last_age + step + 1
        pred_row = postprocess_prediction(pred, age=age)
        pred_row["season"] = season
        predictions.append(ensure_py_types(pred_row))

        next_vec = np.array([pred_row[name] for name in FEATURE_NAMES], dtype=np.float32)
        window = np.vstack([window[1:], next_vec])

    return predictions


def save_predictions_to_files(
    player_id: str,
    predictions: List[Dict[str, object]],
    copy_to_frontend: bool,
) -> None:
    backend_file = PREDICTIONS_DIR / f"{player_id}_predictions.json"
    with backend_file.open("w", encoding="utf-8") as file:
        json.dump(predictions, file, indent=2)
    print(f"Saved backend predictions: {backend_file}")

    if copy_to_frontend:
        FRONTEND_PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
        frontend_file = FRONTEND_PREDICTIONS_DIR / f"{player_id}.json"
        with frontend_file.open("w", encoding="utf-8") as file:
            json.dump(predictions, file, indent=2)
        print(f"Saved frontend predictions: {frontend_file}")


def create_prediction_run(
    conn: Any,
    run_type: str,
    triggered_by: str,
    model_version: str,
    meta: Dict[str, Any],
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into prediction_runs(run_type, status, model_version, triggered_by, meta)
            values (%s, 'running', %s, %s, %s::jsonb)
            returning id
            """,
            (run_type, model_version, triggered_by, json.dumps(meta)),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return str(run_id)


def finalize_prediction_run(
    conn: Any,
    run_id: str,
    status: str,
    error_message: Optional[str],
    meta: Dict[str, Any],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            update prediction_runs
            set status = %s,
                ended_at = now(),
                error_message = %s,
                meta = coalesce(meta, '{}'::jsonb) || %s::jsonb
            where id = %s
            """,
            (status, error_message, json.dumps(meta), run_id),
        )
    conn.commit()



def acquire_prediction_run_lock(conn: Any) -> bool:
    with conn.cursor() as cur:
        cur.execute("select pg_try_advisory_lock(%s)", (PREDICTION_RUN_LOCK_KEY,))
        row = cur.fetchone()
    return bool(row and row[0])


def release_prediction_run_lock(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("select pg_advisory_unlock(%s)", (PREDICTION_RUN_LOCK_KEY,))

def save_predictions_to_db(
    conn: Any,
    run_id: str,
    player_id: str,
    predictions: List[Dict[str, object]],
    confidence_score: Optional[float],
) -> None:
    horizon = len(predictions)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into player_predictions(
              run_id, player_id, predicted_at, horizon_seasons, prediction_json, confidence_score
            )
            values (%s, %s, now(), %s, %s::jsonb, %s)
            on conflict (run_id, player_id, horizon_seasons) do update set
              prediction_json = excluded.prediction_json,
              confidence_score = excluded.confidence_score,
              predicted_at = now()
            """,
            (run_id, player_id, horizon, json.dumps(predictions), confidence_score),
        )
    conn.commit()


def set_seeds(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a global player-career predictor and export predictions.")
    parser.add_argument("--player-id", default="mbappe", help="Target player id for single-player prediction mode.")
    parser.add_argument(
        "--all-players",
        action="store_true",
        help="Generate predictions for all players in data (active only by default).",
    )
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="Generate predictions for active players only.",
    )
    parser.add_argument(
        "--include-retired",
        action="store_true",
        help="When used with --all-players/--all-active, include players marked as retired.",
    )
    parser.add_argument("--window-size", type=int, default=4, help="Historical seasons used for next-season prediction.")
    parser.add_argument("--retirement-age", type=int, default=35, help="Maximum age to forecast to.")
    parser.add_argument("--epochs", type=int, default=300, help="Maximum training epochs.")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--copy-to-frontend",
        action="store_true",
        help="When writing files, also write JSON files into frontend/public/data/predictions.",
    )
    parser.add_argument(
        "--data-source",
        choices=["files", "db"],
        default="files",
        help="Where training/input data is read from.",
    )
    parser.add_argument(
        "--output-target",
        choices=["files", "db", "both"],
        default="files",
        help="Where predictions are written.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Postgres connection string for DB mode.",
    )
    parser.add_argument(
        "--run-type",
        default="manual",
        help="prediction_runs.run_type value when output includes DB.",
    )
    parser.add_argument(
        "--triggered-by",
        default="local",
        help="prediction_runs.triggered_by value when output includes DB.",
    )
    parser.add_argument(
        "--model-version",
        default="gru-v2",
        help="Version label persisted with prediction runs in DB mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seeds(args.seed)

    needs_db = args.data_source == "db" or args.output_target in {"db", "both"}
    db_conn = None
    lock_acquired = False

    if needs_db:
        require_psycopg()
        database_url = args.database_url.strip()
        if not database_url:
            raise ValueError("DB mode requested but no DATABASE_URL / --database-url was provided.")
        db_conn = psycopg.connect(database_url)

        if args.output_target in {"db", "both"}:
            lock_acquired = acquire_prediction_run_lock(db_conn)
            if not lock_acquired:
                raise RuntimeError("Another prediction run is currently active. Try again after it finishes.")

    run_id: Optional[str] = None
    failures: List[str] = []

    try:
        if args.data_source == "db":
            df = load_all_players_df_from_db(db_conn)
        else:
            df = load_all_players_df_from_files()

        x_raw, y_raw = build_training_sequences(df, window_size=args.window_size)
        model, scaler, metrics = train_global_model(
            x_raw=x_raw,
            y_raw=y_raw,
            window_size=args.window_size,
            epochs=args.epochs,
            batch_size=args.batch_size,
            seed=args.seed,
        )

        if args.all_players or args.all_active:
            player_index = (
                df.sort_values(["player_id", "season"])
                .groupby("player_id", as_index=False)["is_retired"]
                .max()
            )

            if not args.include_retired:
                player_index = player_index[player_index["is_retired"] == False]
                print("Skipping retired players in bulk generation (use --include-retired to override).")
            else:
                print("Including retired players in bulk generation.")

            target_ids = sorted(player_index["player_id"].tolist())
        else:
            target_ids = [args.player_id.lower().strip()]

        if not target_ids:
            raise ValueError("No target players selected. Check retired flags or use --include-retired.")

        print(f"Generating predictions for: {', '.join(target_ids)}")
        print(f"Training metrics: {metrics}")

        confidence = 1.0 / (1.0 + metrics.get("val_mae_rating", 1.0))
        confidence = float(max(0.0, min(1.0, confidence)))

        if args.output_target in {"db", "both"}:
            run_meta = {
                "data_source": args.data_source,
                "window_size": args.window_size,
                "retirement_age": args.retirement_age,
                "metrics": metrics,
                "seed": args.seed,
                "player_count": len(target_ids),
            }
            run_id = create_prediction_run(
                conn=db_conn,
                run_type=args.run_type,
                triggered_by=args.triggered_by,
                model_version=args.model_version,
                meta=run_meta,
            )
            print(f"Created prediction run: {run_id}")

        for player_id in target_ids:
            try:
                predictions = predict_for_player(
                    player_id=player_id,
                    full_df=df,
                    model=model,
                    scaler=scaler,
                    window_size=args.window_size,
                    retirement_age=args.retirement_age,
                )

                if args.output_target in {"files", "both"}:
                    save_predictions_to_files(
                        player_id=player_id,
                        predictions=predictions,
                        copy_to_frontend=args.copy_to_frontend,
                    )

                if args.output_target in {"db", "both"} and run_id is not None:
                    save_predictions_to_db(
                        conn=db_conn,
                        run_id=run_id,
                        player_id=player_id,
                        predictions=predictions,
                        confidence_score=confidence,
                    )
                    print(f"Saved DB prediction: {player_id} (horizon={len(predictions)})")
            except Exception as exc:
                failures.append(player_id)
                print(f"[WARN] Failed for {player_id}: {exc}")

        if run_id is not None:
            status = "success" if not failures else "failed"
            finalize_prediction_run(
                conn=db_conn,
                run_id=run_id,
                status=status,
                error_message=None if not failures else f"Failed players: {', '.join(failures)}",
                meta={"failures": failures, "succeeded": len(target_ids) - len(failures)},
            )

        if failures:
            print(f"Finished with failures for: {', '.join(failures)}")
            raise RuntimeError(f"Prediction generation failed for: {', '.join(failures)}")

        print("Finished successfully for all requested players.")
    except Exception as exc:
        if run_id is not None and db_conn is not None:
            try:
                finalize_prediction_run(
                    conn=db_conn,
                    run_id=run_id,
                    status="failed",
                    error_message=str(exc),
                    meta={"failures": failures},
                )
            except Exception:
                pass
        raise
    finally:
        if db_conn is not None:
            if lock_acquired:
                try:
                    release_prediction_run_lock(db_conn)
                except Exception:
                    pass
            db_conn.close()


if __name__ == "__main__":
    main()






