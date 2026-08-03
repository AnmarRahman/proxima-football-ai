"""Merge per-source blocks into one schema-compatible player JSON.

Rules honoured here:
  * Never invent values. A field is set only if a source provided it.
  * Preserve numeric 0 (sourced zero) as distinct from null (missing).
  * One row per (season, team, competition); no aggregate rows.
  * Deduplicate identical (season, team, competition) contributions.
  * Record which provider supplied each field, and flag conflicts when two
    providers disagree on the same field.
  * xG/xA come from a single provider only (enforced by the pilot config,
    which never registers two xG providers).
"""

import re
import unicodedata

from provenance import build_sources

# Canonical stat fields we expose in the schema; unsourced ones are set to null
# explicitly so "missing" is visible and distinct from a sourced 0.
CANONICAL_STAT_FIELDS = [
    "appearances", "starts", "goals", "assists", "minutes",
    "yellow_cards", "red_cards",
    "xG", "xA", "key_passes", "shots", "successful_dribbles",
    "duels_won", "tackles_per_game", "sprint_speed_kmh",
]

# Default merge priority when >1 provider offers the same field. Understat is
# intentionally absent (blocked under the respectful-access policy).
DEFAULT_PRIORITY = ["Wikipedia", "StatsBomb Open Data", "Understat"]


def slugify(value, default="unknown"):
    if not value:
        return default
    norm = unicodedata.normalize("NFKD", str(value))
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or default


def _pick(field, contributions, priority):
    """contributions: {provider: value}. Return (provider, value) by priority."""
    for provider in priority:
        if provider in contributions:
            return provider, contributions[provider]
    # fall back to any
    provider = next(iter(contributions))
    return provider, contributions[provider]


def merge_player(player_id, name, bio_blocks, stat_blocks,
                 priority=None, current_season_start=None):
    priority = priority or DEFAULT_PRIORITY
    bio_blocks = bio_blocks or []
    stat_blocks = stat_blocks or []

    # ---- player identity from bio (highest-priority bio wins per field) ----
    player = {
        "id": player_id, "name": name,
        "birth_date": None, "nationality": None, "dominant_foot": None,
        "height_cm": None, "weight_kg": None,
        "is_retired": False, "retired_since": None,
    }
    bio_field_provider = {}
    bio_sources = []
    for block in sorted(bio_blocks, key=lambda b: priority.index(b["provider"])
                        if b["provider"] in priority else 99):
        recorded = []
        for f in ("birth_date", "nationality", "dominant_foot", "height_cm",
                  "weight_kg", "position"):
            v = block["fields"].get(f)
            if v is not None and (f == "position" or player.get(f) is None):
                if f != "position":
                    player[f] = v
                bio_field_provider.setdefault(f, block["provider"])
                recorded.append(f)
        if recorded:
            bio_sources.append({"provider": block["provider"], "url": block["url"],
                                "retrieved_at": block["retrieved_at"],
                                "supports": recorded})
    bio_position = None
    for block in bio_blocks:
        if block["fields"].get("position"):
            bio_position = block["fields"]["position"]
            bio_position_provider = block["provider"]
            bio_position_meta = {"url": block["url"], "retrieved_at": block["retrieved_at"]}
            break

    # ---- group stat blocks by (season, team_id, league_id) ----
    groups = {}
    teams = {}
    for b in stat_blocks:
        season = b["season"]
        team_id = b.get("team_id") or slugify(b.get("team"))
        league_id = b.get("league_id") or slugify(b.get("competition"))
        teams[team_id] = b.get("team") or team_id
        key = (season, team_id, league_id)
        groups.setdefault(key, []).append(b)

    seasons_by_year = {}
    for (season, team_id, league_id) in groups:
        seasons_by_year.setdefault(season, set()).add(team_id)

    conflicts = []
    season_rows = []
    for (season, team_id, league_id), blocks in sorted(groups.items()):
        # collect per-field contributions
        contributions = {}          # field -> {provider: value}
        provider_meta = {}          # provider -> {url, retrieved_at}
        competition = None
        for b in blocks:
            provider_meta[b["provider"]] = {"url": b["url"], "retrieved_at": b["retrieved_at"]}
            competition = competition or b.get("competition")
            for f, v in b["fields"].items():
                contributions.setdefault(f, {})[b["provider"]] = v

        row = {
            "season": season, "team_id": team_id, "league_id": league_id,
            "is_partial": len(seasons_by_year.get(season, set())) > 1
                          or (current_season_start is not None and season >= current_season_start),
            "position": None,
            "injuries": [], "transfer_history": [], "national_team_stats": [],
        }
        # null-initialise canonical stat fields (explicit missing)
        for f in CANONICAL_STAT_FIELDS:
            row[f] = None

        field_provider = {}
        for field, contrib in contributions.items():
            provider, value = _pick(field, contrib, priority)
            if field in row or field in CANONICAL_STAT_FIELDS:
                row[field] = value
            else:
                row[field] = value
            field_provider[field] = provider
            # conflict if two providers gave different values
            distinct = {v for v in contrib.values()}
            if len(distinct) > 1:
                conflicts.append({
                    "season": season, "team_id": team_id, "league_id": league_id,
                    "field": field, "values": contrib,
                })

        # position: prefer a season-level source, else bio
        if row.get("position") is None and bio_position is not None:
            row["position"] = bio_position
            field_provider["position"] = bio_position_provider
            provider_meta.setdefault(bio_position_provider, bio_position_meta)

        if competition:
            row["_competition"] = competition

        row["sources"] = build_sources(field_provider, provider_meta)
        season_rows.append(row)

    data = {
        "player": player,
        "teams": [{"id": tid, "name": nm, "logo_url": None, "country": None}
                  for tid, nm in sorted(teams.items())],
        "seasons": season_rows,
    }
    if bio_sources:
        data["_bio_sources"] = bio_sources
    return data, conflicts
