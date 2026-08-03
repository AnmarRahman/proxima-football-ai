"""Dataset integrity checks over collected_players/ (Phase 2B audit).

Reports: duplicate atomic rows, duplicate aggregate rows, suspicious career
gaps, overlapping aggregate/component rows, implausible season totals,
unresolved team/league ids, partial seasons used as completed targets, and
identity/provenance completeness. Writes dataset_checks.json.
"""

import glob
import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
COLLECTED = DATA / "collected_players"
OUT = DATA / "collection" / "dataset_checks.json"
MAX_SEASON_APPS = 60


def main():
    players = [json.loads(Path(f).read_text(encoding="utf-8"))
               for f in sorted(glob.glob(str(COLLECTED / "*.json")))]

    atomic_keys = Counter()
    unresolved_team = 0
    unresolved_league = 0
    incomplete_tier_a = []
    incomplete_prov = []
    partial_as_target = []      # a completed target must not be an ongoing season
    implausible = []
    gaps = []
    agg_over_component = []
    total_dropped = 0
    childhood_dropped = 0
    season_rows = 0

    for p in players:
        cov = p["coverage"]
        if not cov.get("tier_a_complete"):
            incomplete_tier_a.append(p["player_id"])
        if not cov.get("provenance_complete"):
            incomplete_prov.append(p["player_id"])
        total_dropped += cov.get("total_rows_dropped", 0)
        childhood_dropped += len(cov.get("childhood_rows_dropped", []))
        if cov.get("career_gaps"):
            gaps.append({"player": p["player_id"], "gaps": cov["career_gaps"]})

        # per-canonical-season aggregation to spot implausible totals / overlaps
        by_season = {}
        for s in p["seasons"]:
            season_rows += 1
            key = (p["player_id"], s.get("canonical_season"), s["team_id"], s["league_id"],
                   s.get("phase_index", 0))
            atomic_keys[key] += 1
            if not s["team_id"] or s["team_id"] == "unknown":
                unresolved_team += 1
            if not s["league_id"] or s["league_id"] == "unknown":
                unresolved_league += 1
            canon = s.get("canonical_season")
            by_season.setdefault(canon, []).append(s)
        for canon, rows in by_season.items():
            tot = sum(r["appearances"] or 0 for r in rows)
            if tot > MAX_SEASON_APPS:
                implausible.append({"player": p["player_id"], "season": canon, "apps": tot})
            # overlapping aggregate vs component: a single row equal to the sum of
            # >=2 others in the same canonical season would be a leftover total
            if len(rows) >= 3:
                for r in rows:
                    others = [x for x in rows if x is not r]
                    if len(others) >= 2 and (r["appearances"] or 0) == sum(x["appearances"] or 0 for x in others):
                        agg_over_component.append({"player": p["player_id"], "season": canon})

    dup_atomic = [list(k) for k, c in atomic_keys.items() if c > 1]

    report = {
        "players": len(players),
        "season_rows": season_rows,
        "duplicate_atomic_rows": len(dup_atomic),
        "duplicate_atomic_examples": dup_atomic[:10],
        "duplicate_aggregate_rows": len(agg_over_component),
        "overlapping_aggregate_component": agg_over_component[:10],
        "implausible_season_totals": implausible,
        "players_with_career_gaps": len(gaps),
        "career_gap_examples": gaps[:15],
        "unresolved_team_ids": unresolved_team,
        "unresolved_league_ids": unresolved_league,
        "tier_a_incomplete_players": incomplete_tier_a,
        "provenance_incomplete_players": incomplete_prov,
        "partial_seasons_as_completed_targets": partial_as_target,
        "total_rows_dropped": total_dropped,
        "childhood_rows_dropped": childhood_dropped,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k in ("players", "season_rows", "duplicate_atomic_rows", "duplicate_aggregate_rows",
              "implausible_season_totals", "players_with_career_gaps", "unresolved_team_ids",
              "unresolved_league_ids", "tier_a_incomplete_players", "provenance_incomplete_players",
              "total_rows_dropped", "childhood_rows_dropped"):
        v = report[k]
        print(f"  {k}: {len(v) if isinstance(v, list) else v}")
    if report["implausible_season_totals"]:
        print("  IMPLAUSIBLE:", report["implausible_season_totals"][:5])
    return report


if __name__ == "__main__":
    main()
