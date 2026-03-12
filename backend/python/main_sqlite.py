import argparse
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from main import (
    PHYSICAL_MAPPING,
    TACTICAL_MAPPING,
    ensure_py_types,
    load_all_players_df_from_files,
    map_label,
    postprocess_loaded_df,
    build_training_sequences,
    predict_for_player,
    save_predictions_to_files,
    set_seeds,
    train_global_model,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "data" / "proxima.sqlite3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train predictor using SQLite or JSON files and export predictions.")
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
        choices=["files", "sqlite"],
        default="files",
        help="Where training/input data is read from.",
    )
    parser.add_argument(
        "--output-target",
        choices=["files", "sqlite", "both"],
        default="files",
        help="Where predictions are written.",
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_DATABASE_PATH", str(DEFAULT_SQLITE_PATH)),
        help="SQLite database file path for sqlite mode.",
    )
    parser.add_argument(
        "--run-type",
        default="manual",
        help="prediction_runs.run_type value when output includes sqlite.",
    )
    parser.add_argument(
        "--triggered-by",
        default="local",
        help="prediction_runs.triggered_by value when output includes sqlite.",
    )
    parser.add_argument(
        "--model-version",
        default="gru-v2-sqlite",
        help="Version label persisted with prediction runs in sqlite mode.",
    )
    return parser.parse_args()


def open_sqlite_connection(sqlite_path: str) -> sqlite3.Connection:
    path = Path(sqlite_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_all_players_df_from_sqlite(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    select
      p.id as player_id,
      p.name as player_name,
      coalesce(p.is_retired, 0) as is_retired,
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
        when p.birth_date is not null then
          cast(strftime('%Y', printf('%04d-07-01', s.season)) as integer) - cast(strftime('%Y', p.birth_date) as integer)
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

    cur = conn.execute(query)
    rows = cur.fetchall()
    columns = [desc[0] for desc in (cur.description or [])]

    if not rows:
        raise ValueError("No player season rows were loaded from sqlite.")

    df = pd.DataFrame(rows, columns=columns)
    df = df.rename(columns={"xg": "xG", "xa": "xA"})

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


def create_prediction_run(
    conn: sqlite3.Connection,
    run_type: str,
    triggered_by: str,
    model_version: str,
    meta: Dict[str, Any],
) -> str:
    run_id = str(uuid.uuid4())
    conn.execute(
        """
        insert into prediction_runs(id, run_type, status, model_version, triggered_by, meta)
        values (?, ?, 'running', ?, ?, ?)
        """,
        (run_id, run_type, model_version, triggered_by, json.dumps(meta)),
    )
    conn.commit()
    return run_id


def finalize_prediction_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    error_message: Optional[str],
    meta: Dict[str, Any],
) -> None:
    current_meta_row = conn.execute("select meta from prediction_runs where id = ?", (run_id,)).fetchone()
    current_meta: Dict[str, Any] = {}
    if current_meta_row and current_meta_row[0]:
        try:
            current_meta = json.loads(current_meta_row[0])
        except Exception:
            current_meta = {}

    merged_meta = {**current_meta, **meta}

    conn.execute(
        """
        update prediction_runs
        set status = ?,
            ended_at = CURRENT_TIMESTAMP,
            error_message = ?,
            meta = ?
        where id = ?
        """,
        (status, error_message, json.dumps(merged_meta), run_id),
    )
    conn.commit()


def save_predictions_to_sqlite(
    conn: sqlite3.Connection,
    run_id: str,
    player_id: str,
    predictions: List[Dict[str, object]],
    confidence_score: Optional[float],
) -> None:
    horizon = len(predictions)
    conn.execute(
        """
        insert into player_predictions(
          run_id, player_id, predicted_at, horizon_seasons, prediction_json, confidence_score
        )
        values (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
        on conflict (run_id, player_id, horizon_seasons) do update set
          prediction_json = excluded.prediction_json,
          confidence_score = excluded.confidence_score,
          predicted_at = CURRENT_TIMESTAMP
        """,
        (run_id, player_id, horizon, json.dumps(predictions), confidence_score),
    )
    conn.commit()


def main() -> None:
    args = parse_args()
    set_seeds(args.seed)

    needs_sqlite = args.data_source == "sqlite" or args.output_target in {"sqlite", "both"}
    sqlite_conn: Optional[sqlite3.Connection] = None

    if needs_sqlite:
        sqlite_conn = open_sqlite_connection(args.sqlite_path)

    run_id: Optional[str] = None
    failures: List[str] = []

    try:
        if args.data_source == "sqlite":
            if sqlite_conn is None:
                raise ValueError("SQLite connection was not initialized.")
            df = load_all_players_df_from_sqlite(sqlite_conn)
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
                df.sort_values(["player_id", "season"]).groupby("player_id", as_index=False)["is_retired"].max()
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

        if args.output_target in {"sqlite", "both"}:
            if sqlite_conn is None:
                raise ValueError("SQLite output requested but SQLite connection is unavailable.")

            run_meta = {
                "data_source": args.data_source,
                "window_size": args.window_size,
                "retirement_age": args.retirement_age,
                "metrics": metrics,
                "seed": args.seed,
                "player_count": len(target_ids),
            }
            run_id = create_prediction_run(
                conn=sqlite_conn,
                run_type=args.run_type,
                triggered_by=args.triggered_by,
                model_version=args.model_version,
                meta=run_meta,
            )
            print(f"Created sqlite prediction run: {run_id}")

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

                if args.output_target in {"sqlite", "both"} and run_id is not None and sqlite_conn is not None:
                    save_predictions_to_sqlite(
                        conn=sqlite_conn,
                        run_id=run_id,
                        player_id=player_id,
                        predictions=predictions,
                        confidence_score=confidence,
                    )
                    print(f"Saved sqlite prediction: {player_id} (horizon={len(predictions)})")
            except Exception as exc:
                if sqlite_conn is not None:
                    sqlite_conn.rollback()
                failures.append(player_id)
                print(f"[WARN] Failed for {player_id}: {exc}")

        if run_id is not None and sqlite_conn is not None:
            status = "success" if not failures else "failed"
            finalize_prediction_run(
                conn=sqlite_conn,
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
        if sqlite_conn is not None:
            sqlite_conn.rollback()

        if run_id is not None and sqlite_conn is not None:
            try:
                finalize_prediction_run(
                    conn=sqlite_conn,
                    run_id=run_id,
                    status="failed",
                    error_message=str(exc),
                    meta={"failures": failures},
                )
            except Exception:
                pass
        raise
    finally:
        if sqlite_conn is not None:
            sqlite_conn.close()


if __name__ == "__main__":
    main()

