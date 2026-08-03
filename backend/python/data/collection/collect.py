"""Collect and validate one player's domestic-league Tier-A career.

Flow: verified Wikidata identity -> canonical enwiki title -> Wikipedia career
table -> domestic-league season rows (one per season-team-competition) ->
normalization + validation. Youth/reserve rows are excluded; national-team
tables are naturally ignored (they lack "League Apps" columns). Nothing is
estimated; unknown values stay null. Split-season club rows are preserved and
no all-clubs aggregate row is created.
"""

import re
import sys
import unicodedata
from pathlib import Path

ACQ = Path(__file__).resolve().parents[1] / "acquisition"
sys.path.insert(0, str(ACQ))

from sources.wikipedia_source import WikipediaSource       # noqa: E402
from sources.base import SourceBlocked, SourceUnavailable  # noqa: E402

CURRENT_SEASON_START = 2026        # season >= this is treated as ongoing/partial
MAX_PLAUSIBLE_LEAGUE_APPS = 60     # per season-team-competition row
MIN_SENIOR_AGE = 15                # rows below this age are childhood/youth artifacts

RESERVE_RE = re.compile(
    r"(\b[bc]\b$)|(\bii+\b$)|(\b2\b$)|(\b3\b$)|castilla|"
    r"\w{3,}\s+atl[eèé]tico?\b|barcelona [bc]|"
    r"sporting cp b|bayern munich ii|jong |primavera|reserves?|youth|junior|"
    r"academy|\bu-?(1[0-9]|2[0-3])\b",
    re.IGNORECASE,
)
RESERVE_COMP_RE = re.compile(
    r"segunda división b|segunda b|tercera|serie c|serie d|regionalliga|"
    r"3\. divisjon|2\. divisjon|reserve|primavera|campeonato de españa",
    re.IGNORECASE,
)
AGG_RE = re.compile(r"\b(all comp\w*|total|totals|combined|aggregate|overall)\b", re.IGNORECASE)


def slugify(value, default="unknown"):
    if not value:
        return default
    norm = unicodedata.normalize("NFKD", str(value))
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or default


def is_reserve(club, competition):
    return bool(RESERVE_RE.search(str(club or "")) or RESERVE_COMP_RE.search(str(competition or "")))


def build_record(identity, roster_entry, meta):
    """Assemble a Tier-A record from a resolved identity + Wikipedia career meta.
    Returns (record, dropped_years, unknown_apps_rows)."""
    birth = identity.get("birth_date")
    birth_year = int(str(birth)[:4]) if birth else None
    provider_src = {"provider": "Wikipedia", "url": meta["url"],
                    "retrieved_at": meta["retrieved_at"], "revision": meta.get("revision"),
                    "supports": ["appearances", "goals"]}

    groups = {}              # (season, team_id, league_id) -> [rows]  (phases allowed)
    dropped_years = set()
    childhood_dropped = []
    all_years = set()
    unknown_apps = []

    for rec in meta["career"]:
        season = rec.get("season")
        club = rec.get("club")
        comp = rec.get("competition")
        if season is None or not club:
            continue
        all_years.add(season)
        if AGG_RE.search(str(club)) or AGG_RE.search(str(comp or "")):
            continue                       # never keep an aggregate row
        if is_reserve(club, comp):
            dropped_years.add(season)
            continue
        age = (season - birth_year) if birth_year else None
        if age is not None and age < MIN_SENIOR_AGE:
            childhood_dropped.append({"season": season, "club": club, "age": age})
            continue                       # childhood/youth artifact (age < 15)
        apps = rec.get("appearances")
        goals = rec.get("goals")
        if apps is None:
            unknown_apps.append({"season": season, "club": club})
            continue
        team_id = slugify(club)
        league_id = slugify(comp)
        canonical_season = rec.get("season_source_label") or str(season)
        row = {
            "season": season, "season_start_year": season,
            "canonical_season": canonical_season,
            "season_source_label": rec.get("season_source_label"),
            "season_format": rec.get("season_format"),
            "stat_scope": "domestic_league",
            "team_id": team_id, "team_name": club,
            "league_id": league_id, "league_name": comp,
            "appearances": int(apps), "goals": (int(goals) if goals is not None else None),
            "is_partial": season >= CURRENT_SEASON_START,
            "age": age,
            "sources": [dict(provider_src)],
        }
        # Canonical season = source label, so "2005" (calendar) and "2005-06"
        # (split-year) are DISTINCT seasons even though both start in 2005; only
        # identical labels for the same club+league are treated as phases.
        key = (canonical_season, team_id, league_id)
        bucket = groups.setdefault(key, [])
        # exact duplicate (duplicate Wikipedia table) -> skip; a different value
        # under the same key is a distinct competition phase (Apertura/Clausura).
        if any((r["appearances"], r["goals"], r["season_source_label"]) ==
               (row["appearances"], row["goals"], row["season_source_label"]) for r in bucket):
            continue
        bucket.append(row)

    # Within each (season,team,league) group, drop a full-season TOTAL row that
    # equals the sum of >=2 phase rows (never sum a phase with a total).
    seasons = []
    total_rows_dropped = 0
    for key, bucket in groups.items():
        keep = list(bucket)
        if len(bucket) >= 3:
            for i, cand in enumerate(bucket):
                others = [r for j, r in enumerate(bucket) if j != i]
                if len(others) >= 2 and cand["appearances"] == sum(r["appearances"] for r in others) \
                        and (cand["goals"] or 0) == sum((r["goals"] or 0) for r in others):
                    keep = others
                    total_rows_dropped += 1
                    break
        for idx, r in enumerate(keep):
            r["phase_index"] = idx if len(keep) > 1 else 0
            seasons.append(r)
    seasons = sorted(seasons, key=lambda r: (r["season_start_year"], r["canonical_season"],
                                             r["team_id"], r["phase_index"]))
    conflicts = []             # phases are preserved, not treated as conflicts
    kept_years = sorted({r["season"] for r in seasons})
    # true missing seasons: years inside the senior span with NO row at all
    missing = []
    if kept_years:
        for y in range(kept_years[0], kept_years[-1] + 1):
            if y not in all_years:
                missing.append(y)

    record = {
        "player_id": slugify(identity.get("enwiki_title") or roster_entry["name"]),
        "wikidata_id": identity.get("wikidata_id"),
        "name": identity.get("enwiki_title") or roster_entry["name"],
        "requested_name": roster_entry["name"],
        "birth_date": birth,
        "nationality": identity.get("nationality"),
        "primary_position": identity.get("position_label") or roster_entry["position_group"],
        "position_group": roster_entry["position_group"],
        "coarse_group": roster_entry["coarse_group"],
        "roster_section": roster_entry["section_title"],
        "stat_scope": "domestic_league",
        "scope_note": ("Wikipedia 'League' columns only (domestic league). Not mixed "
                       "with cup/continental/all-competition totals."),
        "identity_verification": {
            "wikidata_status": identity.get("status"),
            "wikidata_override": bool(identity.get("override")),
            "birth_date": birth, "nationality": identity.get("nationality"),
            "occupation_footballer": identity.get("occupation_footballer"),
            "position": identity.get("position_label"),
            "sitelinks": identity.get("sitelinks"),
            "expected_clubs": identity.get("expected_clubs"),
            "note": identity.get("note"),
        },
        "provenance": provider_src,
        "coverage": {
            "senior_seasons": len(kept_years),
            "season_team_league_rows": len(seasons),
            "reserve_or_youth_years_dropped": sorted(dropped_years),
            "childhood_rows_dropped": childhood_dropped,
            "unknown_apps_rows": unknown_apps,
            "total_rows_dropped": total_rows_dropped,
            "duplicate_conflicts": [list(k) for k in conflicts],
            "career_gaps": missing,      # genuine did-not-play gaps (not errors)
            "missing_middle_seasons": missing,
            "first_season": kept_years[0] if kept_years else None,
            "last_season": kept_years[-1] if kept_years else None,
            "partial_seasons": [r["season"] for r in seasons if r["is_partial"]],
            "tier": "A", "tier_b_c_available": False,
        },
        "seasons": seasons,
    }
    return record, dropped_years, unknown_apps


def validate_record(record, identity):
    """Return (errors, warnings). Any error -> quarantine."""
    errors, warnings = [], []
    cov = record["coverage"]

    if identity.get("status") != "ok":
        errors.append(f"identity status = {identity.get('status')} ({identity.get('note')})")
    if not record["birth_date"]:
        errors.append("missing birth_date (identity)")
    if not record["nationality"]:
        errors.append("missing nationality (identity)")
    if not record["seasons"]:
        errors.append("no domestic-league seasons parsed")
    if cov["duplicate_conflicts"]:
        errors.append(f"conflicting duplicate rows: {cov['duplicate_conflicts']}")
    # A year without a senior season is a did-not-play gap, NOT an error. It is
    # recorded and flagged for review; the player is still collected. We never
    # insert a synthetic zero row.
    if cov["career_gaps"]:
        warnings.append(f"career gap year(s) with no senior season: {cov['career_gaps']} "
                        "(did-not-play period; not zero-filled; review recommended)")
    if cov.get("childhood_rows_dropped"):
        warnings.append(f"{len(cov['childhood_rows_dropped'])} childhood row(s) (age<15) excluded")

    for r in record["seasons"]:
        tag = f"{r['season']}/{r['team_id']}/{r['league_id']}"
        if r["appearances"] is None:
            errors.append(f"{tag}: appearances null (Tier A incomplete)")
        if r["goals"] is None:
            errors.append(f"{tag}: goals null (Tier A incomplete)")
        if r["age"] is None:
            errors.append(f"{tag}: age null (no birth date)")
        if (r["appearances"] is not None and r["appearances"] < 0) or \
                (r["goals"] is not None and r["goals"] < 0):
            errors.append(f"{tag}: negative value")
        if not r["sources"]:
            errors.append(f"{tag}: no provenance")
        if r["appearances"] is not None and r["appearances"] > MAX_PLAUSIBLE_LEAGUE_APPS:
            warnings.append(f"{tag}: {r['appearances']} apps exceeds plausible league range")
        if r["goals"] is not None and r["appearances"] is not None and r["goals"] > r["appearances"]:
            warnings.append(f"{tag}: goals ({r['goals']}) > appearances ({r['appearances']})")

    # ordering sanity
    yrs = [r["season"] for r in record["seasons"]]
    if yrs != sorted(yrs):
        errors.append("season rows not in non-decreasing order")
    if cov["unknown_apps_rows"]:
        warnings.append(f"{len(cov['unknown_apps_rows'])} row(s) with unknown appearances dropped")
    if cov["partial_seasons"]:
        warnings.append(f"ongoing/partial season(s): {cov['partial_seasons']}")

    record["coverage"]["tier_a_complete"] = not errors
    record["coverage"]["provenance_complete"] = all(r["sources"] for r in record["seasons"])
    return errors, warnings


def collect_player(identity, roster_entry, wiki):
    """Resolve+parse+validate a single player. Returns (record, errors, warnings)."""
    title = identity.get("enwiki_title")
    if not title:
        rec = {"player_id": slugify(roster_entry["name"]), "name": roster_entry["name"],
               "requested_name": roster_entry["name"], "seasons": [],
               "identity_verification": {"wikidata_status": identity.get("status"),
                                         "note": identity.get("note")},
               "coverage": {"tier_a_complete": False}}
        return rec, [f"identity unresolved ({identity.get('status')}: {identity.get('note')})"], []
    try:
        meta = wiki.fetch_article_meta(title)
    except (SourceBlocked, SourceUnavailable) as exc:
        rec = {"player_id": slugify(title), "name": title, "requested_name": roster_entry["name"],
               "seasons": [], "coverage": {"tier_a_complete": False}}
        return rec, [f"wikipedia fetch failed: {exc}"], []
    record, _, _ = build_record(identity, roster_entry, meta)
    errors, warnings = validate_record(record, identity)
    return record, errors, warnings
