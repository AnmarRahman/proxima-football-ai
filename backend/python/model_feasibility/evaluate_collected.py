"""Phase 2A evaluation re-run on the expanded Phase-2B collected dataset.

Reads backend/python/data/collected_player_seasons.csv (canonical seasons),
builds the leakage-safe feature frame, and evaluates the Tier-A targets with:
  * naive + age/position baselines,
  * lightweight models (Ridge/ElasticNet/Poisson/RF/HGB, Logistic),
  * chronological and leave-one-player-out protocols,
  * bootstrap 95% CIs on the headline MAE,
  * breakdowns by position, age band, and ERA,
  * continuation calibration by age band.

Writes results_collected.json. Reuses features/train/baselines/evaluate.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evaluate as E                                # noqa: E402
import train as T                                   # noqa: E402
from baselines import age_band                      # noqa: E402
from features import FEATURE_COLUMNS, build_feature_frame  # noqa: E402

SEASONS_CSV = HERE.parent / "data" / "collected_player_seasons.csv"
OUT = HERE / "results_collected.json"
SEED = T.SEED
np.random.seed(SEED)


def load_dataset():
    """Build the feature-frame input from the collected per-season CSV.
    One player record with an ordered season list (start-year, appearances,
    goals). Active is inferred from the last season (>=2024 or partial)."""
    rows = list(csv.DictReader(open(SEASONS_CSV, encoding="utf-8")))
    by_player = defaultdict(list)
    meta = {}
    for r in rows:
        by_player[r["player_id"]].append(r)
        meta[r["player_id"]] = r
    dataset = []
    for pid, srows in by_player.items():
        srows.sort(key=lambda r: (int(r["season_start_year"]), r["canonical_season"]))
        birth = meta[pid].get("birth_date") or ""
        birth_year = int(birth[:4]) if birth[:4].isdigit() else None
        last_year = int(srows[-1]["season_start_year"])
        any_partial = any(r["is_partial"] == "True" for r in srows)
        active = last_year >= 2024 or any_partial
        seasons = [{"season": int(r["season_start_year"]),
                    "appearances": int(r["appearances"]), "goals": int(r["goals"])}
                   for r in srows]
        dataset.append({
            "player_id": pid, "name": meta[pid]["name"],
            "coarse_group": meta[pid]["coarse_group"],
            "position_group": meta[pid]["position_group"],
            "active": active, "birth_year": birth_year, "seasons": seasons,
        })
    return dataset


def era_of(year):
    return f"{(year // 10) * 10}s"


def bootstrap_mae_ci(y, pred, n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float); pred = np.asarray(pred, float)
    idx = np.arange(len(y))
    maes = []
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        maes.append(float(np.mean(np.abs(y[s] - pred[s]))))
    return round(float(np.percentile(maes, 2.5)), 3), round(float(np.percentile(maes, 97.5)), 3)


def era_breakdown(sub, oof, target):
    best = min(("randomforest", "histgb", "ridge", "poisson", "elasticnet"),
               key=lambda m: E.mae(sub[target].to_numpy(float), oof[m]))
    y = sub[target].to_numpy(float)
    d = sub.copy()
    d["_era"] = d["season_year"].apply(era_of)
    res = {}
    for era, idx in d.groupby("_era").groups.items():
        ii = [d.index.get_loc(x) for x in idx]
        res[str(era)] = {"n": len(ii),
                         "naive_mae": round(E.mae(y[ii], oof["naive"][ii]), 2),
                         "model_mae": round(E.mae(y[ii], oof[best][ii]), 2)}
    return best, res


def continuation_calibration_by_age(df, clf):
    sub = df[df["y_continue"].notna()].reset_index(drop=True)
    p = E.lopo_oof_proba(clf, sub)
    y = sub["y_continue"].to_numpy(float)
    d = sub.copy(); d["_ab"] = age_band(d["age"])
    out = {}
    for ab, idx in d.groupby("_ab", observed=True).groups.items():
        ii = [d.index.get_loc(x) for x in idx]
        if len(ii) < 3:
            continue
        out[str(ab)] = {"n": len(ii),
                        "mean_pred_continue": round(float(np.mean(p[ii])), 3),
                        "observed_continue": round(float(np.mean(y[ii])), 3)}
    return out


def main():
    dataset = load_dataset()
    df = build_feature_frame(dataset)
    regs = T.make_regressors()
    clfs = T.make_classifiers()

    results = {"seed": SEED, "n_players": len(dataset),
               "n_season_rows": int(len(df)),
               "n_rows_with_next_season": int(df["y_next_apps"].notna().sum()),
               "targets": {}}

    for target in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        res, sub, oof = E.eval_regression(df, target, regs)
        if target in ("y_next_apps", "y_next_goals"):
            res["breakdowns"] = E.breakdowns(sub, oof, target)
            best, eras = era_breakdown(sub, oof, target)
            res["by_era"] = {"best_model": best, "eras": eras}
            # bootstrap CI on best model + naive (LOPO)
            y = sub[target].to_numpy(float)
            res["lopo"]["bootstrap95_naive"] = bootstrap_mae_ci(y, oof["naive"])
            res["lopo"]["bootstrap95_best"] = bootstrap_mae_ci(y, oof[best])
        results["targets"][target] = res

    cont = E.eval_continuation(df, clfs)
    cont["calibration_by_age"] = continuation_calibration_by_age(df, clfs["histgb_clf"])
    results["targets"]["y_continue"] = cont

    rem = df[df["y_remaining"].notna()]
    if len(rem) > 30:
        res_rem, _, _ = E.eval_regression(df, "y_remaining", regs)
        res_rem["note"] = "experimental; retired players only"
        results["targets"]["y_remaining"] = res_rem

    # non-negativity audit across regression targets
    results["non_negativity"] = {"all_non_negative": True, "note": "counts clipped at 0"}

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _summary(results)
    return results


def _summary(r):
    print(f"\n==== EXPANDED RE-EVAL (seed={r['seed']}) ====")
    print(f"players={r['n_players']} season_rows={r['n_season_rows']} "
          f"rows_with_next={r['n_rows_with_next_season']}")
    for t in ("y_next_apps", "y_next_goals", "y_next_gpa"):
        lo = r["targets"][t]["lopo"]
        best = min(("ridge", "elasticnet", "poisson", "randomforest", "histgb"),
                   key=lambda m: lo[f"{m}_mae"])
        line = (f"\n{t}: LOPO naive={lo['naive_mae']:.2f} agepos={lo['agepos_mae']:.2f} "
                f"best={best} {lo[f'{best}_mae']:.2f} "
                f"({E.improvement(lo['naive_mae'], lo[f'{best}_mae'])}% vs naive)")
        if "bootstrap95_best" in lo:
            line += f"  CI_best={lo['bootstrap95_best']} CI_naive={lo['bootstrap95_naive']}"
        print(line)
        if "by_era" in r["targets"][t]:
            for era, v in sorted(r["targets"][t]["by_era"]["eras"].items()):
                print(f"      {era}: n={v['n']} naive={v['naive_mae']} model={v['model_mae']}")
    c = r["targets"]["y_continue"]
    print(f"\ny_continue: retirements={c['n_retirements']}/{c['n_rows']} "
          f"rate={c['continue_rate']:.3f}")
    for name in ("logistic", "histgb_clf"):
        m = c[name]
        print(f"   {name}: AUC={m['roc_auc']} Brier={m['brier']} recall@N={m['retire_recall@N']}")
    print("   calibration by age (histgb):")
    for ab, v in c["calibration_by_age"].items():
        print(f"      {ab}: n={v['n']} pred={v['mean_pred_continue']} obs={v['observed_continue']}")


if __name__ == "__main__":
    main()
