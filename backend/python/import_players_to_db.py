import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("psycopg is required. Install backend requirements first.") from exc

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PLAYERS_DIR = BASE_DIR / "data" / "players"
STATUS_OVERRIDES_FILENAME = "player_status_overrides.json"
UNKNOWN_TEAM_ID = "unknown-team"
UNKNOWN_TEAM_NAME = "Unknown Team"


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
    parser.add_argument(
        "--over-age-threshold",
        type=int,
        default=35,
        help="Mark players as over_35 when their latest known season age is >= this value.",
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


def normalize_slug(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    raw = str(value).strip().lower()
    if not raw:
        return default
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug or default


def normalize_team_id(value: Any) -> str:
    if value is None:
        return UNKNOWN_TEAM_ID
    clean = str(value).strip().lower()
    return clean or UNKNOWN_TEAM_ID


def explode_season_rows(season: Dict[str, Any]) -> List[Dict[str, Any]]:
    season_year = to_int(season.get("season"))
    if season_year is None:
        return []

    season_level_national = season.get("national_team_stats") or []
    season_level_injuries = season.get("injuries") or []
    season_level_transfers = season.get("transfer_history") or []
    season_level_physical = season.get("physical_metrics") or {}
    season_level_tactical = season.get("tactical_data") or {}

    rows: List[Dict[str, Any]] = []

    teams = season.get("teams") or []
    if isinstance(teams, list):
        for team_entry in teams:
            if not isinstance(team_entry, dict):
                continue

            team_id = normalize_team_id(team_entry.get("team_id") or season.get("team_id"))
            competitions = team_entry.get("competitions") or []
            if not isinstance(competitions, list) or not competitions:
                competitions = [{}]

            for comp in competitions:
                if not isinstance(comp, dict):
                    continue

                competition_name = str(comp.get("competition", "")).strip()
                row = dict(comp)
                row["season"] = season_year
                row["team_id"] = team_id
                row["league_id"] = normalize_slug(comp.get("league_id") or competition_name or season.get("league_id"))
                row["national_team_stats"] = comp.get("national_team_stats", season_level_national) or []
                row["injuries"] = comp.get("injuries", season_level_injuries) or []
                row["transfer_history"] = comp.get("transfer_history", season_level_transfers) or []
                row["physical_metrics"] = comp.get("physical_metrics", season_level_physical) or {}
                row["tactical_data"] = comp.get("tactical_data", season_level_tactical) or {}
                rows.append(row)

    if rows:
        return rows

    fallback = dict(season)
    fallback["season"] = season_year
    fallback["team_id"] = normalize_team_id(season.get("team_id"))
    fallback["league_id"] = normalize_slug(season.get("league_id"))
    fallback["national_team_stats"] = season_level_national
    fallback["injuries"] = season_level_injuries
    fallback["transfer_history"] = season_level_transfers
    fallback["physical_metrics"] = season_level_physical
    fallback["tactical_data"] = season_level_tactical
    return [fallback]


def parse_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "retired"}:
        return True
    if normalized in {"0", "false", "no", "n", "active"}:
        return False
    return default


def parse_birth_year(player: Dict[str, Any]) -> Optional[int]:
    birth_date = player.get("birth_date")
    if not birth_date:
        return None

    try:
        return int(str(birth_date).split("-")[0])
    except Exception:
        return None


def compute_over_age(player: Dict[str, Any], seasons: List[Dict[str, Any]], threshold: int) -> bool:
    explicit = parse_bool(player.get("over_35", player.get("over35")), default=None)
    if explicit is not None:
        return explicit

    birth_year = parse_birth_year(player)
    if birth_year is None:
        return False

    season_years: List[int] = []
    for season in seasons or []:
        if not isinstance(season, dict):
            continue
        season_val = to_int(season.get("season"))
        if season_val is not None:
            season_years.append(season_val)

    if not season_years:
        return False

    last_season_year = max(season_years)
    return (last_season_year - birth_year) >= threshold


def load_status_overrides(path: Path) -> Dict[str, Set[str]]:
    if not path.exists():
        return {"retired_ids": set(), "active_ids": set()}

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    retired_ids = {str(v).strip().lower() for v in (data.get("retired_ids") or []) if str(v).strip()}
    active_ids = {str(v).strip().lower() for v in (data.get("active_ids") or []) if str(v).strip()}
    return {"retired_ids": retired_ids, "active_ids": active_ids}
def parse_retired(
    player: Dict[str, Any],
    player_id: str,
    retired_ids: Set[str],
    active_ids: Set[str],
) -> bool:
    # Explicit flags in player JSON always win.
    if "is_retired" in player or "retired" in player:
        raw = player.get("is_retired", player.get("retired", False))
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        return str(raw).strip().lower() in {"1", "true", "yes", "retired", "y"}

    # Explicit retired date in JSON implies retired.
    if player.get("retired_since"):
        return True

    if player_id in active_ids:
        return False
    if player_id in retired_ids:
        return True

    return False


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


def upsert_player(
    cur: psycopg.Cursor,
    player: Dict[str, Any],
    is_retired: bool,
    over_35: bool,
) -> None:
    player_id = str(player.get("id", "")).strip().lower()
    if not player_id:
        raise ValueError("Player is missing id")

    cur.execute(
        """
        insert into players(
          id, name, birth_date, nationality, height_cm, weight_kg, dominant_foot, is_retired, over_35, retired_since
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
          name = excluded.name,
          birth_date = excluded.birth_date,
          nationality = excluded.nationality,
          height_cm = excluded.height_cm,
          weight_kg = excluded.weight_kg,
          dominant_foot = excluded.dominant_foot,
          is_retired = excluded.is_retired,
          over_35 = excluded.over_35,
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
            is_retired,
            over_35,
            to_date(player.get("retired_since")),
        ),
    )


def upsert_player_season(
    cur: psycopg.Cursor,
    player_id: str,
    season: Dict[str, Any],
) -> int:
    team_id = normalize_team_id(season.get("team_id"))
    league_id = normalize_slug(season.get("league_id"), default="unknown")

    physical = season.get("physical_metrics") or {}
    tactical = season.get("tactical_data") or {}

    ensure_team(cur, team_id, UNKNOWN_TEAM_NAME if team_id == UNKNOWN_TEAM_ID else None)

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


def import_file(
    cur: psycopg.Cursor,
    file_path: Path,
    retired_ids: Set[str],
    active_ids: Set[str],
    over_age_threshold: int,
) -> Dict[str, int]:
    data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    player = data.get("player") or {}
    player_id = str(player.get("id", "")).strip().lower()
    seasons = [s for s in (data.get("seasons") or []) if isinstance(s, dict)]

    upsert_player(
        cur,
        player,
        is_retired=parse_retired(player, player_id, retired_ids=retired_ids, active_ids=active_ids),
        over_35=compute_over_age(player, seasons=seasons, threshold=over_age_threshold),
    )

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

    season_count = 0

    for season in seasons:
        expanded_rows = explode_season_rows(season)
        for season_row in expanded_rows:
            season_id = upsert_player_season(cur, player_id, season_row)
            replace_season_children(cur, season_id, season_row)
            season_count += 1

    return {"seasons": season_count}


def iter_player_files(players_dir: Path) -> Iterable[Path]:
    for file_path in sorted(players_dir.glob("*.json")):
        if file_path.name.endswith("_predictions.json") or file_path.name == STATUS_OVERRIDES_FILENAME:
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

    overrides = load_status_overrides(players_dir / STATUS_OVERRIDES_FILENAME)
    retired_ids = overrides["retired_ids"]
    active_ids = overrides["active_ids"]

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for file_path in iter_player_files(players_dir):
            try:
                with conn.cursor() as cur:
                    stats = import_file(
                        cur,
                        file_path,
                        retired_ids=retired_ids,
                        active_ids=active_ids,
                        over_age_threshold=args.over_age_threshold,
                    )
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
