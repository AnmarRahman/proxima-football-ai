"""Player-grouped, finite-sample split-conformal prediction intervals with an
HONEST nested evaluation (interval quantiles are NEVER calibrated and evaluated
on the same residuals).

  * `conformal_offsets` — finite-sample-corrected asymmetric offsets for a target
    central coverage (1 - alpha).
  * `nested_conformal_eval` — outer player-grouped folds provide untouched
    evaluation players; the conformal quantile is calibrated only INSIDE each
    outer fold (on a held-out calibration split of the outer-train players);
    coverage is reported on outer-test predictions only. Also reports coverage
    by position/age, high-scorer under-coverage, and mean/median width.
  * `chronological_conformal_eval` — time-aware variant (train early, calibrate
    middle, evaluate latest seasons).
  * `final_conformal_offsets` — deployed offsets from cross-conformal (grouped
    OOF) residuals over the COMPLETE training dataset.
"""

import numpy as np
from sklearn.base import clone
from sklearn.model_selection import GroupKFold, GroupShuffleSplit


def conformal_offsets(residuals, alpha, min_cal=10):
    """Finite-sample asymmetric split-conformal offsets (q_low, q_high) for
    central coverage 1-alpha. Uses the (n+1)-rank adjustment; falls back to the
    empirical min/max when a tail rank exceeds the sample."""
    r = np.sort(np.asarray(residuals, dtype=float))
    n = len(r)
    if n < min_cal:
        # too few points to calibrate reliably -> widest empirical bounds
        return float(r.min()) if n else 0.0, float(r.max()) if n else 0.0
    lo_rank = int(np.floor((n + 1) * (alpha / 2)))       # 1-indexed
    hi_rank = int(np.ceil((n + 1) * (1 - alpha / 2)))
    q_low = r[lo_rank - 1] if lo_rank >= 1 else r[0]
    q_high = r[hi_rank - 1] if hi_rank <= n else r[-1]   # rank>n -> +inf -> use max
    return float(q_low), float(q_high)


def _apply(pred, q_low, q_high, cap):
    lo = np.clip(pred + q_low, 0, None)
    hi = pred + q_high
    if cap is not None:
        hi = np.clip(hi, 0, cap)
    return lo, hi


def _summ(cov, width, y, positions, ages):
    y = np.asarray(y, float)
    out = {"n": int(len(cov)),
           "coverage": round(float(np.mean(cov)), 3),
           "mean_width": round(float(np.mean(width)), 2),
           "median_width": round(float(np.median(width)), 2),
           "by_position": {}, "by_age": {}}
    pos = np.asarray(positions)
    for p in sorted(set(pos)):
        m = pos == p
        out["by_position"][p] = {"n": int(m.sum()), "coverage": round(float(np.mean(cov[m])), 3)}
    ab = np.asarray(ages, dtype=float)
    bands = [("<=21", ab <= 21), ("22-25", (ab > 21) & (ab <= 25)),
             ("26-29", (ab > 25) & (ab <= 29)), ("30-33", (ab > 29) & (ab <= 33)),
             ("34+", ab > 33)]
    for name, m in bands:
        if m.sum() >= 5:
            out["by_age"][name] = {"n": int(m.sum()), "coverage": round(float(np.mean(cov[m])), 3)}
    # high scorers = top decile of the target value
    thr = np.quantile(y, 0.9)
    hs = y >= thr
    if hs.sum() >= 5:
        out["high_scorer_subset"] = {"threshold": round(float(thr), 1), "n": int(hs.sum()),
                                     "coverage": round(float(np.mean(cov[hs])), 3),
                                     "note": "under-coverage here means intervals miss high outputs"}
    return out


def nested_conformal_eval(estimator, sub, feature_cols, target_col, cap=None,
                          alpha=0.2, seed=42, n_outer=5):
    X = sub[feature_cols]
    y = sub[target_col].to_numpy(float)
    groups = sub["player_id"].to_numpy()
    positions = sub["coarse_group"].to_numpy()
    ages = sub["age"].to_numpy(float)

    cov = np.zeros(len(sub)); width = np.zeros(len(sub)); filled = np.zeros(len(sub), bool)
    gkf = GroupKFold(n_splits=n_outer)
    for tr, te in gkf.split(X, y, groups):
        # calibration split by PLAYER inside the outer-train fold
        gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)
        pt, cal = next(gss.split(X.iloc[tr], y[tr], groups[tr]))
        proper = tr[pt]; calib = tr[cal]
        model = clone(estimator).fit(X.iloc[proper], y[proper])
        rcal = y[calib] - np.clip(model.predict(X.iloc[calib]), 0, cap)
        q_low, q_high = conformal_offsets(rcal, alpha)
        pred_te = np.clip(model.predict(X.iloc[te]), 0, cap)
        lo, hi = _apply(pred_te, q_low, q_high, cap)
        cov[te] = ((y[te] >= lo) & (y[te] <= hi)).astype(float)
        width[te] = hi - lo
        filled[te] = True
    m = filled
    return _summ(cov[m], width[m], y[m], positions[m], ages[m])


def chronological_conformal_eval(estimator, sub, feature_cols, target_col, cap=None, alpha=0.2):
    s = sub.sort_values("season_year").reset_index(drop=True)
    yq = s["season_year"]
    q1, q2 = int(np.quantile(yq, 0.6)), int(np.quantile(yq, 0.8))
    tr = s[s.season_year <= q1]; cal = s[(s.season_year > q1) & (s.season_year <= q2)]
    te = s[s.season_year > q2]
    if len(cal) < 10 or len(te) < 10:
        return {"note": "insufficient chronological split"}
    model = clone(estimator).fit(tr[feature_cols], tr[target_col].to_numpy(float))
    rcal = cal[target_col].to_numpy(float) - np.clip(model.predict(cal[feature_cols]), 0, cap)
    q_low, q_high = conformal_offsets(rcal, alpha)
    pred = np.clip(model.predict(te[feature_cols]), 0, cap)
    lo, hi = _apply(pred, q_low, q_high, cap)
    y = te[target_col].to_numpy(float)
    return {"n": int(len(te)), "test_from_season": q2 + 1,
            "coverage": round(float(np.mean((y >= lo) & (y <= hi))), 3),
            "mean_width": round(float(np.mean(hi - lo)), 2)}


def final_conformal_offsets(estimator, sub, feature_cols, target_col, cap=None,
                            alpha=0.2, seed=42, n_folds=5):
    """Deployed offsets from grouped cross-conformal (OOF) residuals over the
    complete training data."""
    X = sub[feature_cols]; y = sub[target_col].to_numpy(float)
    groups = sub["player_id"].to_numpy()
    oof = np.full(len(sub), np.nan)
    for tr, te in GroupKFold(n_splits=n_folds).split(X, y, groups):
        model = clone(estimator).fit(X.iloc[tr], y[tr])
        oof[te] = np.clip(model.predict(X.iloc[te]), 0, cap)
    resid = y - oof
    q_low, q_high = conformal_offsets(resid, alpha)
    return q_low, q_high, int(len(resid))
