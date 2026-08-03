"""Sourced career-status resolution.

Replaces the crude `active = last_year >= 2024` heuristic with a status derived
from Wikidata (P54 club memberships and their P582 end qualifiers; P570 date of
death) combined with the player's last sourced domestic-league season.

career_status in {active, retired, inactive, unknown}. Active and unknown
careers are censored (never labelled as retirements) downstream.
"""

STATUS_AS_OF = "2026-07-27"


def _membership_end_years(claims):
    """Return (has_open_membership, latest_end_year) from P54 statements."""
    has_open = False
    latest_end = None
    for st in claims.get("P54", []) or []:
        quals = st.get("qualifiers", {})
        ends = quals.get("P582")
        if not ends:
            has_open = True          # a club membership with no end date
            continue
        for e in ends:
            try:
                t = e["datavalue"]["value"]["time"]      # +YYYY-...
                y = int(t[1:5])
                latest_end = y if latest_end is None else max(latest_end, y)
            except (KeyError, ValueError, TypeError):
                pass
    return has_open, latest_end


def _death_year(claims):
    for st in claims.get("P570", []) or []:
        try:
            return int(st["mainsnak"]["datavalue"]["value"]["time"][1:5])
        except (KeyError, ValueError, TypeError):
            pass
    return None


def resolve_status(claims, qid, last_season_end_year, current_year=2026):
    """claims: Wikidata entity claims dict. Returns a status dict."""
    death = _death_year(claims)
    has_open, latest_end = _membership_end_years(claims)
    src = f"Wikidata:{qid} (P54 memberships, P570 death) + last sourced domestic-league season"
    out = {"career_status": "unknown", "status_as_of": STATUS_AS_OF,
           "status_source": src, "retired_since": None}

    if death is not None:
        out["career_status"] = "retired"
        out["retired_since"] = str(latest_end or death)
        out["status_note"] = "deceased"
        return out
    # active if Wikidata shows an open club membership AND the player still has a
    # recent sourced season, or the last sourced season reaches the current era.
    if (has_open and last_season_end_year and last_season_end_year >= current_year - 2) \
            or (last_season_end_year and last_season_end_year >= current_year - 1):
        out["career_status"] = "active"
        return out
    if last_season_end_year and last_season_end_year <= current_year - 3:
        out["career_status"] = "retired"
        out["retired_since"] = str(latest_end or last_season_end_year)
        return out
    # ambiguous recent stop (1-2 seasons ago) with no open membership
    out["career_status"] = "inactive" if latest_end else "unknown"
    if out["career_status"] == "inactive":
        out["retired_since"] = str(latest_end)
    return out
