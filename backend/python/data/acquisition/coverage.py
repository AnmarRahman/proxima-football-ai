"""Tier-based coverage scoring for player-season data.

Tiers (from the pilot brief):
  Tier A - core required: identity, birth_date, nationality, position, season,
           team, competition, appearances, goals, national_team_stats array,
           provenance. A player-season may be used for model experimentation
           only when Tier A is complete and sourced.
  Tier B - performance: starts, minutes, assists, cards, substitutions.
  Tier C - advanced: xG, xA, key passes, shots, dribbles, duels, tackles,
           defensive stats, goalkeeper stats, physical/tactical fields.

`null` is treated as "missing" (not covered). A numeric 0 is treated as present
(a sourced zero). This module never invents values.
"""

# Player-level Tier A identity fields.
TIER_A_PLAYER = ["birth_date", "nationality"]
# Per-season/competition Tier A fields.
TIER_A_ROW = ["position", "team_id", "competition_or_league", "appearances", "goals"]

TIER_B = ["starts", "minutes", "assists", "yellow_cards", "red_cards", "substitutions"]

TIER_C = ["xG", "xA", "key_passes", "shots", "successful_dribbles", "duels_won",
          "tackles_per_game", "sprint_speed_kmh"]


def _present(value):
    """Present = key carried a real value. null == missing; 0 == present."""
    return value is not None


def _row_stats(season):
    """Yield (row_label, team_id, stats_dict) for flat or nested seasons."""
    nested = season.get("teams")
    if isinstance(nested, list) and nested:
        for ti, team in enumerate(nested):
            if not isinstance(team, dict):
                continue
            tid = str(team.get("team_id", "")).strip().lower()
            for ci, comp in enumerate(team.get("competitions") or []):
                if isinstance(comp, dict):
                    yield (f"s{season.get('season')}.t{ti}.c{ci}", tid, comp)
    else:
        yield (f"s{season.get('season')}", str(season.get("team_id", "")).strip().lower(), season)


def _provenance_supports(stats, season):
    """Return the set of fields declared as sourced via sources[] (row or season)."""
    covered = set()
    srcs = stats.get("sources")
    if srcs is None:
        srcs = season.get("sources")
    if isinstance(srcs, list):
        for s in srcs:
            if isinstance(s, dict) and isinstance(s.get("supports"), list):
                covered |= {str(x) for x in s["supports"]}
    # legacy coarse provenance still counts as "some provenance present"
    if not covered and (stats.get("source_url") or season.get("source_url")):
        covered.add("*legacy*")
    return covered


def score_row(stats, season, player):
    """Coverage detail for one competition row."""
    league_val = stats.get("league_id") or stats.get("competition")
    row_values = {
        "position": stats.get("position"),
        "team_id": stats.get("team_id") or season.get("team_id"),
        "competition_or_league": league_val,
        "appearances": stats.get("appearances"),
        "goals": stats.get("goals"),
    }
    tier_a_row = {k: _present(v) for k, v in row_values.items()}
    tier_b = {k: _present(stats.get(k)) for k in TIER_B}
    tier_c = {k: _present(stats.get(k)) for k in TIER_C}

    covered = _provenance_supports(stats, season)
    # populated statistics (Tier A stats + B + C) that must have provenance
    populated = [f for f in (["appearances", "goals"] + TIER_B + TIER_C)
                 if _present(stats.get(f))]
    prov_ok = [f for f in populated if f in covered or "*legacy*" in covered]

    national_present = isinstance(season.get("national_team_stats"), list)

    unsupported = [k for k, ok in {**tier_a_row, **tier_b, **tier_c}.items() if not ok]

    return {
        "tier_a_row": tier_a_row,
        "tier_b": tier_b,
        "tier_c": tier_c,
        "national_team_stats_present": national_present,
        "populated_stats": populated,
        "provenance_covered": prov_ok,
        "unsupported_fields": unsupported,
    }


def coverage_for_file(data):
    """Aggregate Tier A/B/C + provenance coverage for a whole player file."""
    player = data.get("player") or {}
    seasons = [s for s in (data.get("seasons") or []) if isinstance(s, dict)]

    player_a_present = sum(1 for f in TIER_A_PLAYER if _present(player.get(f)))
    player_a_total = len(TIER_A_PLAYER)

    a_present = a_total = 0
    b_present = b_total = 0
    c_present = c_total = 0
    prov_present = prov_total = 0
    per_season = []
    tier_a_complete_rows = 0
    total_rows = 0

    for season in seasons:
        for label, tid, stats in _row_stats(season):
            total_rows += 1
            det = score_row(stats, season, player)

            row_a_vals = list(det["tier_a_row"].values())
            a_present += sum(1 for v in row_a_vals if v)
            a_total += len(row_a_vals)
            b_present += sum(1 for v in det["tier_b"].values() if v)
            b_total += len(det["tier_b"])
            c_present += sum(1 for v in det["tier_c"].values() if v)
            c_total += len(det["tier_c"])
            prov_present += len(det["provenance_covered"])
            prov_total += len(det["populated_stats"])

            # A row is Tier-A-complete when all row-A fields present, the season
            # carries a national_team_stats array, player identity present, and
            # every populated stat has provenance.
            row_a_complete = (all(row_a_vals)
                              and det["national_team_stats_present"]
                              and player_a_present == player_a_total
                              and len(det["provenance_covered"]) == len(det["populated_stats"]))
            if row_a_complete:
                tier_a_complete_rows += 1

            per_season.append({
                "row": label, "team_id": tid,
                "tier_a_complete": row_a_complete,
                "unsupported_fields": det["unsupported_fields"],
            })

    def pct(n, d):
        return round(100.0 * n / d, 1) if d else 0.0

    # fold player identity into Tier A percentage
    a_present_total = a_present + player_a_present * max(1, total_rows)
    a_total_total = a_total + player_a_total * max(1, total_rows)

    return {
        "rows": total_rows,
        "tier_a_pct": pct(a_present_total, a_total_total),
        "tier_b_pct": pct(b_present, b_total),
        "tier_c_pct": pct(c_present, c_total),
        "provenance_pct": pct(prov_present, prov_total),
        "tier_a_complete_rows": tier_a_complete_rows,
        "tier_a_complete": total_rows > 0 and tier_a_complete_rows == total_rows,
        "player_identity_complete": player_a_present == player_a_total,
        "per_season": per_season,
    }
