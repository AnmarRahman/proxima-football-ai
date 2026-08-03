"""Validate Proxima player JSON files against the project schema, the dataset
quality gates in PLAYER_SCRAPE_ROSTER.md, and the importer/model contract.

Standard library only, so it runs under any Python 3.8+ without the backend
virtualenv.

    python validate_player.py path/to/player.json           # one file
    python validate_player.py path/to/players_dir            # every *.json
    python validate_player.py --strict path/to/player.json   # warnings fail too

Two tiers of finding:
  ERROR   - DEFAULT validation. The file is either importer/DB-breaking or
            violates a hard structural requirement of the collection contract
            (e.g. a season missing national_team_stats). Passing default
            validation means the file is STRUCTURALLY IMPORTABLE.
  warning - STRICT-only. Roster completeness / data-quality / provenance gate
            (missing sourced stat, a populated stat not covered by a source,
            unknown label, out-of-range value, ongoing season not marked
            partial). The file still imports, but is not eligible for the
            completed roster.

A player is COMPLETE (eligible for data/players) only when `--strict` reports
ZERO errors AND ZERO warnings. Never copy a file that fails --strict into
data/players/.

Exit code 0 means every checked file passed (default: no errors; strict: no
errors and no warnings). Exit code 1 means at least one file failed.

The rules encoded here are derived directly from:
  - backend/db/migrations/001_initial_schema.sql  (column types / constraints)
  - backend/python/import_players_to_db.py         (how JSON becomes rows)
  - backend/python/main.py                          (features the model reads)
  - PLAYER_SCRAPE_ROSTER.md                         (collection rules & gates)
Keep this file in sync with those if the schema changes.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# --- Contract mirrored from main.py / the SQL schema -----------------------

# Season-level numeric fields the model reads, with (low, high) sanity bounds.
# Mirrors NUMERIC_CLAMPS in main.py. Values outside the range still import but
# are clamped by the model, so they are flagged as warnings.
NUMERIC_CLAMPS = {
    "appearances": (0.0, 80.0),
    "goals": (0.0, 100.0),
    "assists": (0.0, 60.0),
    "minutes": (0.0, 7000.0),
    "rating": (4.0, 10.0),
    "xG": (0.0, 80.0),
    "xA": (0.0, 50.0),
    "key_passes": (0.0, 250.0),
    "successful_dribbles": (0.0, 400.0),
    "duels_won": (0.0, 600.0),
    "shots_per_game": (0.0, 10.0),
    "tackles_per_game": (0.0, 8.0),
    "fouls_drawn": (0.0, 200.0),
    "sprint_speed_kmh": (20.0, 45.0),
}

# Fields the DB stores as integers (import_players_to_db.to_int).
INTEGER_FIELDS = {
    "appearances", "goals", "assists", "minutes", "starts",
    "key_passes", "successful_dribbles", "duels_won", "fouls_drawn",
}

# Sourced statistics whose provenance must be declared. A value that is present
# (including a sourced 0) must be covered by at least one sources[] entry.
# `null` means "unknown" and is NOT treated as populated -- this is how the
# validator keeps null distinguishable from a sourced zero.
PROVENANCE_TRACKED = [
    "appearances", "goals", "assists", "minutes", "starts", "rating",
    "xG", "xA", "key_passes", "successful_dribbles", "duels_won",
    "shots_per_game", "tackles_per_game", "fouls_drawn",
]

# Qualitative vocabularies the model knows how to map (main.py). Labels outside
# these silently map to 0.0, so unknown labels are warnings.
PHYSICAL_LABELS = {
    "poor", "low", "medium", "moderate", "high", "very high", "very fast",
    "good", "improving", "developing", "normal", "fast", "excellent", "elite",
}
TACTICAL_LABELS = {
    "low", "limited", "below average", "medium", "moderate",
    "high", "very high", "world class",
}

MIN_PREFERRED_SEASON = 2000  # "Prefer seasons from 2000 onward"

# A season is "ongoing" if its starting year is the current football season.
_TODAY = date.today()
CURRENT_SEASON_START = _TODAY.year if _TODAY.month >= 7 else _TODAY.year - 1

# Youth records are not allowed (senior careers only).
YOUTH_RE = re.compile(
    r"\bu-?(1[0-9]|2[0-3])\b|\b(youth|junior|juniors|academy|juvenil|primavera)\b",
    re.IGNORECASE,
)
# An "all competitions"/total row must not sit alongside individual comps.
AGGREGATE_RE = re.compile(
    r"\b(all comp\w*|all competitions|total|totals|combined|aggregate|overall)\b",
    re.IGNORECASE,
)


def is_youth(text):
    return bool(text) and bool(YOUTH_RE.search(str(text)))


def looks_aggregate(text):
    return bool(text) and bool(AGGREGATE_RE.search(str(text)))


def classify_position(position):
    """Replicate main.position_features role detection, returning the set of
    role flags a position string activates. Empty set => the model cannot read
    a role from this label (it would fall through to a generic default)."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(position or "").strip().lower()).strip()
    tokens = set(normalized.split())
    roles = set()

    if "goalkeeper" in normalized or "keeper" in tokens or "gk" in tokens:
        roles.add("goalkeeper")
    if any(t in normalized for t in ("center back", "centre back")) or "cb" in tokens:
        roles.add("center_back")
    if any(t in normalized for t in ("left back", "right back", "full back", "wing back")) \
            or tokens & {"lb", "rb", "lwb", "rwb"}:
        roles.add("full_back")
    if any(t in normalized for t in ("defensive midfield", "holding midfield")) \
            or tokens & {"dm", "cdm"}:
        roles.add("defensive_midfield")
    if any(t in normalized for t in ("central midfield", "centre midfield")) or "cm" in tokens:
        roles.add("central_midfield")
    if any(t in normalized for t in ("attacking midfield", "number 10")) or tokens & {"am", "cam"}:
        roles.add("attacking_midfield")
    if "wing" in normalized or "winger" in normalized or tokens & {"lw", "rw", "lm", "rm"}:
        roles.add("winger")
    if any(t in normalized for t in ("striker", "forward", "false 9", "false nine",
                                     "second striker", "centre forward", "center forward")) \
            or tokens & {"st", "cf", "ss"}:
        roles.add("striker")

    if not roles:
        if "defender" in normalized:
            roles.add("center_back")
        elif "midfield" in normalized:
            roles.add("central_midfield")
    return roles


class Report:
    def __init__(self, path):
        self.path = path
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    @property
    def ok(self):
        return not self.errors


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_iso_date(value, label, rep):
    try:
        date.fromisoformat(str(value))
    except (ValueError, TypeError):
        rep.warn(f"{label}: '{value}' is not an ISO date (YYYY-MM-DD)")


def _source_coverage(container, fallback):
    """Return (declared_bool, covered_stat_set) from a `sources` array on
    `container`, falling back to `fallback` (e.g. the season object)."""
    sources = container.get("sources")
    if sources is None:
        sources = fallback.get("sources") if isinstance(fallback, dict) else None
    if not isinstance(sources, list) or not sources:
        return False, set()
    covered = set()
    for src in sources:
        if isinstance(src, dict):
            supports = src.get("supports")
            if isinstance(supports, list):
                covered |= {str(x) for x in supports}
    return True, covered


def validate(data, rep):
    if not isinstance(data, dict):
        rep.error("top-level JSON must be an object")
        return

    for key in ("player", "teams", "seasons"):
        if key not in data:
            rep.error(f"missing top-level key '{key}'")

    player = data.get("player") or {}
    teams = data.get("teams") or []
    seasons = data.get("seasons") or []

    # --- player -----------------------------------------------------------
    if not isinstance(player, dict):
        rep.error("'player' must be an object")
        player = {}
    player_id = str(player.get("id", "")).strip()
    if not player_id:
        rep.error("player.id is required (importer raises without it)")
    if not str(player.get("name", "")).strip():
        rep.error("player.name is required")
    if player.get("birth_date"):
        _check_iso_date(player["birth_date"], "player.birth_date", rep)
    else:
        rep.warn("player.birth_date missing -> model cannot compute age feature")
    for num_field in ("height_cm", "weight_kg"):
        v = player.get(num_field)
        if v is not None and not _is_number(v):
            rep.warn(f"player.{num_field} should be numeric or null, got {v!r}")
    if "is_retired" not in player and "retired" not in player and not player.get("retired_since"):
        rep.warn("player retired/active status not explicit in JSON "
                 "(gate: 'Current and retired status is explicit'); relies on "
                 "player_status_overrides.json")

    # --- teams ------------------------------------------------------------
    team_ids = set()
    team_names = {}
    if not isinstance(teams, list):
        rep.error("'teams' must be a list")
        teams = []
    for i, team in enumerate(teams):
        if not isinstance(team, dict):
            rep.error(f"teams[{i}] must be an object")
            continue
        tid = str(team.get("id", "")).strip().lower()
        if not tid:
            rep.error(f"teams[{i}].id is required")
            continue
        name = str(team.get("name", "")).strip()
        if not name:
            rep.warn(f"teams[{i}] ('{tid}') missing name")
        team_ids.add(tid)
        team_names[tid] = name

    # --- seasons ----------------------------------------------------------
    if not isinstance(seasons, list) or not seasons:
        rep.error("'seasons' must be a non-empty list")
        seasons = []

    # Season years appearing more than once => split (mid-season transfer) rows,
    # which must be flagged is_partial.
    year_counts = Counter(
        s.get("season") for s in seasons
        if isinstance(s, dict) and _is_number(s.get("season"))
    )

    seen_keys = set()  # (season, team_id, league_id) uniqueness
    for i, season in enumerate(seasons):
        tag = f"seasons[{i}]"
        if not isinstance(season, dict):
            rep.error(f"{tag} must be an object")
            continue

        # season year (season-level, both schemas)
        season_year = season.get("season")
        if season_year is None:
            rep.error(f"{tag}.season is required and must not be null")
        elif not _is_number(season_year):
            rep.error(f"{tag}.season must be numeric, got {season_year!r}")
        elif season_year < MIN_PREFERRED_SEASON:
            rep.warn(f"{tag}.season {season_year} is before {MIN_PREFERRED_SEASON} "
                     "(advanced-stat coverage is weaker)")

        # national_team_stats is a MANDATORY season-level array (use [] if none)
        if "national_team_stats" not in season:
            rep.error(f"{tag}.national_team_stats is required and must be present "
                      "(use [] when there are none)")
            national = []
        else:
            national = season.get("national_team_stats")
            if not isinstance(national, list):
                rep.error(f"{tag}.national_team_stats must be an array")
                national = []

        # national-team entries: no youth records; provenance for populated values
        for ni, nat in enumerate(national):
            ntag = f"{tag}.national_team_stats[{ni}]"
            if not isinstance(nat, dict):
                rep.error(f"{ntag} must be an object")
                continue
            comp = nat.get("competition") or ""
            if is_youth(comp) or is_youth(nat.get("team_id")):
                rep.warn(f"{ntag} '{comp}' looks like a YOUTH national-team record "
                         "(collection contract allows senior records only)")
            nat_pop = [f for f in ("appearances", "goals", "assists", "minutes")
                       if _is_number(nat.get(f))]
            if nat_pop:
                declared, _ = _source_coverage(nat, season)
                legacy = nat.get("source_url") or nat.get("source") or season.get("source_url")
                if not declared and not legacy:
                    rep.warn(f"{ntag} has populated stats {nat_pop} but no provenance "
                             "(add a sources[] entry or source_url)")

        # is_partial handling
        ip = season.get("is_partial")
        if ip is not None and not isinstance(ip, bool):
            rep.error(f"{tag}.is_partial must be a boolean")
        is_ongoing = _is_number(season_year) and season_year >= CURRENT_SEASON_START
        is_split = _is_number(season_year) and year_counts.get(season_year, 0) > 1
        if (is_ongoing or is_split) and ip is not True:
            why = "ongoing (current season)" if is_ongoing else \
                  "split across clubs in one season (mid-season transfer)"
            rep.warn(f"{tag}.is_partial should be true: season is {why}")

        # A season is either flat (stats on the season object) or nested
        # (season -> teams[] -> competitions[]). Normalize to (row_tag, tid, stats).
        rows = []
        nested_teams = season.get("teams")
        if isinstance(nested_teams, list) and nested_teams:
            for ti, team_entry in enumerate(nested_teams):
                if not isinstance(team_entry, dict):
                    rep.error(f"{tag}.teams[{ti}] must be an object")
                    continue
                tid = str(team_entry.get("team_id", "")).strip().lower()
                if not tid:
                    rep.error(f"{tag}.teams[{ti}].team_id is required")
                comps = team_entry.get("competitions")
                if not isinstance(comps, list) or not comps:
                    rep.error(f"{tag}.teams[{ti}].competitions must be a non-empty list")
                    continue
                for ci, comp in enumerate(comps):
                    if not isinstance(comp, dict):
                        rep.error(f"{tag}.teams[{ti}].competitions[{ci}] must be an object")
                        continue
                    rows.append((f"{tag}.teams[{ti}].competitions[{ci}]", tid, comp))
        else:
            rows.append((tag, str(season.get("team_id", "")).strip().lower(), season))

        by_tid = defaultdict(list)   # aggregate-row detection
        injury_sigs = defaultdict(list)  # duplicate-injury detection

        for row_tag, tid, stats in rows:
            comp_name = stats.get("competition") or ""
            league_id = stats.get("league_id") or comp_name
            by_tid[tid].append((row_tag, comp_name or stats.get("league_id") or ""))

            # youth club / competition -> not allowed (senior careers only)
            if is_youth(league_id) or is_youth(comp_name) or is_youth(team_names.get(tid)):
                rep.error(f"{row_tag}: youth club/competition record not allowed "
                          "(collection rule: senior club seasons only)")

            # Completeness gate (strict): sourced core values expected.
            if not tid:
                rep.warn(f"{row_tag}.team_id missing (gate requires a team per season)")
            for field in ("position", "appearances", "goals", "assists", "minutes"):
                if stats.get(field) is None:
                    rep.warn(f"{row_tag}.{field} missing (gate requires a sourced value; "
                             "leave null ONLY if genuinely unavailable)")

            # team_id must resolve to a declared team
            if tid and team_ids and tid not in team_ids:
                rep.error(f"{row_tag}.team_id '{tid}' is not declared in teams[]")

            # league_id needed for the uniqueness key
            if not stats.get("league_id"):
                rep.warn(f"{row_tag}.league_id missing -> importer derives it from "
                         "competition/'unknown', weakening the uniqueness key")

            # uniqueness of the DB unique constraint
            key = (season_year, tid, str(league_id or "unknown").strip().lower())
            if key in seen_keys:
                rep.error(f"{row_tag} duplicates (season, team_id, league_id)={key} "
                          "-> violates player_seasons unique constraint")
            seen_keys.add(key)

            # integer fields must be whole numbers
            for field in INTEGER_FIELDS:
                v = stats.get(field)
                if v is not None and _is_number(v) and float(v) != int(v):
                    rep.warn(f"{row_tag}.{field}={v} is not a whole number (stored as int)")

            # numeric ranges
            for field, (low, high) in NUMERIC_CLAMPS.items():
                v = stats.get(field)
                if v is None:
                    continue
                if not _is_number(v):
                    rep.warn(f"{row_tag}.{field} should be numeric or null, got {v!r}")
                elif not (low <= float(v) <= high):
                    rep.warn(f"{row_tag}.{field}={v} outside expected range [{low}, {high}] "
                             "(model will clamp)")

            # position readability by the model
            position = stats.get("position")
            if position is not None:
                roles = classify_position(position)
                if not roles:
                    rep.warn(f"{row_tag}.position '{position}' maps to no model role flag "
                             "-> row contributes no position signal")
                elif "goalkeeper" in roles:
                    rep.warn(f"{row_tag}.position '{position}' is a goalkeeper. GKs must be "
                             "trained separately and this outfield schema has no "
                             "saves/clean-sheets fields (see compatibility report).")

            # minutes vs appearances sanity
            apps = stats.get("appearances")
            minutes = stats.get("minutes")
            if _is_number(apps) and _is_number(minutes) and apps > 0 and minutes == 0:
                rep.warn(f"{row_tag}: {apps} appearances but 0 minutes "
                         "(is minutes an invented zero rather than a real value?)")

            # injuries structure + collect signatures for dedup
            injuries = stats.get("injuries")
            if injuries is not None:
                if not isinstance(injuries, list):
                    rep.error(f"{row_tag}.injuries must be a list")
                else:
                    for j, inj in enumerate(injuries):
                        if not isinstance(inj, dict):
                            rep.error(f"{row_tag}.injuries[{j}] must be an object")
                            continue
                        if inj.get("days_lost") is not None and not _is_number(inj["days_lost"]):
                            rep.warn(f"{row_tag}.injuries[{j}].days_lost should be numeric")
                        for dfield in ("start_date", "end_date"):
                            if inj.get(dfield):
                                _check_iso_date(inj[dfield], f"{row_tag}.injuries[{j}].{dfield}", rep)
                        sig = (str(inj.get("type", "")).strip().lower(),
                               str(inj.get("start_date", "")).strip())
                        if sig != ("", ""):
                            injury_sigs[sig].append(row_tag)

            # qualitative label vocabularies
            phys = stats.get("physical_metrics") or {}
            if isinstance(phys, dict):
                for lbl_field in ("acceleration", "stamina", "recovery_rate"):
                    val = phys.get(lbl_field)
                    if val and str(val).strip().lower() not in PHYSICAL_LABELS:
                        rep.warn(f"{row_tag}.physical_metrics.{lbl_field} '{val}' not in known "
                                 "vocabulary -> maps to 0.0")
            tac = stats.get("tactical_data") or {}
            if isinstance(tac, dict):
                for lbl_field in ("contribution_to_build_up", "defensive_transitions"):
                    val = tac.get(lbl_field)
                    if val and str(val).strip().lower() not in TACTICAL_LABELS:
                        rep.warn(f"{row_tag}.tactical_data.{lbl_field} '{val}' not in known "
                                 "vocabulary -> maps to 0.0")

            # provenance: every POPULATED sourced stat (incl. a sourced 0) must
            # be covered. null is not populated, keeping null != sourced-zero.
            declared, covered = _source_coverage(stats, season)
            legacy_url = stats.get("source_url") or stats.get("source") or season.get("source_url")
            legacy_ret = stats.get("retrieval_date") or season.get("retrieval_date")
            populated = [f for f in PROVENANCE_TRACKED if _is_number(stats.get(f))]

            if declared:
                # validate sources[] entry structure (season or row level)
                src_list = stats.get("sources") or season.get("sources") or []
                for si, src in enumerate(src_list):
                    if not isinstance(src, dict):
                        rep.error(f"{row_tag}.sources[{si}] must be an object")
                        continue
                    if not src.get("provider"):
                        rep.warn(f"{row_tag}.sources[{si}] missing 'provider'")
                    if not src.get("url"):
                        rep.warn(f"{row_tag}.sources[{si}] missing 'url'")
                    rt = src.get("retrieved_at") or src.get("retrieval_date")
                    if not rt:
                        rep.warn(f"{row_tag}.sources[{si}] missing 'retrieved_at'")
                    else:
                        _check_iso_date(rt, f"{row_tag}.sources[{si}].retrieved_at", rep)
                    if not isinstance(src.get("supports"), list):
                        rep.warn(f"{row_tag}.sources[{si}].supports must be a list of field names")
                for f in populated:
                    if f not in covered:
                        rep.warn(f"{row_tag}.{f} is populated but no sources[] entry lists it "
                                 "in 'supports' (every sourced statistic needs a source)")
            elif legacy_url:
                # backward-compatible coarse provenance
                if not legacy_ret:
                    rep.warn(f"{row_tag}: source_url present but retrieval_date missing")
                if populated:
                    rep.warn(f"{row_tag}: using legacy source_url; migrate to the sources[] "
                             "format so each statistic declares its source")
            elif populated:
                rep.warn(f"{row_tag}: populated stats {populated} but NO provenance "
                         "(add a sources[] entry; a value without a source is not allowed)")
            else:
                rep.warn(f"{row_tag}: no provenance recorded (sources[] or source_url)")

        # aggregate 'all competitions' row alongside individual competitions
        for tid_key, entries in by_tid.items():
            if len(entries) > 1:
                for row_tag2, nm in entries:
                    if looks_aggregate(nm):
                        rep.error(f"{row_tag2}: aggregate/'all competitions' row ('{nm}') present "
                                  "alongside individual competition rows for the same team "
                                  "(double-counting risk; keep only per-competition rows)")

        # duplicate injury across competition rows within a season
        for sig, tags in injury_sigs.items():
            if len(tags) > 1:
                rep.error(f"{tag}: injury {sig} duplicated across rows {tags} "
                          "-> days_lost would be double-counted; record each injury once")


# --------------------------------------------------------------------------
# Tier-based coverage reporting (Tier A core / B performance / C advanced).
# Self-contained so the validator stays dependency-free.
# --------------------------------------------------------------------------

TIER_A_PLAYER = ["birth_date", "nationality"]
TIER_A_ROW = ["position", "team_id", "competition_or_league", "appearances", "goals"]
TIER_B_FIELDS = ["starts", "minutes", "assists", "yellow_cards", "red_cards", "substitutions"]
TIER_C_FIELDS = ["xG", "xA", "key_passes", "shots", "successful_dribbles", "duels_won",
                 "tackles_per_game", "sprint_speed_kmh"]


def _cov_rows(season):
    nested = season.get("teams")
    if isinstance(nested, list) and nested:
        for ti, team in enumerate(nested):
            if not isinstance(team, dict):
                continue
            tid = str(team.get("team_id", "")).strip().lower()
            for ci, comp in enumerate(team.get("competitions") or []):
                if isinstance(comp, dict):
                    yield (f"seasons[?].teams[{ti}].competitions[{ci}]", tid, comp)
    else:
        yield (f"season {season.get('season')}",
               str(season.get("team_id", "")).strip().lower(), season)


def _cov_supports(stats, season):
    covered = set()
    srcs = stats.get("sources") or season.get("sources")
    if isinstance(srcs, list):
        for s in srcs:
            if isinstance(s, dict) and isinstance(s.get("supports"), list):
                covered |= {str(x) for x in s["supports"]}
    if not covered and (stats.get("source_url") or season.get("source_url")):
        covered.add("*legacy*")
    return covered


def coverage_summary(data):
    """Return Tier A/B/C + provenance coverage %, unsupported fields, conflicts,
    and missing-vs-zero inconsistencies for a player file."""
    player = data.get("player") or {}
    seasons = [s for s in (data.get("seasons") or []) if isinstance(s, dict)]

    player_a_present = sum(1 for f in TIER_A_PLAYER if player.get(f) is not None)
    a_p = a_t = b_p = b_t = c_p = c_t = prov_p = prov_t = 0
    rows = 0
    tier_a_complete_rows = 0
    per_season = []
    zero_without_prov = []       # missing-vs-zero inconsistencies
    seen_keys = {}               # (season,team,league) -> (apps,goals) for conflicts
    conflicts = []

    for season in seasons:
        syear = season.get("season")
        for label, tid, stats in _cov_rows(season):
            rows += 1
            league = stats.get("league_id") or stats.get("competition")
            row_a = {
                "position": stats.get("position"),
                "team_id": stats.get("team_id") or season.get("team_id"),
                "competition_or_league": league,
                "appearances": stats.get("appearances"),
                "goals": stats.get("goals"),
            }
            a_present = [k for k, v in row_a.items() if v is not None]
            a_p += len(a_present) + player_a_present
            a_t += len(row_a) + len(TIER_A_PLAYER)

            b_present = [f for f in TIER_B_FIELDS if stats.get(f) is not None]
            c_present = [f for f in TIER_C_FIELDS if stats.get(f) is not None]
            b_p += len(b_present); b_t += len(TIER_B_FIELDS)
            c_p += len(c_present); c_t += len(TIER_C_FIELDS)

            covered = _cov_supports(stats, season)
            populated = [f for f in (["appearances", "goals"] + TIER_B_FIELDS + TIER_C_FIELDS)
                         if stats.get(f) is not None]
            prov_ok = [f for f in populated if f in covered or "*legacy*" in covered]
            prov_p += len(prov_ok); prov_t += len(populated)

            national_ok = isinstance(season.get("national_team_stats"), list)
            row_complete = (len(a_present) == len(row_a) and national_ok
                            and player_a_present == len(TIER_A_PLAYER)
                            and len(prov_ok) == len(populated))
            if row_complete:
                tier_a_complete_rows += 1

            unsupported = ([k for k, v in row_a.items() if v is None]
                           + [f for f in TIER_B_FIELDS if stats.get(f) is None]
                           + [f for f in TIER_C_FIELDS if stats.get(f) is None])
            per_season.append({"row": label, "unsupported": unsupported})

            # missing-vs-zero: a sourced-looking 0 with no provenance may be a
            # disguised missing value (should be null instead).
            for f in (["appearances", "goals"] + TIER_B_FIELDS + TIER_C_FIELDS):
                v = stats.get(f)
                if _is_number(v) and v == 0 and f not in covered and "*legacy*" not in covered:
                    zero_without_prov.append(f"{label}.{f}=0 without provenance")

            # conflict: same (season,team,league) twice with differing apps/goals
            key = (syear, tid, str(league or "unknown").strip().lower())
            sig = (stats.get("appearances"), stats.get("goals"))
            if key in seen_keys and seen_keys[key] != sig:
                conflicts.append(f"{label}: conflicting values for {key}: "
                                 f"{seen_keys[key]} vs {sig}")
            seen_keys.setdefault(key, sig)

    def pct(n, d):
        return round(100.0 * n / d, 1) if d else 0.0

    return {
        "rows": rows,
        "tier_a_pct": pct(a_p, a_t),
        "tier_b_pct": pct(b_p, b_t),
        "tier_c_pct": pct(c_p, c_t),
        "provenance_pct": pct(prov_p, prov_t),
        "tier_a_complete": rows > 0 and tier_a_complete_rows == rows,
        "player_identity_complete": player_a_present == len(TIER_A_PLAYER),
        "per_season": per_season,
        "zero_without_provenance": zero_without_prov,
        "conflicts": conflicts,
    }


def validate_file(path, strict=False):
    rep = Report(path)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        rep.error(f"JSON does not parse: {exc}")
        return rep
    validate(data, rep)
    return rep


def iter_targets(target):
    p = Path(target)
    if p.is_dir():
        for f in sorted(p.glob("*.json")):
            # skip prediction dumps, status overrides, and meta/report files
            # (leading underscore marks a non-player file, e.g. _pilot_summary.json)
            if (f.name.endswith("_predictions.json")
                    or f.name == "player_status_overrides.json"
                    or f.name.startswith("_")):
                continue
            yield f
    else:
        yield p


def main():
    parser = argparse.ArgumentParser(description="Validate Proxima player JSON files.")
    parser.add_argument("target", help="A player JSON file or a directory of them.")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as failures too (roster-complete gate).")
    parser.add_argument("--coverage", action="store_true",
                        help="Print per-season Tier coverage detail.")
    args = parser.parse_args()

    any_fail = False
    checked = 0
    for path in iter_targets(args.target):
        checked += 1
        rep = validate_file(path, strict=args.strict)
        status = "PASS" if rep.ok and not (args.strict and rep.warnings) else "FAIL"
        if status == "FAIL":
            any_fail = True
        print(f"[{status}] {path.name}  ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
        for e in rep.errors:
            print(f"    ERROR   {e}")
        for w in rep.warnings:
            print(f"    warning {w}")

        # coverage report (never labels an incomplete-Tier-A file as complete)
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            cov = coverage_summary(data)
        except Exception:
            cov = None
        if cov:
            tier_a_label = "COMPLETE" if cov["tier_a_complete"] else "INCOMPLETE"
            print(f"    coverage TierA={cov['tier_a_pct']}% ({tier_a_label}) "
                  f"TierB={cov['tier_b_pct']}% TierC={cov['tier_c_pct']}% "
                  f"provenance={cov['provenance_pct']}%")
            for c in cov["conflicts"]:
                print(f"    conflict {c}")
            for z in cov["zero_without_provenance"]:
                print(f"    missing/zero {z}")
            if args.coverage:
                for ps in cov["per_season"]:
                    if ps["unsupported"]:
                        print(f"      {ps['row']} unsupported: {', '.join(ps['unsupported'])}")

    if checked == 0:
        print("No JSON files found to validate.")
        return 1
    print(f"\nChecked {checked} file(s). {'FAILURES present.' if any_fail else 'All passed.'}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
