"""Season chronology utilities.

A canonical season is identified by its source label (e.g. "2015-16" or "2005").
We never infer chronology from start year alone: split-year and calendar-year
seasons, calendar->split transitions, and within-canonical-season transfers all
need explicit handling.

Fields per season: canonical_season, season_source_label, season_start_year,
season_end_year, season_format ("split_year" | "calendar_year").
"""

import re


def season_end_year(start_year, season_format, source_label=None):
    """End (spring) year of a season. Split-year YYYY-YY ends start+1; a
    calendar-year season ends in the same year. If a label carries an explicit
    end (e.g. '2015-16' or '1999-2000'), honour it."""
    if source_label:
        m = re.search(r"(\d{4})\s*[–\-/]\s*(\d{2,4})", str(source_label))
        if m:
            start = int(m.group(1))
            tail = m.group(2)
            end = int(tail) if len(tail) == 4 else (start // 100) * 100 + int(tail)
            if end < start:                      # e.g. 1999-00 -> 2000
                end += 100
            return end
    return int(start_year) + (1 if season_format == "split_year" else 0)


def seasons_consecutive(a, b):
    """True if season b immediately follows season a in football-calendar time.

    Handles:
      * split-year -> split-year  ("2015-16" -> "2016-17")   start diff 1
      * calendar   -> calendar    ("2017" -> "2018")          start diff 1
      * calendar   -> split (transition, "2005" -> "2005-06") same start, end+1
      * split      -> calendar (Europe -> MLS mid-year)       start diff 1
    A multi-year gap, or the same canonical season (a transfer within one
    season), is NOT consecutive.
    """
    if a.get("canonical_season") == b.get("canonical_season"):
        return False                              # same season (e.g. transfer split)
    a_s, b_s = int(a["season_start_year"]), int(b["season_start_year"])
    a_e = int(a.get("season_end_year", season_end_year(a_s, a.get("season_format"),
                                                       a.get("season_source_label"))))
    b_e = int(b.get("season_end_year", season_end_year(b_s, b.get("season_format"),
                                                       b.get("season_source_label"))))
    if b_s - a_s == 1:
        return True
    if b_s == a_s and b_e == a_e + 1:             # calendar -> split transition
        return True
    return False


def order_seasons(seasons):
    """Deterministic chronological order for a player's canonical seasons."""
    return sorted(seasons, key=lambda s: (int(s["season_start_year"]),
                                          int(s.get("season_end_year",
                                              season_end_year(s["season_start_year"],
                                                              s.get("season_format"),
                                                              s.get("season_source_label")))),
                                          str(s.get("canonical_season"))))


def next_is_consecutive(ordered, i):
    """Given a chronologically ordered season list, is entry i+1 the genuine
    next season (consecutive) rather than after a gap?"""
    if i + 1 >= len(ordered):
        return False
    return seasons_consecutive(ordered[i], ordered[i + 1])
