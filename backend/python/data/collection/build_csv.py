"""Build the canonical tabular datasets from collected_players/.

Two CSVs (written to backend/python/data/):

1. collected_players_dataset.csv
   One row per (player, season, team, league) - the atomic sourced record.

2. collected_player_seasons.csv
   Model-ready per-(player, season) aggregation.

Aggregation rules (documented and tested in tests/):
  * A player-season's appearances = SUM of that player's domestic-league
    club-competition rows in that season; goals = SUM of their goals.
  * Because the collector never emits an all-clubs aggregate row (only atomic
    club-competition rows), summing cannot double-count.
  * A mid-season transfer therefore contributes each club's row to the sum, and
    n_clubs/clubs record the split.
  * is_partial for the season is TRUE if any contributing row is partial.
  * age is the season year minus birth year (constant across the season's rows).
  * stat_scope stays "domestic_league".
"""

import csv
import glob
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
COLLECTED = DATA / "collected_players"
RECORD_CSV = DATA / "collected_players_dataset.csv"
SEASON_CSV = DATA / "collected_player_seasons.csv"

RECORD_FIELDS = [
    "player_id", "wikidata_id", "name", "birth_date", "nationality",
    "primary_position", "position_group", "coarse_group", "career_status",
    "canonical_season", "season_source_label", "season_start_year",
    "season_end_year", "season_format",
    "age", "team_id", "team_name", "league_id", "league_name",
    "appearances", "goals", "stat_scope", "is_partial",
    "competition_level", "model_eligible", "exclusion_reason",
    "source_provider", "source_url", "source_retrieved_at", "source_revision",
]

SEASON_FIELDS = [
    "player_id", "name", "birth_date", "nationality", "primary_position",
    "position_group", "coarse_group", "career_status",
    "canonical_season", "season_start_year", "season_end_year", "season_format",
    "age", "appearances", "goals", "n_clubs", "n_competitions", "clubs", "leagues",
    "stat_scope", "is_partial", "model_eligible",
]


def load_players():
    return [json.loads(Path(f).read_text(encoding="utf-8"))
            for f in sorted(glob.glob(str(COLLECTED / "*.json")))]


def record_rows(players):
    for p in players:
        for s in p["seasons"]:
            src = (s.get("sources") or [{}])[0]
            yield {
                "player_id": p["player_id"], "wikidata_id": p.get("wikidata_id"),
                "name": p["name"], "birth_date": p.get("birth_date"),
                "nationality": p.get("nationality"),
                "primary_position": p.get("primary_position"),
                "position_group": p.get("position_group"),
                "coarse_group": p.get("coarse_group"),
                "career_status": p.get("career_status"),
                "canonical_season": s.get("canonical_season"),
                "season_source_label": s.get("season_source_label"),
                "season_start_year": s.get("season_start_year", s["season"]),
                "season_end_year": s.get("season_end_year"),
                "season_format": s.get("season_format"),
                "age": s.get("age"),
                "team_id": s["team_id"], "team_name": s["team_name"],
                "league_id": s["league_id"], "league_name": s["league_name"],
                "appearances": s["appearances"], "goals": s["goals"],
                "stat_scope": s["stat_scope"], "is_partial": s["is_partial"],
                "competition_level": s.get("competition_level"),
                "model_eligible": s.get("model_eligible"),
                "exclusion_reason": s.get("exclusion_reason"),
                "source_provider": src.get("provider"), "source_url": src.get("url"),
                "source_retrieved_at": src.get("retrieved_at"),
                "source_revision": src.get("revision"),
            }


def aggregate_seasons(players):
    """Per-(player, season) aggregation. See module docstring for the rules."""
    for p in players:
        # group by CANONICAL season (source label), never by start-year, so a
        # calendar "2005" and a split-year "2005-06" stay separate seasons while
        # a mid-season transfer (same "2015-16" label, two clubs) sums correctly.
        by_season = {}
        for s in p["seasons"]:
            canon = s.get("canonical_season") or str(s["season"])
            agg = by_season.setdefault(canon, {
                "appearances": 0, "goals": 0, "clubs": [], "leagues": [],
                "is_partial": False, "age": s.get("age"),
                "start_year": s.get("season_start_year", s["season"]),
                "end_year": s.get("season_end_year"),
                "format": s.get("season_format"), "eligible": True})
            agg["appearances"] += s["appearances"] or 0
            agg["goals"] += s["goals"] or 0
            if s["team_name"] not in agg["clubs"]:
                agg["clubs"].append(s["team_name"])
            if s["league_name"] and s["league_name"] not in agg["leagues"]:
                agg["leagues"].append(s["league_name"])
            agg["is_partial"] = agg["is_partial"] or bool(s["is_partial"])
            agg["eligible"] = agg["eligible"] and bool(s.get("model_eligible", True))
        for canon in sorted(by_season, key=lambda c: (by_season[c]["start_year"], c)):
            a = by_season[canon]
            yield {
                "player_id": p["player_id"], "name": p["name"],
                "birth_date": p.get("birth_date"), "nationality": p.get("nationality"),
                "primary_position": p.get("primary_position"),
                "position_group": p.get("position_group"), "coarse_group": p.get("coarse_group"),
                "career_status": p.get("career_status"),
                "canonical_season": canon, "season_start_year": a["start_year"],
                "season_end_year": a["end_year"], "season_format": a["format"], "age": a["age"],
                "appearances": a["appearances"], "goals": a["goals"],
                "n_clubs": len(a["clubs"]), "n_competitions": len(a["leagues"]),
                "clubs": "; ".join(a["clubs"]), "leagues": "; ".join(a["leagues"]),
                "stat_scope": "domestic_league", "is_partial": a["is_partial"],
                "model_eligible": a["eligible"],
            }


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        n = 0
        for r in rows:
            w.writerow(r); n += 1
    return n


def main():
    players = load_players()
    n_rec = write_csv(RECORD_CSV, RECORD_FIELDS, record_rows(players))
    n_seas = write_csv(SEASON_CSV, SEASON_FIELDS, aggregate_seasons(players))
    print(f"players={len(players)}")
    print(f"{RECORD_CSV.name}: {n_rec} rows (player-season-team-league)")
    print(f"{SEASON_CSV.name}: {n_seas} rows (player-season)")


if __name__ == "__main__":
    main()
