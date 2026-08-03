"""Understat adapter (xG/xA) - honest-access probe only.

Understat is the project's chosen single xG/xA model. However, honest requests
(plain GET with an identifying User-Agent) to the league pages no longer return
the inline `playersData`/`teamsData` JSON they used to; the tables are now loaded
via an undocumented AJAX path, and the maintained scraper (`soccerdata`) only
succeeds by using a TLS-fingerprint impersonation library (`tls-client`), which
this project's rules forbid.

This adapter therefore performs one honest probe and, if the structured data is
not present, records the source as UNAVAILABLE (blocked-by-design) rather than
attempting any circumvention. It never estimates values.
"""

import re

from .base import CachingHTTPClient, SourceBlocked, SourceUnavailable

LEAGUE_PAGE = "https://understat.com/league/{code}/{season}"

# our competition -> understat league code (only these 6 leagues exist)
LEAGUE_CODES = {
    "premier league": "EPL", "la liga": "La_liga", "bundesliga": "Bundesliga",
    "serie a": "Serie_A", "ligue 1": "Ligue_1", "russian premier league": "RFPL",
}


class UnderstatSource:
    provider = "Understat"

    def __init__(self, cache_dir=None, min_delay=3.0):
        kw = {"min_delay": min_delay}
        if cache_dir:
            kw["cache_dir"] = cache_dir
        self.http = CachingHTTPClient("understat", **kw)

    def league_code(self, competition):
        return LEAGUE_CODES.get(str(competition or "").strip().lower())

    def probe_league(self, code, season):
        """Return (available, detail). Honest GET; detect inline data."""
        url = LEAGUE_PAGE.format(code=code, season=season)
        try:
            resp = self.http.get(url, ext="html")
        except SourceBlocked as exc:
            return False, f"blocked: HTTP {exc.status}"
        except SourceUnavailable as exc:
            return False, f"unavailable: {exc}"
        has_inline = bool(re.search(r"(playersData|teamsData)\s*=\s*JSON\.parse", resp["text"]))
        if has_inline:
            return True, "inline playersData present"
        return False, ("no inline data via honest request; structured access "
                       "requires TLS-fingerprint impersonation (disallowed)")

    def get_player_season(self, competition, season, player_name):
        """Honest attempt. Returns [] and a recorded reason; never invents."""
        code = self.league_code(competition)
        if not code:
            return [], f"league '{competition}' not covered by Understat"
        available, detail = self.probe_league(code, season)
        if not available:
            return [], detail
        # If Understat ever restores inline data, parsing would go here.
        return [], "inline data present but structured parsing not enabled in pilot"
