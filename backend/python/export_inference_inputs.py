"""Export per-player AGGREGATED inference inputs from collected_player_seasons.csv.

The production model is trained on aggregated CANONICAL seasons (one row per
player-season, transfers already summed). Inference therefore requires the same
aggregated shape (unique canonical seasons per player) -- NOT the atomic
collected_players/*.json (which has one row per season-team-competition).

Writes backend/python/data/inference_inputs/<player_id>.json.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEASONS_CSV = HERE / "data" / "collected_player_seasons.csv"
OUT = HERE / "data" / "inference_inputs"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(SEASONS_CSV, encoding="utf-8")))
    by = defaultdict(list)
    meta = {}
    for r in rows:
        by[r["player_id"]].append(r)
        meta[r["player_id"]] = r
    n = 0
    for pid, srows in by.items():
        m = meta[pid]
        srows.sort(key=lambda r: (int(r["season_start_year"]), r["canonical_season"]))
        player = {
            "player_id": pid, "primary_position": m.get("primary_position"),
            "position_group": m.get("position_group"), "coarse_group": m["coarse_group"],
            "career_status": m["career_status"], "birth_date": m["birth_date"],
            "stat_scope": "domestic_league",
            "seasons": [{
                "canonical_season": r["canonical_season"],
                "season_start_year": int(r["season_start_year"]),
                "season_end_year": int(r["season_end_year"]),
                "season_format": r["season_format"],
                "appearances": int(r["appearances"]), "goals": int(r["goals"]),
                "is_partial": r["is_partial"] == "True",
                "model_eligible": r["model_eligible"] == "True",
            } for r in srows],
        }
        (OUT / f"{pid}.json").write_text(json.dumps(player, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
        n += 1
    print(f"wrote {n} aggregated inference inputs to {OUT}")


if __name__ == "__main__":
    main()
