"""Offline tests for Tier-A collection normalization, identity decisions,
aggregation, deterministic IDs, and cache reuse. No network access.

Run:  python -m unittest discover -s backend/python/data/collection/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG.parent / "acquisition"))

import build_csv                                    # noqa: E402
from collect import build_record, validate_record, is_reserve, slugify  # noqa: E402
from identity import choose_candidate               # noqa: E402
from sources.base import CachingHTTPClient          # noqa: E402
from sources.wikipedia_source import _season_start_year  # noqa: E402

IDENT = {"birth_date": "1990-01-01", "wikidata_id": "Q1", "enwiki_title": "Test Player",
         "nationality": "Testland", "position_label": "defender",
         "occupation_footballer": True, "sitelinks": 50, "status": "ok", "note": ""}
ROSTER = {"name": "Test Player", "section_title": "Centre-backs",
          "position_group": "CB", "coarse_group": "DEF"}


def meta(career):
    return {"url": "http://x", "retrieved_at": "2026-07-27", "revision": 123,
            "career": [{"season": s, "club": c, "competition": comp,
                        "appearances": a, "goals": g} for (s, c, comp, a, g) in career]}


def rec_for(career, ident=None):
    r, _, _ = build_record(ident or IDENT, ROSTER, meta(career))
    return r


class SeasonNormalizationTests(unittest.TestCase):
    def test_split_year_and_calendar_start_year(self):
        self.assertEqual(_season_start_year("2015–16[3]"), 2015)   # split-year
        self.assertEqual(_season_start_year("2018"), 2018)              # calendar-year

    def test_mid_season_transfer_preserves_both_club_rows(self):
        r = rec_for([(2017, "Southampton", "Premier League", 13, 0),
                     (2017, "Liverpool", "Premier League", 14, 1)])
        rows = [s for s in r["seasons"] if s["season_start_year"] == 2017]
        self.assertEqual(len(rows), 2)                       # both clubs kept
        self.assertEqual({x["team_id"] for x in rows}, {"southampton", "liverpool"})

    def test_loan_row_is_kept(self):
        self.assertFalse(is_reserve("Milan (loan)", "Serie A"))
        r = rec_for([(2013, "Milan (loan)", "Serie A", 20, 3)])
        self.assertEqual(len(r["seasons"]), 1)

    def test_aggregate_row_is_dropped(self):
        r = rec_for([(2017, "Southampton", "Premier League", 13, 0),
                     (2017, "Total", "", 27, 1)])           # aggregate row
        self.assertEqual(len(r["seasons"]), 1)
        self.assertEqual(r["seasons"][0]["team_id"], "southampton")

    def test_current_season_is_partial(self):
        r = rec_for([(2020, "Club", "League", 30, 5), (2026, "Club", "League", 3, 0)])
        by = {s["season"]: s["is_partial"] for s in r["seasons"]}
        self.assertFalse(by[2020])
        self.assertTrue(by[2026])                            # ongoing

    def test_duplicate_identical_rows_dedup(self):
        r = rec_for([(2019, "Club", "League", 30, 4), (2019, "Club", "League", 30, 4)])
        self.assertEqual(len(r["seasons"]), 1)


class MissingVsZeroTests(unittest.TestCase):
    def test_zero_apps_kept_as_row(self):
        r = rec_for([(2010, "Club", "League", 30, 10), (2011, "Club", "League", 0, 0),
                     (2012, "Club", "League", 20, 5)])
        by = {s["season"]: s for s in r["seasons"]}
        self.assertIn(2011, by)                              # 0 apps is a real season
        self.assertEqual(by[2011]["appearances"], 0)
        self.assertEqual(r["coverage"]["missing_middle_seasons"], [])

    def test_career_gap_is_warning_not_error(self):
        # 2011 has no senior season (did-not-play year) -> recorded, NOT an error
        r = rec_for([(2010, "Club", "League", 30, 10), (2012, "Club", "League", 20, 5)])
        self.assertEqual(r["coverage"]["career_gaps"], [2011])
        errs, warns = validate_record(r, IDENT)
        self.assertFalse(any("missing" in e or "gap" in e for e in errs))  # collectible
        self.assertTrue(any("career gap" in w for w in warns))


class ChildhoodTests(unittest.TestCase):
    def test_childhood_rows_excluded(self):
        # birth 1990; a 2003 row = age 13 (childhood) must be dropped, 2008 kept
        r = rec_for([(2003, "Lanceros", "Categoría Primera A", 5, 1),
                     (2008, "Senior Club", "La Liga", 30, 8)])
        yrs = [s["season"] for s in r["seasons"]]
        self.assertEqual(yrs, [2008])
        self.assertEqual(len(r["coverage"]["childhood_rows_dropped"]), 1)
        self.assertEqual(r["coverage"]["career_gaps"], [])       # no false gap


class SplitChampionshipTests(unittest.TestCase):
    """Apertura/Clausura and similar phases (Uruguay, Argentina, Mexico...)."""

    def test_two_phases_same_season_are_both_kept(self):
        # same season+club+league, different apps -> distinct phases, not a conflict
        r = rec_for([(2005, "Nacional", "Uruguayan Primera División", 15, 5),
                     (2005, "Nacional", "Uruguayan Primera División", 12, 3)])
        rows = [s for s in r["seasons"] if s["season_start_year"] == 2005]
        self.assertEqual(len(rows), 2)
        self.assertEqual(r["coverage"]["duplicate_conflicts"], [])
        errs, _ = validate_record(r, IDENT)
        self.assertEqual(errs, [])                               # collectible

    def test_phase_aggregation_sums_non_overlapping(self):
        r = rec_for([(2016, "Racing", "Argentine Primera División", 10, 4),
                     (2016, "Racing", "Argentine Primera División", 9, 2)])
        agg = [s for s in build_csv.aggregate_seasons([r]) if s["season_start_year"] == 2016][0]
        self.assertEqual(agg["appearances"], 19)                 # 10 + 9 phases
        self.assertEqual(agg["goals"], 6)

    def test_full_season_total_row_dropped(self):
        # two phases + a season total that equals their sum -> total dropped
        r = rec_for([(2007, "Cerro", "Uruguayan Primera División", 14, 2),
                     (2007, "Cerro", "Uruguayan Primera División", 16, 3),
                     (2007, "Cerro", "Uruguayan Primera División", 30, 5)])
        rows = [s for s in r["seasons"] if s["season_start_year"] == 2007]
        self.assertEqual(len(rows), 2)                           # total (30,5) removed
        self.assertEqual(r["coverage"]["total_rows_dropped"], 1)
        agg = [s for s in build_csv.aggregate_seasons([r]) if s["season_start_year"] == 2007][0]
        self.assertEqual(agg["appearances"], 30)                 # 14+16, not 60


class YouthReserveTests(unittest.TestCase):
    def test_reserve_and_youth_excluded(self):
        self.assertTrue(is_reserve("Barcelona B", "Segunda División B"))
        self.assertTrue(is_reserve("Real Madrid Castilla", ""))
        self.assertTrue(is_reserve("Barcelona Atlètic", "Segunda División"))   # reserve
        self.assertTrue(is_reserve("Sevilla Atlético", ""))                    # reserve
        self.assertFalse(is_reserve("Atlético Madrid", "La Liga"))             # SENIOR
        self.assertFalse(is_reserve("Atlético Mineiro", "Série A"))            # SENIOR
        self.assertFalse(is_reserve("Wigan Athletic", "Premier League"))       # SENIOR
        self.assertFalse(is_reserve("Real Madrid", "La Liga"))
        r = rec_for([(2004, "Sevilla Atlético", "Segunda División B", 20, 1),
                     (2005, "Sevilla", "La Liga", 30, 2)])
        self.assertEqual([s["team_id"] for s in r["seasons"]], ["sevilla"])
        self.assertIn(2004, r["coverage"]["reserve_or_youth_years_dropped"])


class IdentityDecisionTests(unittest.TestCase):
    def base(self, **kw):
        d = {"footballer": True, "is_human": True, "enwiki": "T", "name_match": 1.0,
             "sitelinks": 40}
        d.update(kw); return d

    def test_ok_single_footballer(self):
        best, status, _ = choose_candidate([self.base()])
        self.assertEqual(status, "ok")

    def test_ambiguous_two_prominent(self):
        best, status, _ = choose_candidate([self.base(sitelinks=40), self.base(sitelinks=35)])
        self.assertEqual(status, "ambiguous")

    def test_not_footballer(self):
        best, status, _ = choose_candidate([self.base(footballer=False)])
        self.assertEqual(status, "not_footballer")
        self.assertIsNone(best)


class AggregationTests(unittest.TestCase):
    def test_season_aggregation_sums_clubs_without_double_count(self):
        r = rec_for([(2017, "Southampton", "Premier League", 13, 0),
                     (2017, "Liverpool", "Premier League", 14, 1)])
        seasons = list(build_csv.aggregate_seasons([r]))
        row2017 = [s for s in seasons if s["season_start_year"] == 2017][0]
        self.assertEqual(row2017["appearances"], 27)         # 13 + 14
        self.assertEqual(row2017["goals"], 1)
        self.assertEqual(row2017["n_clubs"], 2)


class DeterministicIdTests(unittest.TestCase):
    def test_slugify_stable_and_accent_safe(self):
        self.assertEqual(slugify("Gerard Piqué"), "gerard-pique")
        self.assertEqual(slugify("Gerard Piqué"), slugify("Gerard Piqué"))
        self.assertEqual(slugify("Sevilla Atlético"), "sevilla-atletico")


class CacheReuseTests(unittest.TestCase):
    def test_second_get_served_from_cache_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = CachingHTTPClient("t", cache_dir=Path(tmp), min_delay=0)
            url = "https://example.org/x"
            body, meta_p = client._key(url, None, "html")
            body.write_text("<html>cached</html>", encoding="utf-8")
            meta_p.write_text('{"url":"%s","status":200,"retrieved_at":"2026-07-27"}' % url,
                              encoding="utf-8")
            resp = client.get(url, ext="html")               # must not hit network
            self.assertTrue(resp["from_cache"])
            self.assertEqual(client.hits, 1)
            self.assertEqual(client.misses, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
