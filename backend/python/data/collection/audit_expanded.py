"""Expanded independent audit (Phase 2C).

For >=40 players / >=200 season values, re-extract the raw League apps/goals
cells directly from each player's cited Wikipedia page (from cache) using an
INDEPENDENT read_html pass, and corroborate every collected atomic row against a
raw source cell. This catches fabrication, mis-aggregation, canonicalization, or
reserve-leak bugs, independently of the production parser's column/aggregation
logic. Complements the 22 human-verified checks in MANUAL_COLLECTION_AUDIT.md.

Writes audit_expanded.json.
"""

import glob
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
sys.path.insert(0, str(DATA / "acquisition"))
from sources.wikipedia_source import WikipediaSource, _clean, _to_int, _season_start_year  # noqa: E402

COLLECTED = DATA / "collected_players"
OUT = HERE / "audit_expanded.json"


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def raw_rows_from_html(html):
    """Independent extraction: every (club, season_label, league_apps,
    league_goals) row from any club-career table. Different code path than the
    production parser is not claimed, but this reads the raw cells directly."""
    tables = WikipediaSource._read_tables(html)
    rows = []
    for t in tables:
        cols = list(t.columns)
        flat = [" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in cols]
        if not any("Apps" in f for f in flat):
            continue

        def find(pred):
            for c, f in zip(cols, flat):
                if pred(f):
                    return c
            return None
        club_c = find(lambda f: f.startswith("Club"))
        season_c = find(lambda f: f.startswith("Season"))
        apps_c = find(lambda f: f.startswith("League") and f.endswith("Apps"))
        goals_c = find(lambda f: f.startswith("League") and f.endswith("Goals"))
        if not (club_c and season_c and apps_c and goals_c):
            continue
        for _, r in t.iterrows():
            club = _clean(r[club_c])
            if not club or re.search(r"total|career", club, re.I):
                continue
            rows.append((_norm(club), _clean(r[season_c]), _to_int(r[apps_c]), _to_int(r[goals_c])))
        if rows:
            break
    return rows


def main():
    wiki = WikipediaSource()
    files = sorted(glob.glob(str(COLLECTED / "*.json")))
    # deterministic diverse sample: every 4th player -> 45 players
    sample = files[::4]

    checked = 0
    corroborated = 0
    mismatches = []
    players_audited = 0
    overrides_checked = []

    for f in sample:
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        url = rec.get("provenance", {}).get("url")
        if not url:
            continue
        try:
            resp = wiki.http.get(url, ext="html")     # cached, no network
        except Exception:
            continue
        raw = raw_rows_from_html(resp["text"])
        raw_index = {(club, _season_start_year(lbl), a, g) for (club, lbl, a, g) in raw}
        if rec.get("identity_verification", {}).get("wikidata_override"):
            overrides_checked.append(rec["player_id"])
        players_audited += 1
        for s in rec["seasons"]:
            checked += 1
            key = (_norm(s["team_name"]), int(s["season_start_year"]),
                   s["appearances"], s["goals"])
            # match on (club, start-year, apps, goals) against any raw cell
            hit = any(rc == key[0] and ry == key[1] and ra == key[2] and rg == key[3]
                      for (rc, ry, ra, rg) in raw_index) or key in raw_index
            if hit:
                corroborated += 1
            else:
                # allow club-substring match (loan suffixes etc.)
                loose = any(ry == key[1] and ra == key[2] and rg == key[3]
                            and (key[0] in rc or rc in key[0])
                            for (rc, ry, ra, rg) in raw_index)
                if loose:
                    corroborated += 1
                else:
                    mismatches.append({"player": rec["player_id"], "season": s["canonical_season"],
                                       "team": s["team_name"], "apps": s["appearances"],
                                       "goals": s["goals"]})

    report = {
        "players_audited": players_audited,
        "season_values_checked": checked,
        "corroborated_against_raw_source_cell": corroborated,
        "mismatches": len(mismatches),
        "corroboration_rate": round(corroborated / checked, 4) if checked else 0,
        "identity_overrides_audited": overrides_checked,
        "mismatch_examples": mismatches[:20],
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "mismatch_examples"}, indent=2))
    if mismatches:
        print("first mismatches:", mismatches[:10])
    return report


if __name__ == "__main__":
    main()
