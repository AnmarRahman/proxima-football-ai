"""Professional-season eligibility classification.

Raw sourced rows are preserved; this only adds flags so model targets and
continuation calculations can exclude clearly non-professional football:
amateur/non-league competitions, exhibition/testimonial rows, and isolated
post-retirement cameos (e.g. Paul Scholes' 2-game 9th-tier appearance for
Royton Town in 2018, after retiring in 2013).
"""

import re

# Clearly amateur / non-league / non-competitive competitions.
AMATEUR_LEAGUE_RE = re.compile(
    r"\bmfl\b|manchester football league|county league|sunday league|"
    r"non[- ]?league|\bamateur\b|exhibition|testimonial|veterans|"
    r"combined counties|north west counties|hellenic|spar mid-?wales|"
    r"\bstep [4-9]\b|regional league|district league|works league",
    re.IGNORECASE,
)

CAMEO_GAP_YEARS = 3       # a return after a gap this long...
CAMEO_MAX_APPS = 8        # ...with this few appearances is a cameo


def classify(league_name, appearances, prev_gap_years):
    """Return (competition_level, model_eligible, exclusion_reason)."""
    league_name = league_name or ""
    if AMATEUR_LEAGUE_RE.search(league_name):
        return "amateur", False, "amateur_or_non_league"
    if prev_gap_years is not None and prev_gap_years >= CAMEO_GAP_YEARS \
            and appearances is not None and appearances <= CAMEO_MAX_APPS:
        return "post_retirement_cameo", False, "post_retirement_cameo"
    return "professional_or_unknown", True, None
