import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("psycopg is required. Install backend requirements first.") from exc

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PLAYERS_DIR = BASE_DIR / "data" / "players"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import player JSON files into Postgres.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Postgres connection string. Defaults to DATABASE_URL env var.",
    )
    parser.add_argument(
        "--players-dir",
        default=str(DEFAULT_PLAYERS_DIR),
        help="Directory containing player JSON files.",
    )
    return parser.parse_args()


def to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def parse_retired(player: Dict[str, Any]) -> bool:
    raw = player.get("is_retired", player.get("retired", False))
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    return str(raw).strip().lower() in {"1", "true", "yes", "retired", "y"}


def ensure_team(cur: psycopg.Cursor, team_id: Optional[str], name: Optional[str] = None) -> None:
    if not team_id:
        return
    clean_id = str(team_id).strip().lower()
    if not clean_id:
        return

    clean_name = (name or clean_id.replace("-", " ").title()).strip()
    cur.execute(
        """
        insert into teams(id, name)
        values (%s, %s)
        on conflict (id) do update set
          name = coalesce(excluded.name, teams.name),
          updated_at = now()
        """,
        (clean_id, clean_name),
    )


def upsert_player(cur: psycopg.Cursor, player: Dict[str, Any]) -> None:
    player_id = str(player.get("id", "")).strip().lower()
    if not player_id:
        raise ValueError("Player is missing id")

    cur.execute(
        """
        insert into players(
          id, name, birth_date, nationality, height_cm, weight_kg, dominant_foot, is_retired, retired_since
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
          name = excluded.name,
          birth_date = excluded.birth_date,
          nationality = excluded.nationality,
          height_cm = excluded.height_cm,
          weight_kg = excluded.weight_kg,
          dominant_foot = excluded.dominant_foot,
          is_retired = excluded.is_retired,
          retired_since = excluded.retired_since,
          updated_at = now()
        """,
        (
            player_id,
            str(player.get("name", player_id)),
            to_date(player.get("birth_date")),
            player.get("nationality"),
            to_int(player.get("height_cm")),
            to_int(player.get("weight_kg")),
            player.get("dominant_foot"),
            parse_retired(player),
            to_date(player.get("retired_since")),
        ),
    )


def upsert_player_season(
    cur: psycopg.Cursor,
    player_id: str,
    season: Dict[str, Any],
) -> int:
    team_id = str(season.get("team_id", "")).strip().lower() or None
    league_id = str(season.get("league_id", "")).strip().lower() or "unknown"

    physical = season.get("physical_metrics") or {}
    tactical = season.get("tactical_data") or {}

    if team_id:
        ensure_team(cur, team_id)

    cur.execute(
        """
        insert into player_seasons(
          player_id, season, team_id, league_id, appearances, goals, assists, minutes,
          position, rating, xg, xa, key_passes, successful_dribbles, duels_won,
          shots_per_game, tackles_per_game, fouls_drawn,
          sprint_speed_kmh, acceleration, stamina, recovery_rate,
          contribution_to_build_up, defensive_transitions, raw_json
        )
        values (
          %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s::jsonb
        )
        on conflict (player_id, season, team_id, league_id) do update set
          appearances = excluded.appearances,
          goals = excluded.goals,
          assists = excluded.assists,
          minutes = excluded.minutes,
          position = excluded.position,
          rating = excluded.rating,
          xg = excluded.xg,
          xa = excluded.xa,
          key_passes = excluded.key_passes,
          successful_dribbles = excluded.successful_dribbles,
          duels_won = excluded.duels_won,
          shots_per_game = excluded.shots_per_game,
          tackles_per_game = excluded.tackles_per_game,
          fouls_drawn = excluded.fouls_drawn,
          sprint_speed_kmh = excluded.sprint_speed_kmh,
          acceleration = excluded.acceleration,
          stamina = excluded.stamina,
          recovery_rate = excluded.recovery_rate,
          contribution_to_build_up = excluded.contribution_to_build_up,
          defensive_transitions = excluded.defensive_transitions,
          raw_json = excluded.raw_json,
          updated_at = now()
        returning id
        """,
        (
            player_id,
            to_int(season.get("season")),
            team_id,
            league_id,
            to_int(season.get("appearances")),
            to_int(season.get("goals")),
            to_int(season.get("assists")),
            to_int(season.get("minutes")),
            season.get("position"),
            to_float(season.get("rating")),
            to_float(season.get("xG", season.get("xg"))),
            to_float(season.get("xA", season.get("xa"))),
            to_int(season.get("key_passes")),
            to_int(season.get("successful_dribbles")),
            to_int(season.get("duels_won")),
            to_float(season.get("shots_per_game")),
            to_float(season.get("tackles_per_game")),
            to_int(season.get("fouls_drawn")),
            to_float(physical.get("sprint_speed_kmh")),
            physical.get("acceleration"),
            physical.get("stamina"),
            physical.get("recovery_rate"),
            tactical.get("contribution_to_build_up"),
            tactical.get("defensive_transitions"),
            json.dumps(season),
        ),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Could not upsert player season row")
    return int(row[0])


def replace_season_children(cur: psycopg.Cursor, player_season_id: int, season: Dict[str, Any]) -> None:
    cur.execute("delete from season_national_stats where player_season_id = %s", (player_season_id,))
    cur.execute("delete from injuries where player_season_id = %s", (player_season_id,))
    cur.execute("delete from transfers where player_season_id = %s", (player_season_id,))

    for nat in season.get("national_team_stats") or []:
        team_id = str(nat.get("team_id", "")).strip().lower() or None
        if team_id:
            ensure_team(cur, team_id)

        cur.execute(
            """
            insert into season_national_stats(
              player_season_id, team_id, competition, appearances, goals, assists,
              minutes, position, rating, raw_json
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                player_season_id,
                team_id,
                nat.get("competition"),
                to_int(nat.get("appearances")),
                to_int(nat.get("goals")),
                to_int(nat.get("assists")),
                to_int(nat.get("minutes")),
                nat.get("position"),
                to_float(nat.get("rating")),
                json.dumps(nat),
            ),
        )

    for injury in season.get("injuries") or []:
        cur.execute(
            """
            insert into injuries(
              player_season_id, injury_type, start_date, end_date,
              days_lost, source, raw_json
            )
            values (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                player_season_id,
                injury.get("type"),
                to_date(injury.get("start_date")),
                to_date(injury.get("end_date")),
                to_int(injury.get("days_lost")),
                injury.get("source"),
                json.dumps(injury),
            ),
        )

    for tr in season.get("transfer_history") or []:
        from_id = str(tr.get("from", "")).strip().lower() or None
        to_id = str(tr.get("to", "")).strip().lower() or None

        ensure_team(cur, from_id)
        ensure_team(cur, to_id)

        cur.execute(
            """
            insert into transfers(
              player_season_id, from_team_id, to_team_id, transfer_fee,
              transfer_date, source, raw_json
            )
            values (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                player_season_id,
                from_id,
                to_id,
                tr.get("transfer_fee"),
                to_date(tr.get("date") or tr.get("transfer_date")),
                tr.get("source"),
                json.dumps(tr),
            ),
        )


def import_file(cur: psycopg.Cursor, file_path: Path) -> Dict[str, int]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    player = data.get("player") or {}

    upsert_player(cur, player)

    for team in data.get("teams") or []:
        ensure_team(cur, str(team.get("id", "")).strip().lower() or None, team.get("name"))
        cur.execute(
            """
            update teams
            set country = %s,
                logo_url = %s,
                updated_at = now()
            where id = %s
            """,
            (team.get("country"), team.get("logo_url"), str(team.get("id", "")).strip().lower()),
        )

    player_id = str(player.get("id", "")).strip().lower()
    season_count = 0

    for season in data.get("seasons") or []:
        season_id = upsert_player_season(cur, player_id, season)
        replace_season_children(cur, season_id, season)
        season_count += 1

    return {"seasons": season_count}


def iter_player_files(players_dir: Path) -> Iterable[Path]:
    for file_path in sorted(players_dir.glob("*.json")):
        if file_path.name.endswith("_predictions.json"):
            continue
        yield file_path


def main() -> None:
    args = parse_args()
    database_url = args.database_url.strip()
    if not database_url:
        raise SystemExit("Missing database url. Set DATABASE_URL or pass --database-url.")

    players_dir = Path(args.players_dir).resolve()
    if not players_dir.exists():
        raise SystemExit(f"Players directory does not exist: {players_dir}")

    imported = 0
    failed = 0
    total_seasons = 0

    with psycopg.connect(database_url) as conn:
        for file_path in iter_player_files(players_dir):
            try:
                with conn.cursor() as cur:
                    stats = import_file(cur, file_path)
                conn.commit()
                imported += 1
                total_seasons += stats["seasons"]
                print(f"Imported {file_path.name}: {stats['seasons']} seasons")
            except Exception as exc:
                conn.rollback()
                failed += 1
                print(f"[ERROR] Failed importing {file_path.name}: {exc}")

    print(
        f"Import complete. files_imported={imported}, files_failed={failed}, seasons_imported={total_seasons}"
    )


if __name__ == "__main__":
    main()
