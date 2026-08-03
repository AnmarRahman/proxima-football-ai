"""Offline unit tests for the acquisition package.

Covers normalization, provenance assembly, null-vs-zero handling, duplicate
detection, conflict detection, and Tier coverage scoring. No network access:
all inputs are synthetic source blocks.

Run:  python -m unittest discover -s backend/python/data/acquisition/tests
"""

import sys
import unittest
from pathlib import Path

ACQ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ACQ))

import coverage
import normalize
from provenance import build_sources
from sources.soccerdata_source import SoccerdataSource


def bio(provider="Wikipedia", **fields):
    return {"provider": provider, "url": f"http://x/{provider}",
            "retrieved_at": "2026-07-27", "fields": fields}


def stat(provider="Wikipedia", season=2019, team="Liverpool", team_id="liverpool",
         competition="Premier League", league_id="premierleague-2019", **fields):
    return {"provider": provider, "url": f"http://x/{provider}", "retrieved_at": "2026-07-27",
            "season": season, "team": team, "team_id": team_id,
            "competition": competition, "league_id": league_id, "position": None,
            "fields": fields}


class ProvenanceTests(unittest.TestCase):
    def test_groups_fields_by_provider(self):
        srcs = build_sources(
            {"appearances": "Wikipedia", "goals": "Wikipedia", "xG": "Understat"},
            {"Wikipedia": {"url": "w", "retrieved_at": "2026-07-27"},
             "Understat": {"url": "u", "retrieved_at": "2026-07-27"}},
        )
        by = {s["provider"]: s for s in srcs}
        self.assertEqual(by["Wikipedia"]["supports"], ["appearances", "goals"])
        self.assertEqual(by["Understat"]["supports"], ["xG"])
        self.assertEqual(by["Understat"]["url"], "u")


class NormalizeTests(unittest.TestCase):
    def test_null_vs_sourced_zero_preserved(self):
        data, conflicts = normalize.merge_player(
            "p", "Player",
            [bio(birth_date="1990-01-01", nationality="Testland", position="Centre-Back")],
            [stat(appearances=30, goals=0)],  # goals is a SOURCED zero
        )
        row = data["seasons"][0]
        self.assertEqual(row["goals"], 0)          # sourced zero preserved
        self.assertEqual(row["appearances"], 30)
        self.assertIsNone(row["assists"])          # unsourced -> null, not 0
        self.assertIsNone(row["minutes"])
        self.assertEqual(conflicts, [])
        # provenance covers the populated stats
        supports = data["seasons"][0]["sources"][0]["supports"]
        self.assertIn("appearances", supports)
        self.assertIn("goals", supports)

    def test_duplicate_identical_blocks_dedup_to_one_row(self):
        block = stat(appearances=30, goals=2)
        data, _ = normalize.merge_player("p", "P", [bio()], [block, dict(block)])
        self.assertEqual(len(data["seasons"]), 1)

    def test_conflict_detected_between_providers(self):
        data, conflicts = normalize.merge_player(
            "p", "P", [bio()],
            [stat(provider="A", goals=5, appearances=30),
             stat(provider="B", goals=7, appearances=30)],
            priority=["A", "B"],
        )
        self.assertEqual(len(data["seasons"]), 1)
        self.assertEqual(data["seasons"][0]["goals"], 5)  # priority A wins
        fields = [c["field"] for c in conflicts]
        self.assertIn("goals", fields)
        self.assertNotIn("appearances", fields)           # equal -> no conflict

    def test_split_season_marked_partial(self):
        data, _ = normalize.merge_player(
            "p", "P", [bio()],
            [stat(season=2017, team="Southampton", team_id="southampton",
                  league_id="pl-2017-so", appearances=13, goals=0),
             stat(season=2017, team="Liverpool", team_id="liverpool",
                  league_id="pl-2017-li", appearances=14, goals=1)],
        )
        self.assertTrue(all(r["is_partial"] for r in data["seasons"]))

    def test_ongoing_season_marked_partial(self):
        data, _ = normalize.merge_player(
            "p", "P", [bio()],
            [stat(season=2026, appearances=5, goals=1)],
            current_season_start=2026,
        )
        self.assertTrue(data["seasons"][0]["is_partial"])


class CoverageTests(unittest.TestCase):
    def _complete_file(self):
        return normalize.merge_player(
            "p", "P",
            [bio(birth_date="1990-01-01", nationality="Testland", position="Centre-Back")],
            [stat(appearances=30, goals=2)],
        )[0]

    def test_tier_a_complete_when_core_sourced(self):
        cov = coverage.coverage_for_file(self._complete_file())
        self.assertEqual(cov["tier_a_pct"], 100.0)
        self.assertTrue(cov["tier_a_complete"])
        self.assertEqual(cov["tier_b_pct"], 0.0)
        self.assertEqual(cov["tier_c_pct"], 0.0)
        self.assertEqual(cov["provenance_pct"], 100.0)

    def test_missing_identity_breaks_tier_a(self):
        data = normalize.merge_player(
            "p", "P", [bio(position="Centre-Back")],  # no birth_date/nationality
            [stat(appearances=30, goals=2)])[0]
        cov = coverage.coverage_for_file(data)
        self.assertFalse(cov["tier_a_complete"])

    def test_null_not_counted_zero_counted(self):
        # goals=0 sourced counts as present; assists null does not
        data = normalize.merge_player(
            "p", "P",
            [bio(birth_date="1990-01-01", nationality="T", position="CB")],
            [stat(appearances=10, goals=0)])[0]
        cov = coverage.coverage_for_file(data)
        self.assertTrue(cov["tier_a_complete"])           # goals=0 is present
        self.assertEqual(cov["tier_b_pct"], 0.0)          # assists/minutes null


class SoccerdataPolicyTests(unittest.TestCase):
    def test_soccerdata_excluded_from_collection(self):
        ev = SoccerdataSource().evaluate()
        self.assertFalse(ev["used_for_collection"])
        self.assertIn("impersonation", ev["reason"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
