"""Phase 2C tests: chronology, corrected targets (partial exclusion, censoring,
gaps, comebacks), eligibility, career status, cluster bootstrap, and recursive
forecasting (leakage, non-negativity, termination, widening uncertainty)."""

import math
import sys
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG.parent / "data" / "collection"))

import chronology as CH                              # noqa: E402
import dataset_corrected as DC                       # noqa: E402
import eligibility as EL                             # noqa: E402
import career_status as CS                           # noqa: E402
import backtest as BT                                # noqa: E402
from bootstrap import cluster_paired_bootstrap       # noqa: E402


def player(pid, seasons, status="retired", coarse="FWD", birth=1990):
    return {"player_id": pid, "name": pid, "coarse_group": coarse,
            "position_group": coarse, "career_status": status, "birth_year": birth,
            "seasons": [{"canonical_season": c, "season_start_year": s, "season_end_year": e,
                         "season_format": f, "appearances": a, "goals": g,
                         "is_partial": p, "model_eligible": el}
                        for (c, s, e, f, a, g, p, el) in seasons]}


CAL = "calendar_year"; SPL = "split_year"


class ChronologyTests(unittest.TestCase):
    def test_end_year(self):
        self.assertEqual(CH.season_end_year(2015, SPL, "2015–16"), 2016)
        self.assertEqual(CH.season_end_year(2018, CAL, "2018"), 2018)
        self.assertEqual(CH.season_end_year(1999, SPL, "1999–2000"), 2000)

    def s(self, canon, start, end, fmt):
        return {"canonical_season": canon, "season_start_year": start,
                "season_end_year": end, "season_format": fmt, "season_source_label": canon}

    def test_split_to_split(self):
        self.assertTrue(CH.seasons_consecutive(self.s("2015–16", 2015, 2016, SPL),
                                               self.s("2016–17", 2016, 2017, SPL)))

    def test_calendar_to_calendar(self):
        self.assertTrue(CH.seasons_consecutive(self.s("2017", 2017, 2017, CAL),
                                               self.s("2018", 2018, 2018, CAL)))

    def test_calendar_to_split_transition(self):
        self.assertTrue(CH.seasons_consecutive(self.s("2005", 2005, 2005, CAL),
                                               self.s("2005–06", 2005, 2006, SPL)))

    def test_gap_not_consecutive(self):
        self.assertFalse(CH.seasons_consecutive(self.s("2018", 2018, 2018, CAL),
                                                self.s("2021", 2021, 2021, CAL)))

    def test_same_season_not_consecutive(self):
        self.assertFalse(CH.seasons_consecutive(self.s("2015–16", 2015, 2016, SPL),
                                                self.s("2015–16", 2015, 2016, SPL)))


class CorrectedTargetTests(unittest.TestCase):
    def test_partial_next_excluded_as_target(self):
        p = player("x", [("2018", 2018, 2018, CAL, 30, 10, False, True),
                         ("2019", 2019, 2019, CAL, 5, 1, True, True)])
        df, removed = DC.build_frame([p])
        row = df[df.season_year == 2018].iloc[0]
        self.assertTrue(math.isnan(row["y_next_apps"]))
        self.assertEqual(removed["target_from_partial_next_excluded"], 1)

    def test_active_last_season_right_censored(self):
        p = player("a", [("2024", 2024, 2024, CAL, 30, 9, False, True),
                         ("2025", 2025, 2025, CAL, 28, 8, False, True)], status="active")
        df, _ = DC.build_frame([p])
        last = df[df.season_year == 2025].iloc[0]
        self.assertTrue(math.isnan(last["y_continue_next_season"]))

    def test_retired_last_season_continuation_zero(self):
        p = player("r", [("2010", 2010, 2010, CAL, 30, 5, False, True),
                         ("2011", 2011, 2011, CAL, 10, 2, False, True)], status="retired")
        df, _ = DC.build_frame([p])
        last = df[df.season_year == 2011].iloc[0]
        self.assertEqual(last["y_continue_next_season"], 0.0)

    def test_career_gap_did_not_continue_but_ever_returns(self):
        p = player("g", [("2018", 2018, 2018, CAL, 30, 10, False, True),
                         ("2021", 2021, 2021, CAL, 20, 5, False, True)], status="retired")
        df, _ = DC.build_frame([p])
        r = df[df.season_year == 2018].iloc[0]
        self.assertEqual(r["y_continue_next_season"], 0.0)   # no season next year
        self.assertEqual(r["y_ever_returns"], 1.0)           # but did return later

    def test_no_future_leakage(self):
        base = player("p", [("2018", 2018, 2018, CAL, 20, 5, False, True),
                            ("2019", 2019, 2019, CAL, 25, 8, False, True),
                            ("2020", 2020, 2020, CAL, 30, 10, False, True)])
        changed = player("p", [("2018", 2018, 2018, CAL, 20, 5, False, True),
                               ("2019", 2019, 2019, CAL, 25, 8, False, True),
                               ("2020", 2020, 2020, CAL, 99, 99, False, True)])
        from features import FEATURE_COLUMNS
        d0, _ = DC.build_frame([base]); d1, _ = DC.build_frame([changed])
        r0 = d0[d0.season_year == 2018][FEATURE_COLUMNS].to_numpy(float)
        r1 = d1[d1.season_year == 2018][FEATURE_COLUMNS].to_numpy(float)
        self.assertTrue(np.allclose(r0, r1, equal_nan=True))


class EligibilityTests(unittest.TestCase):
    def test_amateur_excluded(self):
        level, elig, reason = EL.classify("MFL Premier Division", 2, 6)
        self.assertFalse(elig); self.assertEqual(reason, "amateur_or_non_league")

    def test_post_retirement_cameo_excluded(self):
        level, elig, reason = EL.classify("Indian Super League", 3, 4)
        self.assertFalse(elig); self.assertEqual(reason, "post_retirement_cameo")

    def test_normal_season_eligible(self):
        level, elig, reason = EL.classify("Premier League", 34, 1)
        self.assertTrue(elig); self.assertIsNone(reason)


class CareerStatusTests(unittest.TestCase):
    def test_death_is_retired(self):
        claims = {"P570": [{"mainsnak": {"datavalue": {"value": {"time": "+2018-03-01T00:00:00Z"}}}}]}
        st = CS.resolve_status(claims, "Q1", 2000)
        self.assertEqual(st["career_status"], "retired")

    def test_open_membership_recent_is_active(self):
        claims = {"P54": [{"qualifiers": {}}]}          # no end date -> open
        st = CS.resolve_status(claims, "Q1", 2026)
        self.assertEqual(st["career_status"], "active")

    def test_old_last_season_is_retired(self):
        claims = {"P54": [{"qualifiers": {"P582": [{"datavalue": {"value": {"time": "+2015-06-01T00:00:00Z"}}}]}}]}
        st = CS.resolve_status(claims, "Q1", 2015)
        self.assertEqual(st["career_status"], "retired")


class BootstrapTests(unittest.TestCase):
    def test_cluster_paired_bootstrap_detects_better_model(self):
        y = np.array([10.0] * 40)
        model = np.array([10.0] * 40)          # perfect
        base = np.array([15.0] * 40)           # worse
        players = [f"p{i//4}" for i in range(40)]
        r = cluster_paired_bootstrap(y, model, base, players, n=500)
        self.assertGreater(r["diff_mean"], 0)
        self.assertEqual(r["p_model_beats_base"], 1.0)


class BacktestTests(unittest.TestCase):
    def rec(self, n=6):
        seasons = [{"canonical_season": str(2010 + k), "season_start_year": 2010 + k,
                    "season_end_year": 2010 + k, "season_format": CAL,
                    "appearances": 30, "goals": 8, "is_partial": False, "model_eligible": True}
                   for k in range(n)]
        return {"player_id": "z", "coarse_group": "FWD", "birth_year": 1990, "_ordered": seasons}

    class DummyReg:
        def __init__(self, v): self.v = v
        def predict(self, X): return np.array([self.v] * len(X))

    class DummyClf:
        def __init__(self, p): self.p = p
        def predict_proba(self, X): return np.array([[1 - self.p, self.p]] * len(X))

    def test_forecast_non_negative_and_capped_and_widening(self):
        steps = BT.forecast_model(self.rec(), 2, self.DummyReg(20), self.DummyReg(5),
                                  self.DummyClf(0.9), 5, resid_sd=8.0)
        active = [s for s in steps if not s.get("retired")]
        self.assertEqual(len(active), 5)
        self.assertTrue(all(s["pred_apps"] >= 0 and s["pred_goals"] >= 0 for s in active))
        self.assertTrue(all(s["pred_apps"] <= BT.APPS_CAP for s in active))
        widths = [s["interval_width"] for s in active]
        self.assertEqual(widths, sorted(widths))          # widening uncertainty
        self.assertTrue(widths[-1] > widths[0])

    def test_forecast_terminates_on_low_continuation(self):
        steps = BT.forecast_model(self.rec(), 2, self.DummyReg(20), self.DummyReg(5),
                                  self.DummyClf(0.1), 5, resid_sd=8.0)
        self.assertTrue(steps[-1]["retired"])
        self.assertEqual(sum(1 for s in steps if not s.get("retired")), 0)  # no season after retirement

    def test_apps_cap_enforced(self):
        steps = BT.forecast_model(self.rec(), 2, self.DummyReg(999), self.DummyReg(5),
                                  self.DummyClf(0.9), 3, resid_sd=8.0)
        self.assertTrue(all(s["pred_apps"] <= BT.APPS_CAP for s in steps if not s.get("retired")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
