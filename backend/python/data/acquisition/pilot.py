"""Free-source feasibility pilot for 3 players x 3 representative seasons.

Runs the policy-compliant adapters (Wikipedia + StatsBomb Open Data), probes the
blocked ones (Understat honest-access, soccerdata policy check), normalizes what
was obtained into schema-compatible JSON, scores Tier A/B/C coverage, and writes
everything to pilot_output/. It NEVER writes to data/players/ and never invents
values.

Run from this directory:  python pilot.py
"""

import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import coverage
import normalize
from sources.base import SourceBlocked, SourceUnavailable
from sources.wikipedia_source import WikipediaSource
from sources.understat_source import UnderstatSource
from sources.statsbomb_source import StatsBombSource
from sources.soccerdata_source import SoccerdataSource

OUT = HERE / "pilot_output"
OUT.mkdir(parents=True, exist_ok=True)
CURRENT_SEASON_START = 2026


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# player_id, name, wiki title, and 3 representative seasons.
# understat: competition name if that league is in Understat's 6, else None.
# statsbomb: (competition_name, season_name, team_name) if worth checking, else None.
PILOT = [
    {
        "id": "haaland", "name": "Erling Braut Haaland", "wiki": "Erling Haaland",
        "targets": [
            {"phase": "early", "season": 2018, "club_kw": "molde", "team_id": "molde",
             "team": "Molde FK", "competition": "Eliteserien", "league_id": "eliteserien-2018",
             "understat": None, "statsbomb": None},
            {"phase": "mid", "season": 2019, "club_kw": "salzburg", "team_id": "salzburg",
             "team": "Red Bull Salzburg", "competition": "Austrian Bundesliga",
             "league_id": "austria-bundesliga-2019", "understat": None, "statsbomb": None},
            {"phase": "recent", "season": 2022, "club_kw": "manchester city", "team_id": "mancity",
             "team": "Manchester City", "competition": "Premier League",
             "league_id": "premierleague-2022", "understat": "Premier League",
             "statsbomb": ("Premier League", "2022/2023", "Manchester City")},
        ],
    },
    {
        "id": "van-dijk", "name": "Virgil van Dijk", "wiki": "Virgil van Dijk",
        "targets": [
            {"phase": "early", "season": 2011, "club_kw": "groningen", "team_id": "groningen",
             "team": "FC Groningen", "competition": "Eredivisie", "league_id": "eredivisie-2011",
             "understat": None, "statsbomb": None},
            {"phase": "mid", "season": 2015, "club_kw": "southampton", "team_id": "southampton",
             "team": "Southampton", "competition": "Premier League",
             "league_id": "premierleague-2015", "understat": "Premier League",
             "statsbomb": ("Premier League", "2015/2016", "Southampton")},
            {"phase": "recent", "season": 2019, "club_kw": "liverpool", "team_id": "liverpool",
             "team": "Liverpool", "competition": "Premier League",
             "league_id": "premierleague-2019", "understat": "Premier League",
             "statsbomb": ("Premier League", "2019/2020", "Liverpool")},
        ],
    },
    {
        "id": "modric", "name": "Luka Modric", "wiki": "Luka Modrić",
        "targets": [
            {"phase": "early", "season": 2005, "club_kw": "dinamo", "team_id": "dinamo-zagreb",
             "team": "Dinamo Zagreb", "competition": "Prva HNL", "league_id": "prva-hnl-2005",
             "understat": None, "statsbomb": None},
            {"phase": "mid", "season": 2011, "club_kw": "tottenham", "team_id": "tottenham",
             "team": "Tottenham Hotspur", "competition": "Premier League",
             "league_id": "premierleague-2011", "understat": "Premier League",
             "statsbomb": ("Premier League", "2011/2012", "Tottenham Hotspur")},
            {"phase": "recent", "season": 2018, "club_kw": "real madrid", "team_id": "real-madrid",
             "team": "Real Madrid", "competition": "La Liga", "league_id": "la-liga-2018",
             "understat": "La Liga", "statsbomb": ("La Liga", "2018/2019", "Real Madrid")},
        ],
    },
]


def find_wiki_record(wiki_blocks, season, club_kw):
    for b in wiki_blocks:
        if b.season == season and club_kw in _norm(b.team):
            return b
    return None


def understat_season_label(season):
    return str(season)


def run():
    wiki = WikipediaSource()
    understat = UnderstatSource()
    statsbomb = StatsBombSource()
    soccerdata = SoccerdataSource()

    summary = {
        "generated_for": "free-source feasibility pilot",
        "current_season_start": CURRENT_SEASON_START,
        "soccerdata_evaluation": soccerdata.evaluate(),
        "players": [],
        "source_field_matrix": [],
    }

    for spec in PILOT:
        print(f"[pilot] {spec['id']} ...")
        player_report = {"player_id": spec["id"], "wiki_title": spec["wiki"],
                         "seasons": [], "errors": []}
        stat_blocks = []
        bio_blocks = []

        # --- Wikipedia (bio + career) ---
        try:
            bio, wiki_blocks = wiki.get_player(spec["wiki"])
            bio_blocks.append(bio.as_dict())
            player_report["wikipedia_access"] = "ok"
            player_report["bio_fields"] = sorted(bio.fields.keys())
        except SourceBlocked as exc:
            wiki_blocks = []
            player_report["wikipedia_access"] = f"blocked: {exc.status}"
            player_report["errors"].append(f"wikipedia blocked: {exc}")
        except SourceUnavailable as exc:
            wiki_blocks = []
            player_report["wikipedia_access"] = f"unavailable: {exc}"
            player_report["errors"].append(f"wikipedia unavailable: {exc}")

        for t in spec["targets"]:
            srec = {"phase": t["phase"], "season": t["season"], "team": t["team"],
                    "competition": t["competition"], "sources": {}}

            # Wikipedia record for this season
            wb = find_wiki_record(wiki_blocks, t["season"], t["club_kw"])
            if wb:
                block = type(wb)(  # rebuild with canonical target ids
                    provider=wb.provider, url=wb.url, retrieved_at=wb.retrieved_at,
                    season=t["season"], team=t["team"], team_id=t["team_id"],
                    competition=t["competition"], league_id=t["league_id"],
                    fields=dict(wb.fields))
                stat_blocks.append(block.as_dict())
                srec["sources"]["Wikipedia"] = {"fields": sorted(wb.fields.keys()),
                                                 "values": wb.fields}
            else:
                srec["sources"]["Wikipedia"] = {"fields": [], "note": "season/club not found in career table"}

            # Understat (honest probe)
            if t["understat"]:
                _, reason = understat.get_player_season(t["understat"],
                                                        understat_season_label(t["season"]),
                                                        spec["name"])
                srec["sources"]["Understat"] = {"fields": [], "status": "unavailable", "note": reason}
            else:
                srec["sources"]["Understat"] = {"fields": [], "status": "not_covered",
                                                "note": "league not among Understat's 6 leagues"}

            # StatsBomb (coverage + validation)
            if t["statsbomb"]:
                comp, season_name, team_name = t["statsbomb"]
                try:
                    v = statsbomb.validate_presence(comp, season_name, team_name, spec["name"])
                    srec["sources"]["StatsBomb Open Data"] = v
                except (SourceBlocked, SourceUnavailable) as exc:
                    srec["sources"]["StatsBomb Open Data"] = {"covered": None, "note": str(exc)}
            else:
                srec["sources"]["StatsBomb Open Data"] = {"covered": False,
                                                          "note": "competition not in open data"}

            player_report["seasons"].append(srec)

        # --- normalize what we obtained ---
        data, conflicts = normalize.merge_player(
            spec["id"], spec["name"], bio_blocks, stat_blocks,
            current_season_start=CURRENT_SEASON_START)
        cov = coverage.coverage_for_file(data)
        player_report["coverage"] = cov
        player_report["conflicts"] = conflicts

        out_path = OUT / f"{spec['id']}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        player_report["output_file"] = str(out_path.relative_to(HERE))
        summary["players"].append(player_report)

    (OUT / "_pilot_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # concise ASCII console summary
    print("\n==== PILOT SUMMARY ====")
    print("soccerdata:", "EXCLUDED -", summary["soccerdata_evaluation"]["reason"][:70], "...")
    for p in summary["players"]:
        c = p["coverage"]
        print(f"\n{p['player_id']}: TierA={c['tier_a_pct']}% TierB={c['tier_b_pct']}% "
              f"TierC={c['tier_c_pct']}% prov={c['provenance_pct']}% "
              f"TierA_complete={c['tier_a_complete']}")
        for s in p["seasons"]:
            wiki = "Y" if s["sources"]["Wikipedia"]["fields"] else "-"
            us = s["sources"]["Understat"].get("status", "-")
            sb = s["sources"]["StatsBomb Open Data"]
            sbtxt = f"covered={sb.get('covered')},found={sb.get('player_found')}"
            print(f"   {s['phase']:<6} {s['season']} {s['team'][:18]:<18} "
                  f"wiki={wiki} understat={us} statsbomb[{sbtxt}]")
    print(f"\nOutputs in {OUT.relative_to(HERE.parent)}")
    return summary


if __name__ == "__main__":
    run()
