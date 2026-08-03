"""Multi-season recursive career backtest (Phase 2C).

Historical-cutoff backtest: at each cutoff we hide every season after it, then
recursively forecast appearances, goals and continuation, stepping one canonical
season at a time. Features at each step are computed only from real history +
already-predicted seasons (never from hidden future). Trajectories terminate on
continuation probability, not a fixed age. Models are trained with the target
player held out (GroupKFold), so a player's own future never trains its forecast.

Constraints enforced: non-negative counts, a documented appearances cap,
no season after modelled retirement, and uncertainty that widens with horizon.

Baselines: naive age-curve ageing and previous-season persistence.
Writes results_multiseason.json.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import (HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor)
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataset_corrected as DC                       # noqa: E402
from features import COARSE_GROUPS, FEATURE_COLUMNS, _gpa, _safe_lag, _trend3  # noqa: E402

OUT = HERE / "results_multiseason.json"
SEED = 42
APPS_CAP = 60          # documented cap: max plausible domestic-league apps/season
CONTINUE_THRESHOLD = 0.5
MAX_AGE = 42           # hard safety backstop only (termination is prob-driven)
np.random.seed(SEED)


def prefix_features(apps, goals, i, birth_year, coarse):
    """Feature vector for 'current season = index i' from history apps[0..i]."""
    yr_age = None
    f = {}
    cum_a = sum(apps[:i + 1]); cum_g = sum(goals[:i + 1])
    f["age"] = np.nan  # set by caller (needs season year); placeholder
    f["years_experience"] = i + 1
    f["cur_apps"] = apps[i]; f["cur_goals"] = goals[i]
    f["cur_gpa"] = _gpa(goals[i], apps[i]); f["cur_apps_zero"] = 1.0 if apps[i] == 0 else 0.0
    f["career_apps"] = cum_a; f["career_goals"] = cum_g; f["career_gpa"] = _gpa(cum_g, cum_a)
    f["roll3_apps"] = float(np.mean(apps[max(0, i - 2):i + 1]))
    f["roll3_goals"] = float(np.mean(goals[max(0, i - 2):i + 1]))
    f["roll3_gpa"] = _gpa(sum(goals[max(0, i - 2):i + 1]), sum(apps[max(0, i - 2):i + 1]))
    f["apps_trend3"] = _trend3(apps, i)
    for k in range(1, 6):
        va, ma = _safe_lag(apps, i, k); vg, _ = _safe_lag(goals, i, k)
        f[f"lag{k}_apps"] = va; f[f"lag{k}_goals"] = vg; f[f"lag{k}_apps_missing"] = ma
    if i - 1 >= 0:
        f["delta_apps"] = float(apps[i] - apps[i - 1]); f["delta_goals"] = float(goals[i] - goals[i - 1])
        f["delta_missing"] = 0.0
    else:
        f["delta_apps"] = np.nan; f["delta_goals"] = np.nan; f["delta_missing"] = 1.0
    for g in COARSE_GROUPS:
        f[f"g_{g}"] = 1.0 if coarse == g else 0.0
    return f


def _feat_row(apps, goals, years, i, birth_year, coarse):
    f = prefix_features(apps, goals, i, birth_year, coarse)
    age = (years[i] - birth_year) if birth_year else np.nan
    f["age"] = age; f["age_sq"] = age * age if age == age else np.nan
    return pd.DataFrame([f]).reindex(columns=FEATURE_COLUMNS)


def clip_apps(x):
    return float(min(APPS_CAP, max(0.0, x)))


def build_age_curve(players, holdout):
    apps_by_age = defaultdict(list); goals_by_age = defaultdict(list)
    for rec in players:
        if rec["player_id"] == holdout or not rec["birth_year"]:
            continue
        for s in rec["seasons"]:
            if not s["model_eligible"]:
                continue
            a = s["season_start_year"] - rec["birth_year"]
            apps_by_age[a].append(s["appearances"]); goals_by_age[a].append(s["goals"])
    ca = {a: float(np.mean(v)) for a, v in apps_by_age.items()}
    cg = {a: float(np.mean(v)) for a, v in goals_by_age.items()}
    return ca, cg


def forecast_model(rec, cutoff_i, reg_apps, reg_goals, clf, max_h, resid_sd):
    """Recursive model trajectory from cutoff. Returns list of step dicts."""
    seasons = rec["_ordered"]
    birth_year = rec["birth_year"]; coarse = rec["coarse_group"]
    apps = [s["appearances"] for s in seasons[:cutoff_i + 1]]
    goals = [s["goals"] for s in seasons[:cutoff_i + 1]]
    years = [s["season_start_year"] for s in seasons[:cutoff_i + 1]]
    steps = []; survival = 1.0
    for h in range(1, max_h + 1):
        i = len(apps) - 1
        X = _feat_row(apps, goals, years, i, birth_year, coarse)
        p_cont = float(clf.predict_proba(X)[:, 1][0])
        survival *= p_cont
        if p_cont < CONTINUE_THRESHOLD or (birth_year and years[-1] + 1 - birth_year > MAX_AGE):
            steps.append({"h": h, "retired": True, "p_continue": round(p_cont, 3),
                          "survival": round(survival, 3)})
            break
        na = clip_apps(float(reg_apps.predict(X)[0]))
        ng = max(0.0, float(reg_goals.predict(X)[0]))
        steps.append({"h": h, "retired": False, "pred_apps": round(na, 1),
                      "pred_goals": round(ng, 1), "p_continue": round(p_cont, 3),
                      "survival": round(survival, 3),
                      "interval_width": round(resid_sd * np.sqrt(h), 1)})  # widens with h
        apps.append(na); goals.append(ng); years.append(years[-1] + 1)
    return steps


def forecast_persistence(rec, cutoff_i, max_h):
    seasons = rec["_ordered"]
    la, lg = seasons[cutoff_i]["appearances"], seasons[cutoff_i]["goals"]
    return [{"h": h, "pred_apps": float(la), "pred_goals": float(lg), "retired": False}
            for h in range(1, max_h + 1)]


def forecast_ageing(rec, cutoff_i, ca, cg, max_h):
    seasons = rec["_ordered"]; by = rec["birth_year"]
    y0 = seasons[cutoff_i]["season_start_year"]
    steps = []
    for h in range(1, max_h + 1):
        age = (y0 + h - by) if by else None
        if age is not None and age > 36:      # fixed-age retirement (the naive rule)
            steps.append({"h": h, "retired": True}); break
        steps.append({"h": h, "retired": False,
                      "pred_apps": clip_apps(ca.get(age, 0.0)),
                      "pred_goals": max(0.0, cg.get(age, 0.0))})
    return steps


def actual_future(rec, cutoff_i, max_h):
    seasons = rec["_ordered"]
    out = []
    for h in range(1, max_h + 1):
        j = cutoff_i + h
        if j < len(seasons):
            out.append({"apps": seasons[j]["appearances"], "goals": seasons[j]["goals"]})
        else:
            out.append(None)      # player did not play this season (retired/censored)
    return out


def horizon_errors(pred_steps, actual, max_h):
    """Per-horizon cumulative appearance/goal absolute error vs actual played."""
    def pa(step):
        return 0.0 if step.get("retired") else step.get("pred_apps", 0.0)

    def pg(step):
        return 0.0 if step.get("retired") else step.get("pred_goals", 0.0)
    pred_by_h = {s["h"]: s for s in pred_steps}
    cum_pred_a = cum_pred_g = cum_act_a = cum_act_g = 0.0
    res = {}
    for h in range(1, max_h + 1):
        s = pred_by_h.get(h, {"retired": True})
        cum_pred_a += pa(s); cum_pred_g += pg(s)
        act = actual[h - 1]
        cum_act_a += (act["apps"] if act else 0.0)
        cum_act_g += (act["goals"] if act else 0.0)
        if h in (1, 3, 5):
            res[h] = {"cum_apps_abs_err": round(abs(cum_pred_a - cum_act_a), 2),
                      "cum_goals_abs_err": round(abs(cum_pred_g - cum_act_g), 2)}
    return res


def main():
    players = DC.load_players()
    from chronology import order_seasons
    for rec in players:
        rec["_ordered"] = [s for s in order_seasons(rec["seasons"]) if s["model_eligible"]]

    # feature frame for training (reuse corrected builder) + residual sd for intervals
    df, _ = DC.build_frame(players)
    sub_apps = df[df["y_next_apps"].notna()]
    resid_sd = float(np.std(sub_apps["y_next_apps"] - sub_apps["cur_apps"]))  # persistence resid

    reg_apps_base = HistGradientBoostingRegressor(random_state=SEED, max_depth=3, learning_rate=0.08)
    reg_goals_base = HistGradientBoostingRegressor(loss="poisson", random_state=SEED, max_depth=3)
    clf_base = HistGradientBoostingClassifier(random_state=SEED, max_depth=3, learning_rate=0.08)

    # 5-fold player-grouped training so a player never trains its own forecast
    pid_index = {rec["player_id"]: k for k, rec in enumerate(players)}
    groups = np.array([pid_index[r] for r in df["player_id"]])
    gkf = GroupKFold(n_splits=5)
    fold_models = {}
    fold_of_player = {}
    for fold, (tr, te) in enumerate(gkf.split(df[FEATURE_COLUMNS], df["y_next_apps"].fillna(0), groups)):
        trdf = df.iloc[tr]
        ra = clone(reg_apps_base).fit(trdf[df["y_next_apps"].notna().values[tr]][FEATURE_COLUMNS]
                                      if False else trdf[trdf["y_next_apps"].notna()][FEATURE_COLUMNS],
                                      trdf[trdf["y_next_apps"].notna()]["y_next_apps"])
        rg = clone(reg_goals_base).fit(trdf[trdf["y_next_goals"].notna()][FEATURE_COLUMNS],
                                       trdf[trdf["y_next_goals"].notna()]["y_next_goals"])
        cf_sub = trdf[trdf["y_continue_next_season"].notna()]
        cf = clone(clf_base).fit(cf_sub[FEATURE_COLUMNS], cf_sub["y_continue_next_season"])
        fold_models[fold] = (ra, rg, cf)
        for p in df.iloc[te]["player_id"].unique():
            fold_of_player[p] = fold

    # cutoffs: retired players with >=4 seasons history and >=1 future; several cutoffs
    results = {"seed": SEED, "apps_cap": APPS_CAP, "resid_sd": round(resid_sd, 2),
               "horizons": [1, 3, 5], "n_trajectories": 0,
               "by_horizon": {}, "by_position": {}, "by_cutoff_age": {},
               "remaining_len_error": {}, "retirement_age_error": {},
               "constraint_checks": {}, "examples": {}}

    err_model = {1: {"a": [], "g": []}, 3: {"a": [], "g": []}, 5: {"a": [], "g": []}}
    err_naive = {1: {"a": [], "g": []}, 3: {"a": [], "g": []}, 5: {"a": [], "g": []}}
    err_pers = {1: {"a": [], "g": []}, 3: {"a": [], "g": []}, 5: {"a": [], "g": []}}
    by_pos = defaultdict(lambda: {1: [], 3: [], 5: []})
    by_age = defaultdict(lambda: {1: [], 3: [], 5: []})
    rem_err, retage_err = [], []
    max_int_width_monotonic = True
    neg_violation = cap_violation = post_retire_violation = 0
    n_traj = 0

    for rec in players:
        seasons = rec["_ordered"]
        n = len(seasons)
        if rec["career_status"] != "retired" or n < 5 or not rec["birth_year"]:
            continue
        ra, rg, cf = fold_models[fold_of_player[rec["player_id"]]]
        ca, cg = build_age_curve(players, rec["player_id"])
        # multiple cutoffs at ~40%, 55%, 70% of career, needing >=1 future season
        for frac in (0.4, 0.55, 0.7):
            c = max(3, int(round(frac * (n - 1))))
            if c >= n - 1:
                continue
            n_traj += 1
            steps = forecast_model(rec, c, ra, rg, cf, 5, resid_sd)
            actual = actual_future(rec, c, 5)
            e_m = horizon_errors(steps, actual, 5)
            e_n = horizon_errors(forecast_ageing(rec, c, ca, cg, 5), actual, 5)
            e_p = horizon_errors(forecast_persistence(rec, c, 5), actual, 5)
            cutoff_age = seasons[c]["season_start_year"] - rec["birth_year"]
            for h in (1, 3, 5):
                if h in e_m:
                    err_model[h]["a"].append(e_m[h]["cum_apps_abs_err"])
                    err_model[h]["g"].append(e_m[h]["cum_goals_abs_err"])
                    err_naive[h]["a"].append(e_n[h]["cum_apps_abs_err"])
                    err_pers[h]["a"].append(e_p[h]["cum_apps_abs_err"])
                    by_pos[rec["coarse_group"]][h].append(e_m[h]["cum_apps_abs_err"])
                    by_age[f"{(cutoff_age//4)*4}-{(cutoff_age//4)*4+3}"][h].append(e_m[h]["cum_apps_abs_err"])
            # remaining career length + retirement age (full hidden future)
            pred_remaining = sum(1 for s in steps if not s.get("retired"))
            actual_remaining = n - 1 - c
            rem_err.append(abs(pred_remaining - actual_remaining))
            pred_retire_age = cutoff_age + pred_remaining + 1
            actual_retire_age = seasons[-1]["season_start_year"] - rec["birth_year"]
            retage_err.append(abs(pred_retire_age - actual_retire_age))
            # constraint checks
            widths = [s.get("interval_width", 0) for s in steps if not s.get("retired")]
            if widths != sorted(widths):
                max_int_width_monotonic = False
            retired_seen = False
            for s in steps:
                if s.get("retired"):
                    retired_seen = True
                else:
                    if retired_seen:
                        post_retire_violation += 1
                    if s["pred_apps"] < 0 or s["pred_goals"] < 0:
                        neg_violation += 1
                    if s["pred_apps"] > APPS_CAP:
                        cap_violation += 1
            if rec["player_id"] in ("radamel-falcao", "wayne-rooney", "paolo-maldini") and frac == 0.55:
                results["examples"][rec["player_id"]] = {
                    "cutoff_age": cutoff_age, "steps": steps,
                    "actual_future": actual}

    def stats(lst):
        return {"n": len(lst), "mae": round(float(np.mean(lst)), 2)} if lst else {"n": 0}
    results["n_trajectories"] = n_traj
    for h in (1, 3, 5):
        results["by_horizon"][h] = {
            "model_cum_apps_mae": stats(err_model[h]["a"]),
            "naive_ageing_cum_apps_mae": stats(err_naive[h]["a"]),
            "persistence_cum_apps_mae": stats(err_pers[h]["a"]),
            "model_cum_goals_mae": stats(err_model[h]["g"]),
        }
    results["by_position"] = {k: {h: stats(v[h]) for h in (1, 3, 5)} for k, v in by_pos.items()}
    results["by_cutoff_age"] = {k: {h: stats(v[h]) for h in (1, 3, 5)} for k, v in sorted(by_age.items())}
    results["remaining_len_error"] = stats(rem_err)
    results["retirement_age_error"] = stats(retage_err)
    results["constraint_checks"] = {
        "negative_count_violations": neg_violation,
        "apps_cap_violations": cap_violation,
        "season_after_retirement_violations": post_retire_violation,
        "interval_width_monotonic_increasing": bool(max_int_width_monotonic),
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _summary(results)
    return results


def _summary(r):
    print(f"\n==== MULTI-SEASON BACKTEST (seed={r['seed']}) ====")
    print(f"trajectories={r['n_trajectories']} apps_cap={r['apps_cap']}")
    for h in (1, 3, 5):
        b = r["by_horizon"][h]
        print(f"  h={h}: model cum-apps MAE={b['model_cum_apps_mae']} | "
              f"naive-ageing={b['naive_ageing_cum_apps_mae']} | persistence={b['persistence_cum_apps_mae']} "
              f"| model cum-goals MAE={b['model_cum_goals_mae']}")
    print(f"  remaining-length error MAE={r['remaining_len_error']}")
    print(f"  retirement-age error MAE={r['retirement_age_error']}")
    print(f"  constraints: {r['constraint_checks']}")


if __name__ == "__main__":
    main()
