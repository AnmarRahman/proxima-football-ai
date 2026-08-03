"""Export a deterministic Tier A training CSV from Postgres."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import psycopg


FIELDS = [
    "player_id", "name", "birth_date", "nationality", "primary_position",
    "position_group", "coarse_group", "career_status", "canonical_season",
    "season_start_year", "season_end_year", "season_format", "appearances",
    "goals", "stat_scope", "is_partial", "model_eligible",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.database_url.strip():
        raise SystemExit("Missing DATABASE_URL or --database-url")

    query = """
      select p.id, p.name, p.birth_date, p.nationality, p.primary_position,
             p.position_group, p.coarse_group, p.career_status,
             s.canonical_season, s.season_start_year, s.season_end_year,
             s.season_format, s.appearances, s.goals, p.stat_scope,
             s.is_partial, s.model_eligible
      from ml_players p
      join ml_player_seasons s on s.player_id = p.id
      order by p.id, s.season_start_year, s.canonical_season
    """
    with psycopg.connect(args.database_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FIELDS)
        for row in rows:
            writer.writerow([
                value.isoformat() if hasattr(value, "isoformat") else
                ("True" if value is True else "False" if value is False else value)
                for value in row
            ])
    print(f"Exported {len(rows)} Tier A season rows to {args.output}")


if __name__ == "__main__":
    main()
