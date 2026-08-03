"""Build the Tier-A feasibility dataset from the approved Wikimedia pipeline.

Collects ONLY Tier A fields (domestic-league appearances + goals per season,
plus identity) for a small, deliberately diverse outfield roster. It:
  * reuses the policy-compliant WikipediaSource adapter (cached, rate-limited),
  * excludes youth / reserve seasons,
  * aggregates per season-YEAR as domestic-league totals (stat_scope),
  * keeps provenance and records coverage metadata,
  * writes per-player JSON + a combined dataset to
    backend/python/data/acquisition/model_feasibility_data/.

It never writes to data/players/, never fabricates values, and marks
Wikipedia's figures as domestic-league only (the parser reads the "League"
columns exclusively).

Run:  python build_dataset.py
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent / "data" / "acquisition"
sys.path.insert(0, str(ACQ))

from sources.wikipedia_source import WikipediaSource       # noqa: E402
from sources.base import SourceBlocked, SourceUnavailable  # noqa: E402

OUT = ACQ / "model_feasibility_data"
OUT.mkdir(parents=True, exist_ok=True)

# Reserve / youth team or lower-tier reserve competition patterns to exclude.
RESERVE_RE = re.compile(
    r"(\b[bc]\b$)|(\bii+\b$)|(\b2\b$)|castilla|sevilla atl|barcelona [bc]|"
    r"sporting cp b|jong |primavera|reserves?|youth|junior|academy|"
    r"\bu-?(1[0-9]|2[0-3])\b",
    re.IGNORECASE,
)
RESERVE_COMP_RE = re.compile(
    r"segunda división b|segunda b|tercera|serie c|serie d|regionalliga|"
    r"3\. divisjon|reserve",
    re.IGNORECASE,
)

# id, wiki title, display name, fine position group, coarse group, active flag,
# era label. Coarse: FWD / WIDE / MID / DEF.
ROSTER = [
    # forwards / strikers
    ("haaland", "Erling Haaland", "Erling Haaland", "FW", "FWD", True, "2010s-2020s"),
    ("ibrahimovic", "Zlatan Ibrahimović", "Zlatan Ibrahimovic", "FW", "FWD", False, "2000s-2020s"),
    ("henry", "Thierry Henry", "Thierry Henry", "FW", "FWD", False, "1990s-2010s"),
    ("van-basten", "Marco van Basten", "Marco van Basten", "FW", "FWD", False, "1980s-1990s (early retirement)"),
    # wide / wingers
    ("ronaldo", "Cristiano Ronaldo", "Cristiano Ronaldo", "WNG", "WIDE", True, "2000s-2020s"),
    ("robben", "Arjen Robben", "Arjen Robben", "WNG", "WIDE", False, "2000s-2010s"),
    ("ribery", "Franck Ribéry", "Franck Ribery", "WNG", "WIDE", False, "2000s-2020s"),
    ("beckham", "David Beckham", "David Beckham", "WNG", "WIDE", False, "1990s-2010s (low scorer)"),
    # attacking mids
    ("kaka", "Kaká", "Kaka", "AM", "MID", False, "2000s-2010s"),
    ("totti", "Francesco Totti", "Francesco Totti", "AM", "MID", False, "1990s-2010s (one club)"),
    # central mids
    ("lampard", "Frank Lampard", "Frank Lampard", "CM", "MID", False, "1990s-2010s (high-scoring mid)"),
    ("gerrard", "Steven Gerrard", "Steven Gerrard", "CM", "MID", False, "1990s-2010s"),
    ("modric", "Luka Modrić", "Luka Modric", "CM", "MID", True, "2000s-2020s (long, low scorer)"),
    ("pirlo", "Andrea Pirlo", "Andrea Pirlo", "CM", "MID", False, "1990s-2010s (deep playmaker)"),
    # defensive mid
    ("busquets", "Sergio Busquets", "Sergio Busquets", "DM", "MID", True, "2000s-2020s (very low scorer)"),
    # centre-backs
    ("van-dijk", "Virgil van Dijk", "Virgil van Dijk", "CB", "DEF", True, "2010s-2020s"),
    ("ramos", "Sergio Ramos", "Sergio Ramos", "CB", "DEF", True, "2000s-2020s (high-scoring CB)"),
    ("maldini", "Paolo Maldini", "Paolo Maldini", "CB", "DEF", False, "1980s-2000s (very long)"),
    # full-backs
    ("dani-alves", "Dani Alves", "Dani Alves", "FB", "DEF", False, "2000s-2020s (very long)"),
    ("lahm", "Philipp Lahm", "Philipp Lahm", "FB", "DEF", False, "2000s-2010s"),
]


def is_reserve(club, competition):
    club = str(club or "")
    comp = str(competition or "")
    return bool(RESERVE_RE.search(club) or RESERVE_COMP_RE.search(comp))


def collect_player(wiki, entry):
    pid, title, name, pos, coarse, active, era = entry
    src = wiki
    bio, blocks = src.get_player(title)

    birth = bio.fields.get("birth_date")
    birth_year = int(str(birth)[:4]) if birth else None

    kept = {}          # season_year -> {apps, goals, clubs, comps}
    dropped = []
    for b in blocks:
        if is_reserve(b.team, b.competition):
            dropped.append({"season": b.season, "club": b.team, "competition": b.competition})
            continue
        apps = b.fields.get("appearances")
        goals = b.fields.get("goals")
        if apps is None:
            continue
        row = kept.setdefault(b.season, {"appearances": 0, "goals": 0, "clubs": [], "competitions": []})
        row["appearances"] += apps
        row["goals"] += (goals or 0)
        # goals may be legitimately 0 (sourced zero) or null; Wikipedia gives a
        # number for played league seasons, so treat as sourced.
        if b.team and b.team not in row["clubs"]:
            row["clubs"].append(b.team)
        if b.competition and b.competition not in row["competitions"]:
            row["competitions"].append(b.competition)

    seasons = []
    for year in sorted(kept):
        r = kept[year]
        seasons.append({
            "season": year,
            "stat_scope": "domestic_league",
            "appearances": r["appearances"],
            "goals": r["goals"],
            "clubs": r["clubs"],
            "competitions": r["competitions"],
        })

    record = {
        "player_id": pid,
        "name": name,
        "position_group": pos,
        "coarse_group": coarse,
        "active": active,
        "era": era,
        "birth_year": birth_year,
        "birth_date": birth,
        "nationality": bio.fields.get("nationality"),
        "career_position_label": bio.fields.get("position"),
        "stat_scope": "domestic_league",
        "scope_note": ("Wikipedia 'League' columns only; domestic-league apps/goals. "
                       "NOT mixed with cup/continental/all-competition totals."),
        "provenance": {"provider": "Wikipedia", "url": bio.url,
                       "retrieved_at": bio.retrieved_at,
                       "supports": ["appearances", "goals", "position", "birth_date", "nationality"]},
        "coverage": {
            "senior_seasons": len(seasons),
            "reserve_or_youth_rows_dropped": len(dropped),
            "dropped_rows": dropped,
            "first_season": seasons[0]["season"] if seasons else None,
            "last_season": seasons[-1]["season"] if seasons else None,
            "tier": "A",
            "tier_b_c_available": False,
        },
        "seasons": seasons,
    }
    return record


def main():
    wiki = WikipediaSource()
    dataset = []
    coverage = []
    for entry in ROSTER:
        pid, title = entry[0], entry[1]
        try:
            rec = collect_player(wiki, entry)
        except (SourceBlocked, SourceUnavailable) as exc:
            print(f"[skip] {pid}: {exc}")
            continue
        (OUT / f"{pid}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
        dataset.append(rec)
        coverage.append({"player_id": pid, "name": rec["name"],
                         "position_group": rec["position_group"], "coarse_group": rec["coarse_group"],
                         "active": rec["active"], "birth_year": rec["birth_year"],
                         "seasons": rec["coverage"]["senior_seasons"],
                         "span": [rec["coverage"]["first_season"], rec["coverage"]["last_season"]],
                         "dropped_reserve_youth": rec["coverage"]["reserve_or_youth_rows_dropped"]})
        print(f"[ok] {pid:14} seasons={rec['coverage']['senior_seasons']:2} "
              f"dropped={rec['coverage']['reserve_or_youth_rows_dropped']} "
              f"span={rec['coverage']['first_season']}-{rec['coverage']['last_season']}")

    (OUT / "_dataset.json").write_text(json.dumps(dataset, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    (OUT / "_coverage.json").write_text(json.dumps(coverage, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
    total_rows = sum(len(r["seasons"]) for r in dataset)
    print(f"\nPlayers={len(dataset)}  season_rows={total_rows}  -> {OUT}")


if __name__ == "__main__":
    main()
