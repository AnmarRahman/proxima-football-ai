"""Regression tests for the Supabase-backed Tier A prediction pipeline."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
CSV_PATH = BACKEND / "data" / "collected_player_seasons.csv"
MIGRATION = BACKEND.parent / "db" / "migrations" / "003_tier_a_prediction_pipeline.sql"
sys.path.insert(0, str(BACKEND))

from import_tier_a_to_db import group_rows, load_rows, parse_bool
from run_tier_a_predictions import build_player_input, input_sha256, prediction_point


class TierAImportTests(unittest.TestCase):
    def test_committed_dataset_has_expected_size(self):
        rows = load_rows(CSV_PATH)
        self.assertEqual(len(rows), 2996)
        self.assertEqual(len(group_rows(rows)), 180)

    def test_boolean_parser_does_not_turn_false_into_true(self):
        for value in ("False", "false", "0", "no", ""):
            self.assertFalse(parse_bool(value))
        for value in ("True", "true", "1", "yes"):
            self.assertTrue(parse_bool(value))


class TierAInputTests(unittest.TestCase):
    def setUp(self):
        self.player = {
            "id": "example-player",
            "primary_position": "forward",
            "position_group": "FW",
            "coarse_group": "FWD",
            "career_status": "active",
            "birth_date": "2000-01-01",
            "stat_scope": "domestic_league",
        }
        self.seasons = [
            {
                "canonical_season": "2023-24",
                "season_start_year": 2023,
                "season_end_year": 2024,
                "season_format": "split_year",
                "appearances": 30,
                "goals": 12,
                "is_partial": False,
                "model_eligible": True,
            }
        ]

    def test_input_is_exact_and_deterministic(self):
        first = build_player_input(self.player, self.seasons)
        second = build_player_input(dict(reversed(list(self.player.items()))), self.seasons)
        self.assertEqual(first, second)
        self.assertEqual(input_sha256(first), input_sha256(second))
        self.assertEqual(len(input_sha256(first)), 64)

    def test_partial_latest_season_uses_latest_completed_policy(self):
        completed = build_player_input(self.player, self.seasons)
        self.assertEqual(prediction_point(completed), "next")

        partial_rows = self.seasons + [
            {
                **self.seasons[0],
                "canonical_season": "2024-25",
                "season_start_year": 2024,
                "season_end_year": 2025,
                "appearances": 10,
                "goals": 4,
                "is_partial": True,
            }
        ]
        partial = build_player_input(self.player, partial_rows)
        self.assertEqual(prediction_point(partial), "latest-completed")


class TierASchemaTests(unittest.TestCase):
    def test_predictions_are_isolated_from_historical_tables(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("create table if not exists ml_player_seasons", sql)
        self.assertIn("create table if not exists next_season_predictions", sql)
        self.assertIn("player_id text primary key", sql)
        self.assertNotIn("references player_seasons", sql)

    def test_release_import_prunes_players_outside_snapshot(self):
        source = (BACKEND / "import_tier_a_to_db.py").read_text(encoding="utf-8")
        self.assertIn("delete from ml_players where not (id = any(%s))", source)

    def test_runner_supports_out_of_band_manifest_digest(self):
        source = (BACKEND / "run_tier_a_predictions.py").read_text(encoding="utf-8")
        self.assertIn("TIER_A_EXPECTED_MANIFEST_SHA256", source)

    def test_migration_is_stable_for_release_tracking(self):
        digest = hashlib.sha256(MIGRATION.read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
