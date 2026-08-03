"""StatsBomb Open Data adapter - supplemental coverage + validation only.

Honest access: the data lives in a public GitHub repo (raw.githubusercontent),
which serves plain JSON without any anti-bot control. Per the brief, StatsBomb
Open Data is used ONLY for the competitions/seasons actually in the repo, as
supplemental event data and validation - never as full-career coverage. To stay
respectful we do not download whole seasons of events; we check coverage and
validate a player's presence from a single lineup file.
"""

import json
import unicodedata

from .base import CachingHTTPClient, SourceBlocked, SourceUnavailable

RAW = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


class StatsBombSource:
    provider = "StatsBomb Open Data"
    license = "CC BY-NC 4.0 (attribution, non-commercial)"

    def __init__(self, cache_dir=None, min_delay=1.5):
        kw = {"min_delay": min_delay}
        if cache_dir:
            kw["cache_dir"] = cache_dir
        self.http = CachingHTTPClient("statsbomb", **kw)
        self._competitions = None

    def competitions(self):
        if self._competitions is None:
            resp = self.http.get(f"{RAW}/competitions.json", ext="json")
            self._competitions = json.loads(resp["text"])
        return self._competitions

    def resolve(self, competition_name, season_name):
        """Return (competition_id, season_id) or None if not in open data."""
        for c in self.competitions():
            if (_norm(c["competition_name"]) == _norm(competition_name)
                    and _norm(c["season_name"]) == _norm(season_name)):
                return c["competition_id"], c["season_id"]
        return None

    def validate_presence(self, competition_name, season_name, team_name, player_name):
        """Coverage + single-match validation. Returns a dict; never season totals."""
        result = {
            "provider": self.provider, "competition": competition_name,
            "season": season_name, "covered": False, "matches_available": 0,
            "player_found": False, "sample_match_id": None,
            "sample_minutes": None, "note": "",
        }
        ids = self.resolve(competition_name, season_name)
        if not ids:
            result["note"] = "competition/season not in StatsBomb open data"
            return result
        comp_id, season_id = ids
        result["covered"] = True
        try:
            matches = json.loads(self.http.get(f"{RAW}/matches/{comp_id}/{season_id}.json",
                                               ext="json")["text"])
        except (SourceBlocked, SourceUnavailable) as exc:
            result["note"] = f"matches list unavailable: {exc}"
            return result

        team_matches = [m for m in matches
                        if _norm(team_name) in (_norm(m["home_team"]["home_team_name"]),
                                                _norm(m["away_team"]["away_team_name"]))]
        result["matches_available"] = len(team_matches)
        if not team_matches:
            result["note"] = "team not found in this competition-season"
            return result

        # inspect ONE lineup only (respectful; validation, not aggregation)
        match_id = team_matches[0]["match_id"]
        result["sample_match_id"] = match_id
        try:
            lineups = json.loads(self.http.get(f"{RAW}/lineups/{match_id}.json",
                                               ext="json")["text"])
        except (SourceBlocked, SourceUnavailable) as exc:
            result["note"] = f"lineup unavailable: {exc}"
            return result

        for team in lineups:
            for p in team.get("lineup", []):
                if _norm(player_name) in _norm(p.get("player_name")) or \
                        _norm(p.get("player_nickname")) == _norm(player_name):
                    result["player_found"] = True
                    # minutes for THIS match only (sample, not a season total)
                    mins = 0
                    for pos in p.get("positions", []) or []:
                        try:
                            start = pos.get("from") or "00:00"
                            end = pos.get("to") or "90:00"
                            sm = int(start.split(":")[0]); em = int(end.split(":")[0])
                            mins += max(0, em - sm)
                        except Exception:
                            pass
                    result["sample_minutes"] = mins or None
                    result["note"] = ("validation sample only: player confirmed in one "
                                      "match lineup; full-season aggregation intentionally "
                                      "not performed")
                    return result
        result["note"] = "player not found in sampled lineup"
        return result
