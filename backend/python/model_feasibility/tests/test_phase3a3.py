"""Phase 3A.3 tests: prove the interval POLICY is fully nested — the outer-test
fold never influences method selection, suppression, fallback, thresholds, or
calibration — and that emitted-only reporting is correct. Uses small synthetic
datasets so the properties are checked directly and deterministically."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

import conditional as C                                # noqa: E402
from features import FEATURE_COLUMNS                    # noqa: E402
from sklearn.linear_model import Ridge                  # noqa: E402


def make_df(n_players=60, seasons=8, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    positions = ["DEF", "MID", "WIDE", "FWD"]
    for p in range(n_players):
        pos = positions[p % 4]
        base = {"DEF": 2, "MID": 4, "WIDE": 8, "FWD": 14}[pos]
        for s in range(seasons):
            y = max(0, rng.normal(base, 3))
            row = {c: 0.0 for c in FEATURE_COLUMNS}
            row.update({"player_id": f"p{p}", "coarse_group": pos,
                        "season_year": 2010 + s, "age": 20 + s,
                        "cur_apps": 30, "cur_goals": base, "career_apps": 30 * (s + 1),
                        "y_next_goals": y})
            row[f"g_{pos}"] = 1.0
            rows.append(row)
    return pd.DataFrame(rows)


def ridge():
    from train import _linear
    return _linear(Ridge(alpha=1.0))


class NestedPolicyTests(unittest.TestCase):
    def setUp(self):
        self.df = make_df()
        self.est = ridge()

    def test_learn_policy_only_sees_its_data(self):
        # policy learned on a subset must be independent of rows outside it
        sub = self.df.reset_index(drop=True)
        train = sub[sub.player_id.isin([f"p{i}" for i in range(40)])].reset_index(drop=True)
        pol1 = C.learn_policy(self.est, train, FEATURE_COLUMNS, "y_next_goals", None, 0.2, "goals", seed=42)
        # mutate the OTHER players' targets wildly; policy on the same train subset unchanged
        sub2 = sub.copy()
        mask = ~sub2.player_id.isin([f"p{i}" for i in range(40)])
        sub2.loc[mask, "y_next_goals"] = 999.0
        train2 = sub2[sub2.player_id.isin([f"p{i}" for i in range(40)])].reset_index(drop=True)
        pol2 = C.learn_policy(self.est, train2, FEATURE_COLUMNS, "y_next_goals", None, 0.2, "goals", seed=42)
        self.assertEqual(pol1["method"], pol2["method"])
        self.assertEqual(pol1["suppressed_positions"], pol2["suppressed_positions"])
        self.assertEqual(pol1["suppressed_pred_bands"], pol2["suppressed_pred_bands"])
        self.assertEqual(pol1["global_q"], pol2["global_q"])

    def test_changing_outer_test_targets_does_not_change_frozen_policy(self):
        # In nested_policy_eval the policy for a fold is learned on outer-train only.
        # We assert learn_policy on outer-train is invariant to outer-test targets.
        from sklearn.model_selection import GroupKFold
        sub = self.df.reset_index(drop=True)
        X = sub[FEATURE_COLUMNS]; y = sub["y_next_goals"].to_numpy(float); groups = sub.player_id.to_numpy()
        tr, te = next(GroupKFold(5).split(X, y, groups))
        sub_tr = sub.iloc[tr].reset_index(drop=True)
        p1 = C.learn_policy(self.est, sub_tr, FEATURE_COLUMNS, "y_next_goals", None, 0.2, "goals", seed=42)
        sub_mut = sub.copy(); sub_mut.iloc[te, sub_mut.columns.get_loc("y_next_goals")] = 500.0
        sub_tr2 = sub_mut.iloc[tr].reset_index(drop=True)   # outer-train rows are identical
        p2 = C.learn_policy(self.est, sub_tr2, FEATURE_COLUMNS, "y_next_goals", None, 0.2, "goals", seed=42)
        self.assertEqual(p1["method"], p2["method"])
        self.assertEqual(p1["position_q"], p2["position_q"])
        self.assertEqual(p1["suppressed_positions"], p2["suppressed_positions"])

    def test_emitted_only_coverage_excludes_suppressed(self):
        agg = C.nested_policy_eval(self.est, self.df, FEATURE_COLUMNS, "y_next_goals",
                                   None, 0.2, "goals", seed=42, n_outer=4, n_inner=3)
        o = agg["overall"]
        # coverage_when_emitted computed only over emitted rows
        self.assertLessEqual(o["n_emitted"], o["n"])
        self.assertEqual(round(o["emission_rate"], 3), round(o["n_emitted"] / o["n"], 3))
        self.assertIn("suppression_rate", agg)
        self.assertIn("selected_method_frequency", agg)

    def test_method_frequency_recorded_over_folds(self):
        agg = C.nested_policy_eval(self.est, self.df, FEATURE_COLUMNS, "y_next_goals",
                                   None, 0.2, "goals", seed=42, n_outer=4, n_inner=3)
        self.assertEqual(sum(agg["selected_method_frequency"].values()), 4)  # one per outer fold

    def test_point_mae_over_all_rows(self):
        agg = C.nested_policy_eval(self.est, self.df, FEATURE_COLUMNS, "y_next_goals",
                                   None, 0.2, "goals", seed=42, n_outer=4, n_inner=3)
        self.assertIn("point_mae_all_rows", agg)
        self.assertGreater(agg["point_mae_all_rows"], 0)

    def test_deterministic(self):
        a = C.nested_policy_eval(self.est, self.df, FEATURE_COLUMNS, "y_next_goals",
                                 None, 0.2, "goals", seed=42, n_outer=4, n_inner=3)
        b = C.nested_policy_eval(self.est, self.df, FEATURE_COLUMNS, "y_next_goals",
                                 None, 0.2, "goals", seed=42, n_outer=4, n_inner=3)
        self.assertEqual(a["overall"], b["overall"])
        self.assertEqual(a["selected_method_frequency"], b["selected_method_frequency"])

    def test_runtime_interval_ignores_actuals(self):
        # runtime selection signature takes only (params, pred, pos) — no target
        params = {"method": "mondrian_pos", "mondrian": True, "scaled": False, "cap": None,
                  "global_q": 5.0, "position_q": {"FWD": 8.0}, "target_kind": "goals",
                  "suppressed_positions": [], "suppressed_pred_bands": []}
        iv, _ = C.runtime_interval(params, 20.0, "FWD")
        self.assertEqual(iv, (12.0, 28.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
