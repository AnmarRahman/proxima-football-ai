"""Run approved Tier A inference from Postgres and upsert current predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


HERE = Path(__file__).resolve().parent
DEFAULT_ARTIFACT_DIR = HERE / "model_artifacts" / "tier_a_v1"
PREDICT_SCRIPT = HERE / "predict_next_season.py"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_sha256(player: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(player).encode("utf-8")).hexdigest()


def build_player_input(player: dict[str, Any], seasons: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "player_id": player["id"],
        "primary_position": player.get("primary_position"),
        "position_group": player.get("position_group"),
        "coarse_group": player["coarse_group"],
        "career_status": player["career_status"],
        "birth_date": str(player["birth_date"]),
        "stat_scope": player["stat_scope"],
        "seasons": [
            {
                "canonical_season": row["canonical_season"],
                "season_start_year": int(row["season_start_year"]),
                "season_end_year": int(row["season_end_year"]),
                "season_format": row["season_format"],
                "appearances": int(row["appearances"]),
                "goals": int(row["goals"]),
                "is_partial": bool(row["is_partial"]),
                "model_eligible": bool(row["model_eligible"]),
            }
            for row in seasons
        ],
    }


def prediction_point(player_input: dict[str, Any]) -> str:
    eligible = [row for row in player_input["seasons"] if row["model_eligible"]]
    return "latest-completed" if eligible and eligible[-1]["is_partial"] else "next"


def run_inference(
    player_input: dict[str, Any], artifact_dir: Path, expected_manifest_sha: str
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    command = [
        sys.executable,
        str(PREDICT_SCRIPT),
        "--artifact-dir",
        str(artifact_dir),
        "--prediction-point",
        prediction_point(player_input),
        "--expected-manifest-sha256",
        expected_manifest_sha,
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        command,
        input=json.dumps(player_input, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None, {"code": "INVALID_INFERENCE_OUTPUT", "message": completed.stderr[-1000:]}
    if completed.returncode != 0 or "error" in payload:
        error = payload.get("error") or {}
        return None, {
            "code": str(error.get("code") or "INFERENCE_FAILED"),
            "message": str(error.get("message") or completed.stderr[-1000:]),
        }
    return payload, None


def interval_values(block: dict[str, Any]) -> tuple[int | None, int | None, str | None, str | None]:
    interval = block.get("interval")
    if not isinstance(interval, dict):
        return None, None, None, block.get("interval_unavailable_reason")
    return (
        int(interval["lower"]),
        int(interval["upper"]),
        interval.get("method"),
        None,
    )


def upsert_prediction(
    cur: psycopg.Cursor,
    run_id: Any,
    model_version: str,
    player_input: dict[str, Any],
    prediction: dict[str, Any],
) -> None:
    app_lo, app_hi, app_method, app_reason = interval_values(prediction["appearances"])
    goal_lo, goal_hi, goal_method, _ = interval_values(prediction["goals"])
    cur.execute(
        """
        insert into next_season_predictions(
          player_id, run_id, model_version, prediction_scope, prediction_point,
          based_on_season, predicted_season, appearances_expected,
          appearances_lower, appearances_upper, appearances_interval_method,
          appearances_interval_unavailable_reason, goals_expected, goals_lower,
          goals_upper, goals_interval_method, limitations, coverage_metadata,
          prediction_json, input_sha256, predicted_at, updated_at
        ) values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, now()
        )
        on conflict (player_id) do update set
          run_id = excluded.run_id,
          model_version = excluded.model_version,
          prediction_scope = excluded.prediction_scope,
          prediction_point = excluded.prediction_point,
          based_on_season = excluded.based_on_season,
          predicted_season = excluded.predicted_season,
          appearances_expected = excluded.appearances_expected,
          appearances_lower = excluded.appearances_lower,
          appearances_upper = excluded.appearances_upper,
          appearances_interval_method = excluded.appearances_interval_method,
          appearances_interval_unavailable_reason = excluded.appearances_interval_unavailable_reason,
          goals_expected = excluded.goals_expected,
          goals_lower = excluded.goals_lower,
          goals_upper = excluded.goals_upper,
          goals_interval_method = excluded.goals_interval_method,
          limitations = excluded.limitations,
          coverage_metadata = excluded.coverage_metadata,
          prediction_json = excluded.prediction_json,
          input_sha256 = excluded.input_sha256,
          predicted_at = excluded.predicted_at,
          updated_at = now()
        """,
        (
            prediction["player_id"],
            run_id,
            model_version,
            prediction["prediction_scope"],
            prediction["prediction_point"],
            prediction.get("based_on_season"),
            prediction.get("predicted_season"),
            int(prediction["appearances"]["expected"]),
            app_lo,
            app_hi,
            app_method,
            app_reason,
            int(prediction["goals"]["expected"]),
            goal_lo,
            goal_hi,
            goal_method,
            Jsonb(prediction.get("limitations") or []),
            Jsonb(prediction.get("coverage_metadata") or {}),
            Jsonb(prediction),
            input_sha256(player_input),
            prediction["model"]["generated_at"],
        ),
    )


def fetch_inputs(cur: psycopg.Cursor, player_id: str | None) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = "where career_status = 'active'"
    if player_id:
        where += " and id = %s"
        params.append(player_id)
    cur.execute(
        f"""
        select id, name, birth_date, nationality, primary_position,
               position_group, coarse_group, career_status, stat_scope
        from ml_players
        {where}
        order by id
        """,
        params,
    )
    columns = [description.name for description in cur.description]
    players = [dict(zip(columns, row)) for row in cur.fetchall()]
    if player_id and not players:
        raise ValueError(f"Active Tier A player not found: {player_id}")

    if not players:
        return []
    ids = [player["id"] for player in players]
    cur.execute(
        """
        select player_id, canonical_season, season_start_year, season_end_year,
               season_format, appearances, goals, is_partial, model_eligible
        from ml_player_seasons
        where player_id = any(%s)
        order by player_id, season_start_year, season_end_year, canonical_season
        """,
        (ids,),
    )
    season_columns = [description.name for description in cur.description]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cur.fetchall():
        item = dict(zip(season_columns, row))
        grouped[item.pop("player_id")].append(item)
    return [build_player_input(player, grouped.get(player["id"], [])) for player in players]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument(
        "--expected-manifest-sha256",
        default=os.getenv("TIER_A_EXPECTED_MANIFEST_SHA256", ""),
        help="Trusted out-of-band digest for the approved model manifest.",
    )
    parser.add_argument("--player-id")
    parser.add_argument("--run-type", default="manual")
    parser.add_argument("--triggered-by", default="local")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.database_url.strip():
        raise SystemExit("Missing DATABASE_URL or --database-url")
    artifact_dir = args.artifact_dir.resolve()
    manifest = json.loads((artifact_dir / "model_manifest.json").read_text(encoding="utf-8"))
    manifest_sha = (artifact_dir / "manifest.sha256").read_text(encoding="utf-8").strip()
    if args.expected_manifest_sha256 and args.expected_manifest_sha256 != manifest_sha:
        raise ValueError("Approved model manifest does not match the trusted release digest")
    model_version = manifest["model_version"]

    with psycopg.connect(args.database_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select approved, manifest_sha256 from model_versions where version = %s",
                (model_version,),
            )
            model_row = cur.fetchone()
            if not model_row or not model_row[0] or model_row[1] != manifest_sha:
                raise ValueError(f"Model {model_version} is not registered and approved with this manifest")
            cur.execute(
                """
                insert into tier_a_prediction_runs(
                  status, run_type, triggered_by, model_version, requested_player_id
                ) values ('running', %s, %s, %s, %s)
                returning id
                """,
                (args.run_type, args.triggered_by, model_version, args.player_id),
            )
            run_id = cur.fetchone()[0]
            player_inputs = fetch_inputs(cur, args.player_id)
        conn.commit()

        predicted = 0
        rejected: list[dict[str, str]] = []
        try:
            with conn.cursor() as cur:
                for player_input in player_inputs:
                    prediction, error = run_inference(player_input, artifact_dir, manifest_sha)
                    if error:
                        rejected.append({"player_id": player_input["player_id"], **error})
                        cur.execute(
                            "delete from next_season_predictions where player_id = %s",
                            (player_input["player_id"],),
                        )
                        print(f"[REJECTED] {player_input['player_id']}: {error['code']} - {error['message']}")
                        continue
                    upsert_prediction(cur, run_id, model_version, player_input, prediction)
                    predicted += 1
                    print(f"Predicted {player_input['player_id']}: apps={prediction['appearances']['expected']}, goals={prediction['goals']['expected']}")

                if not args.player_id:
                    cur.execute(
                        """
                        delete from next_season_predictions nsp
                        using ml_players p
                        where nsp.player_id = p.id and p.career_status <> 'active'
                        """
                    )
                cur.execute(
                    """
                    update tier_a_prediction_runs
                    set status = 'success', ended_at = now(), predicted_count = %s,
                        rejected_count = %s, meta = %s
                    where id = %s
                    """,
                    (predicted, len(rejected), Jsonb({"rejections": rejected}), run_id),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update tier_a_prediction_runs
                    set status = 'failed', ended_at = now(), error_message = %s
                    where id = %s
                    """,
                    (str(exc), run_id),
                )
            conn.commit()
            raise

    print(f"Tier A prediction run complete: run_id={run_id}, predicted={predicted}, rejected={len(rejected)}")


if __name__ == "__main__":
    main()
