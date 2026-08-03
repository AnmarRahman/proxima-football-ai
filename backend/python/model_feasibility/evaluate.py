"""Evaluate Tier-A feasibility models against mandatory baselines.

Protocols:
  * Chronological hold-out: train earlier seasons, validate later seasons.
  * Leave-one-player-out (LOPO): a player's rows never span train and test.
Both fit baselines on the same training data for a fair comparison. Count
predictions are clipped to be non-negative. Fixed seed for reproducibility.

Outputs model_feasibility/results.json and prints a summary.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (brier_score_loss, mean_absolute_error,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import LeaveOneGroupOut

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train as T                                    # noqa: E402
from baselines import AgePositionAvg, BaseRate, NaivePrevSeason, age_band  # noqa: E402
from features import FEATURE_COLUMNS, build_feature_frame  # noqa: E402

DATA = HERE.parent / "data" / "acquisition" / "model_feasibility_data" / "_dataset.json"
SEED = T.SEED
np.random.seed(SEED)


def clip0(a):
    return np.clip(np.asarray(a, dtype=float), 0, None)


def mae(y, p):
    return float(mean_absolute_error(y, p))


def improvement(base, model):
    return round(100.0 * (base - model) / base, 1) if base else 0.0


# ----------------------------------------------------------------------------
# LOPO out-of-fold predictions
# ----------------------------------------------------------------------------
def lopo_oof_model(estimator, sub, target):
    X = sub[FEATURE_COLUMNS]
    y = sub[target].to_numpy(dtype=float)
    groups = sub["player_id"].to_numpy()
    oof = np.full(len(sub), np.nan)
    raw_min = np.inf
    for tr, te in LeaveOneGroupOut().split(X, y, groups):
        est = clone(estimator)
        est.fit(X.iloc[tr], y[tr])
        pred = np.asarray(est.predict(X.iloc[te]), dtype=float)
        raw_min = min(raw_min, float(np.min(pred)))
        oof[te] = clip0(pred)
    return oof, raw_min


def lopo_oof_baseline(kind, sub, target):
    oof = np.full(len(sub), np.nan)
    y = sub[target]
    groups = sub["player_id"].to_numpy()
    for tr, te in LeaveOneGroupOut().split(sub, y, groups):
        tr_df, te_df = sub.iloc[tr], sub.iloc[te]
        b = (NaivePrevSeason(target) if kind == "naive" else AgePositionAvg(target)).fit(tr_df)
        oof[te] = b.predict(te_df)
    return oof


def lopo_oof_proba(clf, sub, target="y_continue"):
    X = sub[FEATURE_COLUMNS]
    y = sub[target].to_numpy(dtype=float)
    groups = sub["player_id"].to_numpy()
    oof = np.full(len(sub), np.nan)
    for tr, te in LeaveOneGroupOut().split(X, y, groups):
        est = clone(clf)
        est.fit(X.iloc[tr], y[tr])
        oof[te] = est.predict_proba(X.iloc[te])[:, 1]
    return oof


# ----------------------------------------------------------------------------
# Chronological split
# ----------------------------------------------------------------------------
def chrono_split(sub, q=0.70):
    cutoff = int(np.quantile(sub["season_year"], q))
    tr = sub[sub["season_year"] <= cutoff]
    te = sub[sub["season_year"] > cutoff]
    return tr, te, cutoff


def eval_regression(df, target, models):
    sub = df[df[target].notna()].reset_index(drop=True)
    out = {"n_rows": int(len(sub)), "chronological": {}, "lopo": {}}
    use_naive = target in NaivePrevSeason.COL   # persistence only for apps/goals/gpa

    # --- chronological ---
    tr, te, cutoff = chrono_split(sub)
    out["chronological"]["cutoff_season"] = cutoff
    out["chronological"]["n_train"] = int(len(tr))
    out["chronological"]["n_test"] = int(len(te))
    yte = te[target].to_numpy(dtype=float)
    if use_naive:
        out["chronological"]["naive_mae"] = mae(yte, NaivePrevSeason(target).fit(tr).predict(te))
    out["chronological"]["agepos_mae"] = mae(yte, AgePositionAvg(target).fit(tr).predict(te))
    Xtr, Xte = tr[FEATURE_COLUMNS], te[FEATURE_COLUMNS]
    ytr = tr[target].to_numpy(dtype=float)
    for name, est in models.items():
        m = clone(est).fit(Xtr, ytr)
        out["chronological"][f"{name}_mae"] = mae(yte, clip0(m.predict(Xte)))

    # --- LOPO ---
    y = sub[target].to_numpy(dtype=float)
    oof_store = {}
    oof_store["agepos"] = lopo_oof_baseline("agepos", sub, target)
    out["lopo"]["agepos_mae"] = mae(y, oof_store["agepos"])
    if use_naive:
        oof_store["naive"] = lopo_oof_baseline("naive", sub, target)
        out["lopo"]["naive_mae"] = mae(y, oof_store["naive"])
    raw_mins = {}
    for name, est in models.items():
        oof, raw_min = lopo_oof_model(est, sub, target)
        out["lopo"][f"{name}_mae"] = mae(y, oof)
        oof_store[name] = oof
        raw_mins[name] = raw_min
    out["lopo"]["raw_min_prediction_before_clip"] = raw_mins
    baseline_key = "naive_mae" if use_naive else "agepos_mae"
    out["lopo"]["best_model_vs_baseline_pct"] = improvement(
        out["lopo"][baseline_key], min(out["lopo"][f"{m}_mae"] for m in models))
    return out, sub, oof_store


def eval_continuation(df, classifiers):
    sub = df[df["y_continue"].notna()].reset_index(drop=True)
    y = sub["y_continue"].to_numpy(dtype=float)      # 1 = continues
    y_ret = 1.0 - y                                   # 1 = retires (rare)
    out = {"n_rows": int(len(sub)), "n_retirements": int(y_ret.sum()),
           "continue_rate": float(y.mean())}

    base = BaseRate().fit(sub).predict_proba(sub)
    out["baseline_baserate_brier"] = float(brier_score_loss(y, base))

    for name, clf in classifiers.items():
        p = lopo_oof_proba(clf, sub)
        auc = float(roc_auc_score(y, p))               # ranking of continuation
        brier = float(brier_score_loss(y, p))
        # retirement detection at 0.5 and at precision@N (N = #retirements)
        pred_ret_05 = (p < 0.5).astype(int)
        prec05 = float(precision_score(y_ret, pred_ret_05, zero_division=0))
        rec05 = float(recall_score(y_ret, pred_ret_05, zero_division=0))
        N = int(y_ret.sum())
        order = np.argsort(p)                           # lowest continue prob first
        flagged = np.zeros_like(y_ret); flagged[order[:N]] = 1
        prec_at_n = float(precision_score(y_ret, flagged, zero_division=0))
        rec_at_n = float(recall_score(y_ret, flagged, zero_division=0))
        # calibration bins (predicted continue vs observed)
        bins = pd.cut(p, bins=[0, 0.5, 0.7, 0.85, 0.95, 1.01], include_lowest=True)
        cal = []
        for b, idx in pd.Series(range(len(p))).groupby(bins, observed=True):
            ii = idx.to_numpy()
            cal.append({"bin": str(b), "n": int(len(ii)),
                        "mean_pred": round(float(np.mean(p[ii])), 3),
                        "obs_continue": round(float(np.mean(y[ii])), 3)})
        out[name] = {"roc_auc": round(auc, 3), "brier": round(brier, 4),
                     "retire_precision@0.5": round(prec05, 3),
                     "retire_recall@0.5": round(rec05, 3),
                     "retire_precision@N": round(prec_at_n, 3),
                     "retire_recall@N": round(rec_at_n, 3),
                     "calibration": cal}
    return out


def breakdowns(sub, oof, target):
    """MAE by coarse position group and age band for the best model + naive."""
    best = min(("randomforest", "histgb", "ridge", "poisson", "elasticnet"),
               key=lambda m: mae(sub[target].to_numpy(float), oof[m]))
    y = sub[target].to_numpy(dtype=float)
    d = sub.copy()
    d["_ab"] = age_band(d["age"])
    res = {"best_model": best, "by_position": {}, "by_age": {}}
    for g, idx in d.groupby("coarse_group", observed=True).groups.items():
        ii = [d.index.get_loc(x) for x in idx]
        res["by_position"][g] = {"n": len(ii),
                                 "naive_mae": round(mae(y[ii], oof["naive"][ii]), 2),
                                 "model_mae": round(mae(y[ii], oof[best][ii]), 2)}
    for ab, idx in d.groupby("_ab", observed=True).groups.items():
        ii = [d.index.get_loc(x) for x in idx]
        if not ii:
            continue
        res["by_age"][str(ab)] = {"n": len(ii),
                                  "naive_mae": round(mae(y[ii], oof["naive"][ii]), 2),
                                  "model_mae": round(mae(y[ii], oof[best][ii]), 2)}
    return res


def quantile_intervals(df, target="y_next_apps"):
    sub = df[df[target].notna()].reset_index(drop=True)
    y = sub[target].to_numpy(dtype=float)
    qr = T.make_quantile_regressors()
    q10, _ = lopo_oof_model(qr["q10"], sub, target)
    q90, _ = lopo_oof_model(qr["q90"], sub, target)
    lo = np.minimum(q10, q90); hi = np.maximum(q10, q90)
    coverage = float(np.mean((y >= lo) & (y <= hi)))
    return {"target": target, "coverage_80pct_interval": round(coverage, 3),
            "mean_interval_width": round(float(np.mean(hi - lo)), 1)}


def example_trajectories(df, sub, oof, target, players):
    out = {}
    for pid in players:
        rows = sub[sub["player_id"] == pid]
        traj = []
        for pos, (_, r) in zip(rows.index, rows.iterrows()):
            loc = sub.index.get_loc(pos)
            traj.append({"season": int(r["season_year"]), "age": int(r["age"]),
                         "actual": round(float(r[target]), 1),
                         "pred_histgb": round(float(oof["histgb"][loc]), 1),
                         "pred_naive": round(float(oof["naive"][loc]), 1)})
        out[pid] = traj
    return out


def main():
    dataset = json.loads(DATA.read_text(encoding="utf-8"))
    df = build_feature_frame(dataset)
    regs = T.make_regressors()
    clfs = T.make_classifiers()

    results = {"seed": SEED, "n_players": len(dataset),
               "n_season_rows": int(len(df)),
               "n_rows_with_next_season": int(df["y_next_apps"].notna().sum()),
               "targets": {}}

    reg_oof = {}
    reg_sub = {}
    for target in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        res, sub, oof = eval_regression(df, target, regs)
        if target in ("y_next_apps", "y_next_goals"):
            res["breakdowns"] = breakdowns(sub, oof, target)
        results["targets"][target] = res
        reg_oof[target] = oof; reg_sub[target] = sub

    results["targets"]["y_continue"] = eval_continuation(df, clfs)

    # remaining-career (experimental; retired players only)
    rem = df[df["y_remaining"].notna()].reset_index(drop=True)
    if len(rem) > 30:
        res_rem, _, _ = eval_regression(df, "y_remaining", regs)
        res_rem["note"] = "experimental; retired players only (active players censored)"
        results["targets"]["y_remaining"] = res_rem

    results["quantile_intervals"] = quantile_intervals(df)
    results["example_trajectories_next_apps"] = example_trajectories(
        df, reg_sub["y_next_apps"], reg_oof["y_next_apps"], "y_next_apps",
        ["van-basten", "modric", "haaland"])

    # non-negativity audit
    all_min = min(min(v.min() for v in reg_oof[t].values()) for t in reg_oof)
    results["non_negativity"] = {
        "min_prediction_after_clip": round(float(all_min), 3),
        "all_non_negative": bool(all_min >= 0),
        "note": "linear models can emit negatives; clipped to 0 in post-processing.",
    }

    (HERE / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    _print_summary(results)
    return results


def _print_summary(r):
    print(f"\n==== TIER-A FEASIBILITY (seed={r['seed']}) ====")
    print(f"players={r['n_players']} season_rows={r['n_season_rows']} "
          f"rows_with_next={r['n_rows_with_next_season']}")
    for t in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        res = r["targets"][t]
        lo = res["lopo"]
        best = min(("ridge", "elasticnet", "poisson", "randomforest", "histgb"),
                   key=lambda m: lo[f"{m}_mae"])
        print(f"\n{t}: LOPO naive_MAE={lo['naive_mae']:.2f} agepos_MAE={lo['agepos_mae']:.2f} "
              f"| best={best} MAE={lo[f'{best}_mae']:.2f} "
              f"(vs naive {improvement(lo['naive_mae'], lo[f'{best}_mae'])}%)")
    c = r["targets"]["y_continue"]
    print(f"\ny_continue: retirements={c['n_retirements']}/{c['n_rows']} "
          f"continue_rate={c['continue_rate']:.3f}")
    for name in ("logistic", "histgb_clf"):
        m = c[name]
        print(f"   {name}: AUC={m['roc_auc']} Brier={m['brier']} "
              f"retire_recall@N={m['retire_recall@N']} prec@N={m['retire_precision@N']}")
    print(f"\nnon-negative after clip: {r['non_negativity']['all_non_negative']} "
          f"(min={r['non_negativity']['min_prediction_after_clip']})")
    print(f"80% interval coverage (next_apps): {r['quantile_intervals']['coverage_80pct_interval']}")


if __name__ == "__main__":
    main()
