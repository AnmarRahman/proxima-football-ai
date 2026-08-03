"""Offline tests for the Tier-A feasibility package: leakage controls,
null-vs-zero handling, target censoring, non-negativity, and the reserve/youth
filter. No network access.

Run:  python -m unittest discover -s backend/python/model_feasibility/tests
"""

import math
import sys
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

import build_dataset                                 # noqa: E402
from evaluate import clip0                           # noqa: E402
from features import FEATURE_COLUMNS, build_feature_frame  # noqa: E402


def rec(pid, seasons, active=False, pos="FW", coarse="FWD", birth=1990):
    return {
        "player_id": pid, "name": pid, "position_group": pos, "coarse_group": coarse,
        "active": active, "birth_year": birth,
        "seasons": [{"season": y, "appearances": a, "goals": g,
                     "stat_scope": "domestic_league"} for (y, a, g) in seasons],
    }


class LeakageTests(unittest.TestCase):
    def test_features_do_not_use_future_seasons(self):
        base = [rec("p", [(2010, 20, 5), (2011, 25, 8), (2012, 30, 10), (2013, 28, 9)])]
        changed = [rec("p", [(2010, 20, 5), (2011, 25, 8), (2012, 30, 10), (2013, 99, 99)])]
        fb = build_feature_frame(base).sort_values("season_year").reset_index(drop=True)
        fc = build_feature_frame(changed).sort_values("season_year").reset_index(drop=True)
        # rows for 2010-2012 must be identical (they precede the changed 2013 season)
        for yr in (2010, 2011, 2012):
            rb = fb[fb.season_year == yr][FEATURE_COLUMNS].to_numpy(dtype=float)
            rc = fc[fc.season_year == yr][FEATURE_COLUMNS].to_numpy(dtype=float)
            self.assertTrue(np.allclose(rb, rc, equal_nan=True),
                            f"features for {yr} changed when a future season changed")

    def test_target_uses_next_season(self):
        f = build_feature_frame([rec("p", [(2010, 20, 5), (2011, 25, 8)])])
        row2010 = f[f.season_year == 2010].iloc[0]
        self.assertEqual(row2010["y_next_apps"], 25)
        self.assertEqual(row2010["y_next_goals"], 8)


class NullVsZeroTests(unittest.TestCase):
    def test_first_season_lag_is_missing_not_zero(self):
        f = build_feature_frame([rec("p", [(2010, 20, 5), (2011, 25, 8)])])
        r = f[f.season_year == 2010].iloc[0]
        self.assertTrue(math.isnan(r["lag1_apps"]))
        self.assertEqual(r["lag1_apps_missing"], 1.0)

    def test_real_zero_season_is_zero_not_missing(self):
        # a genuine 0-apps season (injury) must appear as lag value 0.0, not NaN
        f = build_feature_frame([rec("p", [(2010, 30, 10), (2011, 0, 0), (2012, 20, 5)])])
        r2012 = f[f.season_year == 2012].iloc[0]
        self.assertEqual(r2012["lag1_apps"], 0.0)          # 2011 had 0 apps (sourced zero)
        self.assertEqual(r2012["lag1_apps_missing"], 0.0)  # present, not missing
        self.assertEqual(r2012["cur_apps"], 20)


class CensoringTests(unittest.TestCase):
    def test_retired_last_season_continue_zero(self):
        f = build_feature_frame([rec("r", [(2010, 20, 5), (2011, 10, 2)], active=False)])
        last = f[f.season_year == 2011].iloc[0]
        first = f[f.season_year == 2010].iloc[0]
        self.assertEqual(last["y_continue"], 0.0)
        self.assertEqual(first["y_continue"], 1.0)

    def test_active_last_season_continue_censored(self):
        f = build_feature_frame([rec("a", [(2024, 30, 9), (2025, 28, 8)], active=True)])
        last = f[f.season_year == 2025].iloc[0]
        self.assertTrue(math.isnan(last["y_continue"]))     # censored, not 0

    def test_active_players_excluded_from_remaining(self):
        f = build_feature_frame([rec("a", [(2024, 30, 9), (2025, 28, 8)], active=True)])
        self.assertTrue(f["y_remaining"].isna().all())

    def test_retired_remaining_counts_down(self):
        f = build_feature_frame([rec("r", [(2010, 20, 5), (2011, 10, 2), (2012, 5, 1)], active=False)])
        self.assertEqual(f[f.season_year == 2010].iloc[0]["y_remaining"], 2)
        self.assertEqual(f[f.season_year == 2012].iloc[0]["y_remaining"], 0)


class NonNegativityTests(unittest.TestCase):
    def test_clip_removes_negatives(self):
        out = clip0([-3.0, 2.5, 0.0, -0.1])
        self.assertTrue((out >= 0).all())
        self.assertEqual(list(out), [0.0, 2.5, 0.0, 0.0])


class ReserveFilterTests(unittest.TestCase):
    def test_reserve_and_youth_detected(self):
        self.assertTrue(build_dataset.is_reserve("Barcelona B", "Segunda División B"))
        self.assertTrue(build_dataset.is_reserve("Sevilla Atlético", "Segunda División B"))
        self.assertTrue(build_dataset.is_reserve("Bryne 2", "3. divisjon"))
        self.assertTrue(build_dataset.is_reserve("Real Madrid Castilla", ""))
        self.assertFalse(build_dataset.is_reserve("Real Madrid", "La Liga"))
        self.assertFalse(build_dataset.is_reserve("Liverpool", "Premier League"))


class DeterminismTests(unittest.TestCase):
    def test_feature_frame_is_deterministic(self):
        ds = [rec("p", [(2010, 20, 5), (2011, 25, 8), (2012, 30, 10)])]
        a = build_feature_frame(ds)[FEATURE_COLUMNS].to_numpy(dtype=float)
        b = build_feature_frame(ds)[FEATURE_COLUMNS].to_numpy(dtype=float)
        self.assertTrue(np.allclose(a, b, equal_nan=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
