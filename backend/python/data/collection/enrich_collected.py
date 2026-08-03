"""Enrich collected player records (Phase 2C) in place:

  * add season_end_year and keep season_format/label/canonical_season;
  * fill unknown league labels from reviewed league_overrides.json;
  * add per-season competition_level / model_eligible / exclusion_reason
    (amateur + post-retirement cameo exclusion);
  * add sourced career_status / status_as_of / status_source / retired_since
    from Wikidata (P54 memberships, P570 death) + last sourced season.

Raw sourced rows are preserved; only flags are added. Then rebuilds the CSVs.
"""

import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
ACQ = DATA / "acquisition"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(DATA.parent / "model_feasibility"))

from identity import WikidataIdentity                # noqa: E402
import career_status as CS                           # noqa: E402
import eligibility as EL                             # noqa: E402
from chronology import season_end_year, order_seasons  # noqa: E402

COLLECTED = DATA / "collected_players"
LEAGUE_OVERRIDES = json.loads((ACQ / "league_overrides.json").read_text(encoding="utf-8")).get("overrides", {})


def fetch_all_claims(qids):
    wd = WikidataIdentity()
    claims = {}
    uniq = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(uniq), 40):
        chunk = uniq[i:i + 40]
        ents = wd.entities(chunk)
        for q, e in ents.items():
            claims[q] = e.get("claims", {})
    return claims


def enrich_player(rec, claims_by_qid):
    seasons = rec.get("seasons") or []
    for s in seasons:
        s["season_end_year"] = season_end_year(
            s["season_start_year"], s.get("season_format"), s.get("season_source_label"))
        # reviewed league override for unknown labels (match loan variants too)
        if (not s.get("league_name")) or s.get("league_id") in (None, "", "unknown"):
            tov = LEAGUE_OVERRIDES.get(rec["player_id"], {})
            tid = s.get("team_id") or ""
            base_tid = re.sub(r"-(on-)?loan$", "", tid)
            ov = tov.get(tid) or tov.get(base_tid)
            if ov:
                s["league_name"] = ov["league_name"]
                s["league_id"] = ov["league_id"]
                s["league_source"] = "reviewed_override: " + ov["reason"]

    ordered = order_seasons(seasons)
    # per canonical season: gap from previous canonical season's end year
    prev_end = None
    gap_by_canon = {}
    for s in ordered:
        canon = s["canonical_season"]
        if canon not in gap_by_canon:
            gap_by_canon[canon] = None if prev_end is None else (int(s["season_start_year"]) - prev_end)
        prev_end = max(prev_end or 0, int(s["season_end_year"]))
    for s in seasons:
        gap = gap_by_canon.get(s["canonical_season"])
        level, eligible, reason = EL.classify(s.get("league_name"), s.get("appearances"), gap)
        s["competition_level"] = level
        s["model_eligible"] = eligible
        s["exclusion_reason"] = reason

    # sourced career status
    last_end = max((int(s["season_end_year"]) for s in seasons), default=None)
    claims = claims_by_qid.get(rec.get("wikidata_id"), {})
    status = CS.resolve_status(claims, rec.get("wikidata_id"), last_end)
    rec.update(status)

    cov = rec.setdefault("coverage", {})
    cov["model_eligible_seasons"] = sum(1 for s in seasons if s["model_eligible"])
    cov["ineligible_rows"] = [{"season": s["canonical_season"], "team": s["team_name"],
                               "reason": s["exclusion_reason"]}
                              for s in seasons if not s["model_eligible"]]
    return rec


def main():
    files = sorted(glob.glob(str(COLLECTED / "*.json")))
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in files]
    claims_by_qid = fetch_all_claims([r.get("wikidata_id") for r in recs])

    status_counts = {}
    elig_excluded = 0
    for f, rec in zip(files, recs):
        enrich_player(rec, claims_by_qid)
        status_counts[rec["career_status"]] = status_counts.get(rec["career_status"], 0) + 1
        elig_excluded += len(rec["coverage"]["ineligible_rows"])
        Path(f).write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"enriched {len(recs)} players")
    print("career_status:", status_counts)
    print(f"model-ineligible rows flagged: {elig_excluded}")
    # show the cameo exclusions explicitly
    for rec in recs:
        for x in rec["coverage"]["ineligible_rows"]:
            print(f"   excluded: {rec['player_id']:20} {x['season']:8} {x['team'][:22]:22} {x['reason']}")


if __name__ == "__main__":
    main()
