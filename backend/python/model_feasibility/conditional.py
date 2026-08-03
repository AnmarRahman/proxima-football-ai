"""Conditional (group-valid) conformal prediction intervals.

The global interval is not conditionally valid (it under-covers forwards / high
scorers and over-covers defenders). This module compares several conditional
methods inside the nested player-grouped outer evaluation and produces a
DEPLOYABLE calibrator that keys only on information available at inference time
(position, age, and the model's point prediction — never a future actual).

Methods:
  A global               absolute-residual conformal (marginal only)
  B mondrian_pos         per-coarse-position conformal
  C scaled               scale s(pred)=sqrt(max(pred,0)+1); |resid|/s conformal
  D mondrian_pos_scaled  per-position conformal on scaled residuals
  E cqr                  conformalized quantile regression (HGB quantile), evaluated

Deployed methods are A-D (compact params + a documented scale). E is evaluated
for comparison. Selection uses an INNER evaluation with predetermined criteria
so the outer-fold results used for final reporting are never used to select.
"""

from collections import Counter

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

DEPLOYABLE = ["global", "mondrian_pos", "scaled", "mondrian_pos_scaled"]
ALL_METHODS = DEPLOYABLE + ["cqr"]
POSITIONS = ["DEF", "MID", "WIDE", "FWD"]
AGE_BANDS = [("<=21", -np.inf, 21), ("22-25", 22, 25), ("26-29", 26, 29),
             ("30-33", 30, 33), ("34+", 34, np.inf)]
GOAL_BANDS = [("0-2", 0, 2), ("3-7", 3, 7), ("8-15", 8, 15), ("16+", 16, np.inf)]
APP_BANDS = [("0-15", 0, 15), ("16-25", 16, 25), ("26-34", 26, 34), ("35+", 35, np.inf)]
MIN_CAL = 40


def scale_fn(pred):
    return np.sqrt(np.maximum(np.asarray(pred, float), 0) + 1.0)


def finite_q(scores, alpha, min_n=MIN_CAL):
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    if n < min_n:
        return None
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float(s[min(k, n) - 1])


def band_label(value, bands):
    for name, lo, hi in bands:
        if lo <= value <= hi:
            return name
    return bands[-1][0]


# ---- deployable param-based calibrator (methods A-D) ----------------------
def build_params(method, pred, y, pos, alpha, cap):
    scaled = "scaled" in method
    mondrian = "mondrian" in method
    resid = np.abs(np.asarray(y, float) - np.asarray(pred, float))
    if scaled:
        resid = resid / scale_fn(pred)
    params = {"method": method, "scaled": scaled, "mondrian": mondrian,
              "cap": cap, "global_q": finite_q(resid, alpha),
              "position_q": {}, "min_calibration_sample": MIN_CAL}
    if mondrian:
        pos = np.asarray(pos)
        for p in POSITIONS:
            m = pos == p
            params["position_q"][p] = finite_q(resid[m], alpha) if m.sum() else None
    return params


def apply_interval(params, pred, pos):
    q = None
    if params["mondrian"]:
        q = params["position_q"].get(pos)
    if q is None:
        q = params["global_q"]         # fallback
    if q is None:
        return None
    s = float(scale_fn(pred)) if params["scaled"] else 1.0
    lo = max(0.0, pred - q * s)
    hi = pred + q * s
    if params["cap"] is not None:
        hi = min(params["cap"], hi)
    return lo, hi


# ---- nested evaluation (per conditional group) ----------------------------
def _accumulate(store, key, covered, width):
    d = store.setdefault(key, {"cov": [], "w": []})
    d["cov"].append(covered); d["w"].append(width)


def _fit_predict_interval(method, model, Xp, yp, Xc, yc, posc, Xt, alpha, cap):
    """Return (pred_test, lo, hi) for a fold. Params methods vs cqr."""
    if method == "cqr":
        qlo = HistGradientBoostingRegressor(loss="quantile", quantile=alpha / 2,
                                            random_state=42, max_depth=3).fit(Xp, yp)
        qhi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - alpha / 2,
                                            random_state=42, max_depth=3).fit(Xp, yp)
        lo_c = qlo.predict(Xc); hi_c = qhi.predict(Xc)
        E = np.maximum(lo_c - yc, yc - hi_c)
        Q = finite_q(E, alpha) or 0.0
        pred_t = np.clip(model.predict(Xt), 0, cap)
        lo = np.clip(qlo.predict(Xt) - Q, 0, None)
        hi = qhi.predict(Xt) + Q
        if cap is not None:
            hi = np.clip(hi, 0, cap)
        return pred_t, lo, hi
    pred_c = np.clip(model.predict(Xc), 0, cap)
    params = build_params(method, pred_c, yc, posc, alpha, cap)
    pred_t = np.clip(model.predict(Xt), 0, cap)
    los, his = [], []
    # for eval we need position per test row -> caller supplies via closure
    return pred_t, params


def nested_eval(estimator, sub, feature_cols, target_col, method, cap, alpha,
                target_kind, seed=42, n_outer=5):
    X = sub[feature_cols]; y = sub[target_col].to_numpy(float)
    groups = sub["player_id"].to_numpy(); pos = sub["coarse_group"].to_numpy()
    ages = sub["age"].to_numpy(float)
    bands = GOAL_BANDS if target_kind == "goals" else APP_BANDS

    by = {}
    for tr, te in GroupKFold(n_outer).split(X, y, groups):
        gss = GroupShuffleSplit(1, test_size=0.3, random_state=seed)
        pt, cal = next(gss.split(X.iloc[tr], y[tr], groups[tr]))
        proper, calib = tr[pt], tr[cal]
        model = clone(estimator).fit(X.iloc[proper], y[proper])
        if method == "cqr":
            pt_pred, lo, hi = _fit_predict_interval("cqr", model, X.iloc[proper], y[proper],
                                                    X.iloc[calib], y[calib], pos[calib],
                                                    X.iloc[te], alpha, cap)
        else:
            pred_c = np.clip(model.predict(X.iloc[calib]), 0, cap)
            params = build_params(method, pred_c, y[calib], pos[calib], alpha, cap)
            pt_pred = np.clip(model.predict(X.iloc[te]), 0, cap)
            lo = np.empty(len(te)); hi = np.empty(len(te))
            for j, idx in enumerate(te):
                iv = apply_interval(params, pt_pred[j], pos[idx])
                lo[j], hi[j] = (iv if iv else (np.nan, np.nan))
        yt = y[te]
        covered = ((yt >= lo) & (yt <= hi)).astype(float)
        width = hi - lo
        for j, idx in enumerate(te):
            if not np.isfinite(lo[j]):
                continue
            _accumulate(by, "overall", covered[j], width[j])
            _accumulate(by, f"pos:{pos[idx]}", covered[j], width[j])
            _accumulate(by, f"age:{band_label(ages[idx], AGE_BANDS)}", covered[j], width[j])
            _accumulate(by, f"predband:{band_label(pt_pred[j], bands)}", covered[j], width[j])

    def summ(d):
        cov = np.array(d["cov"]); w = np.array(d["w"])
        return {"n": int(len(cov)), "coverage": round(float(cov.mean()), 3),
                "mean_width": round(float(w.mean()), 2), "median_width": round(float(np.median(w)), 2)}
    return {k: summ(v) for k, v in by.items()}


# ---- acceptance criteria --------------------------------------------------
def acceptance(report, target_kind):
    def cov(k):
        return report.get(k, {}).get("coverage")
    checks = {"overall_0.75_0.87": (cov("overall") is not None and 0.75 <= cov("overall") <= 0.87)}
    for p in POSITIONS:
        checks[f"pos_{p}_ge_0.70"] = (cov(f"pos:{p}") is None) or (cov(f"pos:{p}") >= 0.70)
    if target_kind == "goals":
        checks["FWD_ge_0.70"] = (cov("pos:FWD") is None) or (cov("pos:FWD") >= 0.70)
        checks["WIDE_ge_0.70"] = (cov("pos:WIDE") is None) or (cov("pos:WIDE") >= 0.70)
        checks["highgoal_16+_ge_0.70"] = (cov("predband:16+") is None) or (cov("predband:16+") >= 0.70)
    else:
        checks["age34+_ge_0.70"] = (cov("age:34+") is None) or (cov("age:34+") >= 0.70)
        checks["highapp_35+_ge_0.70"] = (cov("predband:35+") is None) or (cov("predband:35+") >= 0.70)
    checks["_n_pass"] = sum(1 for k, v in checks.items() if not k.startswith("_") and v)
    checks["_all_pass"] = all(v for k, v in checks.items() if not k.startswith("_"))
    return checks


def select_method(estimator, sub, feature_cols, target_col, cap, alpha, target_kind, seed=7):
    """INNER selection (a DIFFERENT seed than final reporting). Predetermined
    criterion: the SIMPLEST method (in DEPLOYABLE complexity order) that meets
    every acceptance criterion on inner folds; if none fully pass, the earliest
    method with the most criteria passed. Selection never touches the outer-test
    seed used for final reporting."""
    scored = []
    for method in DEPLOYABLE:                          # complexity order
        rep = nested_eval(estimator, sub, feature_cols, target_col, method, cap, alpha,
                          target_kind, seed=seed, n_outer=5)
        acc = acceptance(rep, target_kind)
        scored.append((method, acc))
        if acc["_all_pass"]:
            return method                              # simplest fully-passing method
    max_pass = max(a["_n_pass"] for _, a in scored)
    for method, acc in scored:                         # earliest with most passes
        if acc["_n_pass"] == max_pass:
            return method


def build_deployed(estimator, sub, feature_cols, target_col, method, cap, alpha,
                   target_kind, seed=42, n_folds=5):
    """Deployed params from grouped cross-conformal residuals over the full data,
    plus suppressed groups from the honest outer evaluation."""
    X = sub[feature_cols]; y = sub[target_col].to_numpy(float)
    groups = sub["player_id"].to_numpy(); pos = sub["coarse_group"].to_numpy()
    oof = np.full(len(sub), np.nan)
    for tr, te in GroupKFold(n_folds).split(X, y, groups):
        m = clone(estimator).fit(X.iloc[tr], y[tr])
        oof[te] = np.clip(m.predict(X.iloc[te]), 0, cap)
    params = build_params(method, oof, y, pos, alpha, cap)

    outer = nested_eval(estimator, sub, feature_cols, target_col, method, cap, alpha,
                        target_kind, seed=seed, n_outer=n_folds)
    suppressed_pos = [p for p in POSITIONS
                      if outer.get(f"pos:{p}") and outer[f"pos:{p}"]["coverage"] < 0.70]
    bands = GOAL_BANDS if target_kind == "goals" else APP_BANDS
    suppressed_bands = [b[0] for b in bands
                        if outer.get(f"predband:{b[0]}") and outer[f"predband:{b[0]}"]["coverage"] < 0.70]
    params.update({
        "nominal_coverage": 1 - alpha,
        "scale_formula": "sqrt(max(pred,0)+1)" if params["scaled"] else None,
        "target_kind": target_kind,
        "fallback_hierarchy": ["position", "global"] if params["mondrian"] else ["global"],
        "suppressed_positions": suppressed_pos,
        "suppressed_pred_bands": suppressed_bands,
        "outer_holdout": outer,
        "acceptance": acceptance(outer, target_kind),
    })
    return params


def runtime_interval(params, pred, pos):
    """Inference-time interval using only position + point prediction. Returns
    (lo, hi) or None with a reason."""
    bands = GOAL_BANDS if params["target_kind"] == "goals" else APP_BANDS
    if pos in params.get("suppressed_positions", []):
        return None, f"interval suppressed for position {pos} (insufficient conditional coverage)"
    band = band_label(pred, bands)
    if band in params.get("suppressed_pred_bands", []):
        return None, f"interval suppressed for predicted band {band} (insufficient conditional coverage)"
    iv = apply_interval(params, pred, pos)
    if iv is None:
        return None, "Insufficient conditional calibration"
    return iv, None


# ==========================================================================
# FULLY NESTED interval POLICY (3A.3)
# A "policy" (method + suppression + calibration) is learned ONLY from the data
# passed to learn_policy. In nested_policy_eval that data is the outer-training
# fold, so the outer-test fold never influences method selection, suppression,
# fallback, thresholds, or calibration.
# ==========================================================================
def _select_from_reports(reports, target_kind):
    """Predetermined rule: simplest method (complexity order) that fully passes
    inner acceptance; else the most criteria passed; ties -> narrower width ->
    simpler method."""
    scored = [(m, acceptance(reports[m], target_kind), reports[m]["overall"]["mean_width"])
              for m in DEPLOYABLE]
    for m, acc, _ in scored:
        if acc["_all_pass"]:
            return m
    max_pass = max(a["_n_pass"] for _, a, _ in scored)
    cands = [(m, w) for m, a, w in scored if a["_n_pass"] == max_pass]
    cands.sort(key=lambda t: (t[1], DEPLOYABLE.index(t[0])))
    return cands[0][0]


def learn_policy(estimator, sub_train, feature_cols, target_col, cap, alpha,
                 target_kind, seed=42, n_inner=4):
    """Learn a FROZEN interval policy from `sub_train` only: inner player-grouped
    CV picks the method and its suppression; calibration q's come from grouped
    OOF residuals over `sub_train`. Returns a runtime-ready params dict."""
    reports = {m: nested_eval(estimator, sub_train, feature_cols, target_col, m, cap,
                              alpha, target_kind, seed=seed, n_outer=n_inner)
               for m in DEPLOYABLE}
    selected = _select_from_reports(reports, target_kind)
    rep = reports[selected]
    supp_pos = [p for p in POSITIONS
                if rep.get(f"pos:{p}") and (rep[f"pos:{p}"]["coverage"] < 0.70
                                            or rep[f"pos:{p}"]["n"] < MIN_CAL)]
    bands = GOAL_BANDS if target_kind == "goals" else APP_BANDS
    supp_band = [b[0] for b in bands
                 if rep.get(f"predband:{b[0]}") and (rep[f"predband:{b[0]}"]["coverage"] < 0.70
                                                     or rep[f"predband:{b[0]}"]["n"] < MIN_CAL)]
    X = sub_train[feature_cols]; y = sub_train[target_col].to_numpy(float)
    groups = sub_train["player_id"].to_numpy(); pos = sub_train["coarse_group"].to_numpy()
    oof = np.full(len(sub_train), np.nan)
    for tr, te in GroupKFold(n_inner).split(X, y, groups):
        m = clone(estimator).fit(X.iloc[tr], y[tr])
        oof[te] = np.clip(m.predict(X.iloc[te]), 0, cap)
    params = build_params(selected, oof, y, pos, alpha, cap)
    params.update({
        "target_kind": target_kind, "nominal_coverage": 1 - alpha,
        "scale_formula": "sqrt(max(pred,0)+1)" if params["scaled"] else None,
        "fallback_hierarchy": ["position", "global"] if params["mondrian"] else ["global"],
        "suppressed_positions": supp_pos, "suppressed_pred_bands": supp_band,
        "inner_selection": {m: {"n_pass": acceptance(reports[m], target_kind)["_n_pass"],
                                "all_pass": acceptance(reports[m], target_kind)["_all_pass"]}
                            for m in DEPLOYABLE},
    })
    return params


def _agg_records(records, target_kind):
    bands = GOAL_BANDS if target_kind == "goals" else APP_BANDS

    def stats(rs):
        n = len(rs); em = [r for r in rs if r["emitted"]]
        cov = np.mean([r["cov"] for r in em]) if em else None
        return {"n": n, "n_emitted": len(em),
                "emission_rate": round(len(em) / n, 3) if n else None,
                "coverage_when_emitted": round(float(cov), 3) if cov is not None else None,
                "mean_width_when_emitted": round(float(np.mean([r["width"] for r in em])), 2) if em else None,
                "median_width_when_emitted": round(float(np.median([r["width"] for r in em])), 2) if em else None}
    out = {"overall": stats(records), "by_position": {}, "by_age": {}, "by_pred_band": {}}
    for p in POSITIONS:
        out["by_position"][p] = stats([r for r in records if r["pos"] == p])
    for ab, _, _ in AGE_BANDS:
        out["by_age"][ab] = stats([r for r in records if r["age_band"] == ab])
    for b in bands:
        out["by_pred_band"][b[0]] = stats([r for r in records if r["pred_band"] == b[0]])
    supp = [r for r in records if not r["emitted"]]
    out["suppression_rate"] = round(len(supp) / len(records), 3) if records else None
    out["suppression_reasons"] = dict(Counter(r["reason"] for r in supp))
    out["point_mae_all_rows"] = round(float(np.mean([r["abs_err"] for r in records])), 3)
    return out


def nested_policy_eval(estimator, sub, feature_cols, target_col, cap, alpha,
                       target_kind, seed=42, n_outer=5, n_inner=4):
    """Fully nested: per outer fold, learn the policy on outer-train ONLY, freeze
    it, fit the point model on outer-train, and apply the frozen policy to the
    held-out outer-test players. Outer-test never influences the policy."""
    X = sub[feature_cols]; y = sub[target_col].to_numpy(float)
    groups = sub["player_id"].to_numpy(); pos = sub["coarse_group"].to_numpy()
    ages = sub["age"].to_numpy(float)
    bands = GOAL_BANDS if target_kind == "goals" else APP_BANDS
    records = []; method_freq = Counter()
    for tr, te in GroupKFold(n_outer).split(X, y, groups):
        sub_tr = sub.iloc[tr].reset_index(drop=True)
        policy = learn_policy(estimator, sub_tr, feature_cols, target_col, cap, alpha,
                              target_kind, seed=seed, n_inner=n_inner)
        method_freq[policy["method"]] += 1
        model = clone(estimator).fit(X.iloc[tr], y[tr])
        pred_te = np.clip(model.predict(X.iloc[te]), 0, cap)
        for j, idx in enumerate(te):
            iv, reason = runtime_interval(policy, float(pred_te[j]), pos[idx])
            emitted = iv is not None
            records.append({
                "emitted": emitted,
                "cov": (float(iv[0]) <= y[idx] <= float(iv[1])) if emitted else None,
                "width": (iv[1] - iv[0]) if emitted else None,
                "reason": reason if not emitted else None,
                "pos": pos[idx], "age_band": band_label(ages[idx], AGE_BANDS),
                "pred_band": band_label(float(pred_te[j]), bands),
                "abs_err": abs(y[idx] - float(pred_te[j])),
            })
    agg = _agg_records(records, target_kind)
    agg["selected_method_frequency"] = dict(method_freq)
    agg["availability_acceptance"] = availability_acceptance(agg, target_kind)
    return agg


def availability_acceptance(agg, target_kind, min_group_emitted=20):
    o = agg["overall"]
    checks = {}
    c = o["coverage_when_emitted"]
    checks["overall_coverage_when_emitted_0.75_0.87"] = (c is not None and 0.75 <= c <= 0.87)
    checks["overall_emission_rate_ge_0.70"] = (o["emission_rate"] is not None and o["emission_rate"] >= 0.70)
    for p in POSITIONS:
        g = agg["by_position"][p]
        if g["n_emitted"] >= min_group_emitted:
            checks[f"pos_{p}_coverage_ge_0.70"] = g["coverage_when_emitted"] >= 0.70
        if g["n"] >= min_group_emitted:
            checks[f"pos_{p}_emission_ge_0.60"] = (g["emission_rate"] or 0) >= 0.60
    hi = "16+" if target_kind == "goals" else "35+"
    g = agg["by_pred_band"].get(hi, {})
    if g.get("n_emitted", 0) >= min_group_emitted:
        checks[f"highband_{hi}_coverage_ge_0.70"] = g["coverage_when_emitted"] >= 0.70
    checks["_all_pass"] = all(v for k, v in checks.items() if not k.startswith("_"))
    checks["_n_pass"] = sum(1 for k, v in checks.items() if not k.startswith("_") and v)
    # unsupported groups: emitted coverage < 0.70 with enough emitted samples
    unsupported = []
    for p in POSITIONS:
        g = agg["by_position"][p]
        if g["n_emitted"] >= min_group_emitted and g["coverage_when_emitted"] is not None \
                and g["coverage_when_emitted"] < 0.70:
            unsupported.append(f"pos:{p}")
    for band, g in agg["by_pred_band"].items():
        if g["n_emitted"] >= min_group_emitted and g["coverage_when_emitted"] is not None \
                and g["coverage_when_emitted"] < 0.70:
            unsupported.append(f"predband:{band}")
    checks["unsupported_interval_groups"] = unsupported
    return checks
