"""Corrected one-step evaluation (Phase 2C).

Fixes vs Phase 2B: partial-season target leakage removed; precise continuation
target; player-cluster paired bootstrap; every candidate model reported
independently; time-aware nested model selection (select on validation era,
report on held-out test era); full continuation metrics with player-grouped
calibration (raw / Platt / isotonic) compared to the base-rate Brier.

Writes results_corrected.json.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, cross_val_predict

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evaluate as E                                # noqa: E402
import train as T                                   # noqa: E402
import dataset_corrected as DC                      # noqa: E402
from bootstrap import cluster_paired_bootstrap      # noqa: E402
from baselines import NaivePrevSeason, AgePositionAvg, age_band  # noqa: E402
from features import FEATURE_COLUMNS                 # noqa: E402

OUT = HERE / "results_corrected.json"
SEED = T.SEED
np.random.seed(SEED)


def regressors():
    r = T.make_regressors(SEED)
    r["histgb_poisson"] = HistGradientBoostingRegressor(
        loss="poisson", random_state=SEED, max_depth=3, learning_rate=0.08)
    return r


def time_aware_select(sub, target, models):
    """Fit on early seasons, SELECT best on a validation era, REPORT on a
    held-out later era (honest model selection, no selection-on-test)."""
    yq = sub["season_year"]
    q1, q2 = int(np.quantile(yq, 0.6)), int(np.quantile(yq, 0.8))
    tr = sub[sub.season_year <= q1]
    va = sub[(sub.season_year > q1) & (sub.season_year <= q2)]
    te = sub[sub.season_year > q2]
    if len(va) < 20 or len(te) < 20:
        return None
    Xtr, ytr = tr[FEATURE_COLUMNS], tr[target].to_numpy(float)
    val_mae, test_mae = {}, {}
    for name, est in models.items():
        m = clone(est).fit(Xtr, ytr)
        val_mae[name] = E.mae(va[target].to_numpy(float), np.clip(m.predict(va[FEATURE_COLUMNS]), 0, None))
        test_mae[name] = E.mae(te[target].to_numpy(float), np.clip(m.predict(te[FEATURE_COLUMNS]), 0, None))
    # baselines on val/test
    for bl, cls in (("naive", NaivePrevSeason), ("agepos", AgePositionAvg)):
        b = cls(target).fit(tr)
        val_mae[bl] = E.mae(va[target].to_numpy(float), b.predict(va))
        test_mae[bl] = E.mae(te[target].to_numpy(float), b.predict(te))
    chosen = min((m for m in models), key=lambda m: val_mae[m])
    return {"val_cutoff": q1, "test_cutoff": q2, "n_test": int(len(te)),
            "selected_on_val": chosen,
            "val_mae": {k: round(v, 3) for k, v in val_mae.items()},
            "test_mae": {k: round(v, 3) for k, v in test_mae.items()},
            "selected_test_mae": round(test_mae[chosen], 3),
            "naive_test_mae": round(test_mae["naive"], 3)}


def eval_regression_corrected(df, target, models):
    sub = df[df[target].notna()].reset_index(drop=True)
    y = sub[target].to_numpy(float)
    players = sub["player_id"].to_numpy()
    out = {"n_rows": int(len(sub)), "n_players": int(sub.player_id.nunique()), "lopo": {}}

    oof = {"naive": E.lopo_oof_baseline("naive", sub, target),
           "agepos": E.lopo_oof_baseline("agepos", sub, target)}
    out["lopo"]["naive_mae"] = round(E.mae(y, oof["naive"]), 3)
    out["lopo"]["agepos_mae"] = round(E.mae(y, oof["agepos"]), 3)
    # EVERY model reported independently + cluster-bootstrap vs naive
    out["lopo"]["models"] = {}
    for name, est in models.items():
        pred, _ = E.lopo_oof_model(est, sub, target)
        oof[name] = pred
        boot = cluster_paired_bootstrap(y, pred, oof["naive"], players)
        out["lopo"]["models"][name] = {
            "mae": round(E.mae(y, pred), 3),
            "vs_naive_diff_mean": boot["diff_mean"],
            "vs_naive_diff_ci95": boot["diff_ci95"],
            "p_beats_naive": boot["p_model_beats_base"],
        }
    out["time_aware_selection"] = time_aware_select(sub, target, models)
    return out, sub, oof


def _reliability(p, y, bins=(0, .2, .4, .6, .8, .9, .95, .99, 1.01)):
    out = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() >= 5:
            out.append({"bin": f"[{lo},{hi})", "n": int(m.sum()),
                        "mean_pred": round(float(p[m].mean()), 3),
                        "obs": round(float(y[m].mean()), 3)})
    return out


def _cal_intercept_slope(p, y):
    """Logistic recalibration: fit y ~ logit(p); slope~1 & intercept~0 = good."""
    eps = 1e-6
    logit = np.log(np.clip(p, eps, 1 - eps) / (1 - np.clip(p, eps, 1 - eps)))
    lr = LogisticRegression(C=1e6, solver="lbfgs").fit(logit.reshape(-1, 1), y)
    return round(float(lr.intercept_[0]), 3), round(float(lr.coef_[0][0]), 3)


def eval_continuation_corrected(df, clf, seed=SEED):
    sub = df[df["y_continue_next_season"].notna()].reset_index(drop=True)
    y = sub["y_continue_next_season"].to_numpy(float)      # 1 = continues
    y_ret = 1 - y                                           # retirement event
    players = sub["player_id"].to_numpy()
    X = sub[FEATURE_COLUMNS]

    p_raw = E.lopo_oof_proba(clf, sub, target="y_continue_next_season")
    # player-grouped calibration of the raw OOF probs
    gkf = GroupKFold(n_splits=5)
    platt = cross_val_predict(LogisticRegression(C=1e6),
                              p_raw.reshape(-1, 1), y, cv=gkf, groups=players,
                              method="predict_proba")[:, 1]
    iso = cross_val_predict(IsotonicRegression(out_of_bounds="clip"),
                            p_raw, y, cv=gkf, groups=players)

    base_rate = float(y.mean())
    base_brier = float(np.mean((y - base_rate) ** 2))
    variants = {"raw": p_raw, "platt": platt, "isotonic": iso}
    cal = {}
    for name, p in variants.items():
        inter, slope = _cal_intercept_slope(p, y)
        cal[name] = {"brier": round(float(brier_score_loss(y, p)), 4),
                     "beats_base_rate_brier": bool(brier_score_loss(y, p) < base_brier),
                     "cal_intercept": inter, "cal_slope": slope,
                     "reliability": _reliability(p, y)}

    # retirement detection with the raw model (ranking)
    ap = float(average_precision_score(y_ret, 1 - p_raw))   # PR-AUC for retirement
    auc = float(roc_auc_score(y, p_raw))
    thr_rows = {}
    for thr in (0.5, 0.3, 0.2):
        pred_ret = (p_raw < thr).astype(int)
        cm = confusion_matrix(y_ret, pred_ret, labels=[1, 0]).tolist()  # [[TP,FN],[FP,TN]]
        thr_rows[str(thr)] = {
            "precision_retire": round(float(precision_score(y_ret, pred_ret, zero_division=0)), 3),
            "recall_retire": round(float(recall_score(y_ret, pred_ret, zero_division=0)), 3),
            "confusion_[[TP,FN],[FP,TN]]": cm}

    # by age / position (retirement recall at 0.5)
    d = sub.copy(); d["_ab"] = age_band(d["age"])
    by_age, by_pos = {}, {}
    pred_ret05 = (p_raw < 0.5).astype(int)
    for grp, col, store in ((d["_ab"], "_ab", by_age), (d["coarse_group"], "coarse_group", by_pos)):
        for key, idx in d.groupby(col, observed=True).groups.items():
            ii = [d.index.get_loc(x) for x in idx]
            n_ret = int(y_ret[ii].sum())
            store[str(key)] = {"n": len(ii), "retirements": n_ret,
                               "recall_retire@0.5": round(float(recall_score(
                                   y_ret[ii], pred_ret05[ii], zero_division=0)), 3) if n_ret else None}

    return {
        "n_rows": int(len(sub)), "n_players": int(sub.player_id.nunique()),
        "n_retirement_events": int(y_ret.sum()), "continue_rate": round(base_rate, 4),
        "base_rate_brier": round(base_brier, 4),
        "roc_auc": round(auc, 3), "retirement_pr_auc": round(ap, 3),
        "calibration_variants": cal,
        "thresholds": thr_rows, "by_age": by_age, "by_position": by_pos,
    }


def main():
    players = DC.load_players()
    df, removed = DC.build_frame(players)
    regs = regressors()

    results = {"seed": SEED, "n_players": len(players),
               "n_feature_rows": int(len(df)),
               "leakage_removed_counts": removed,
               "rows_by_target": {t: int(df[t].notna().sum()) for t in DC.CORRECTED_TARGETS},
               "targets": {}}

    for target in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        res, _, _ = eval_regression_corrected(df, target, regs)
        results["targets"][target] = res

    results["targets"]["y_continue_next_season"] = eval_continuation_corrected(
        df, T.make_classifiers(SEED)["histgb_clf"])

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _summary(results)
    return results


def _summary(r):
    print(f"\n==== CORRECTED ONE-STEP EVAL (seed={r['seed']}) ====")
    print(f"players={r['n_players']} feature_rows={r['n_feature_rows']}")
    print("leakage/censoring removed:", r["leakage_removed_counts"])
    print("rows by target:", r["rows_by_target"])
    for t in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        res = r["targets"][t]
        print(f"\n{t}: n={res['n_rows']} naive={res['lopo']['naive_mae']} agepos={res['lopo']['agepos_mae']}")
        for m, v in res["lopo"]["models"].items():
            print(f"   {m:16} MAE={v['mae']:.3f}  vs_naive Δ={v['vs_naive_diff_mean']:+.3f} "
                  f"CI{v['vs_naive_diff_ci95']} P(beats)={v['p_beats_naive']}")
        ts = res.get("time_aware_selection")
        if ts:
            print(f"   time-aware: selected '{ts['selected_on_val']}' -> test MAE "
                  f"{ts['selected_test_mae']} vs naive {ts['naive_test_mae']}")
    c = r["targets"]["y_continue_next_season"]
    print(f"\ny_continue_next_season: rows={c['n_rows']} retirements={c['n_retirement_events']} "
          f"rate={c['continue_rate']}")
    print(f"   ROC-AUC={c['roc_auc']} retirement PR-AUC={c['retirement_pr_auc']} "
          f"base_rate_Brier={c['base_rate_brier']}")
    for name, v in c["calibration_variants"].items():
        print(f"   {name:9} Brier={v['brier']} beats_base={v['beats_base_rate_brier']} "
              f"intercept={v['cal_intercept']} slope={v['cal_slope']}")


if __name__ == "__main__":
    main()
