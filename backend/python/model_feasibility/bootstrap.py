"""Player-cluster paired bootstrap.

Row-level bootstrap understates uncertainty because a player's seasons are
correlated. Here we resample PLAYER IDs with replacement and include all of a
sampled player's rows, then compute the PAIRED difference (baseline MAE - model
MAE) on the same resample. Positive difference = model better. We report the
difference CI and P(model beats baseline).
"""

from collections import defaultdict

import numpy as np


def cluster_paired_bootstrap(y, pred_model, pred_base, players, n=2000, seed=42):
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float)
    pred_model = np.asarray(pred_model, float)
    pred_base = np.asarray(pred_base, float)
    idx_by = defaultdict(list)
    for i, p in enumerate(players):
        idx_by[p].append(i)
    uniq = list(idx_by)
    diffs, mm, bb = [], [], []
    for _ in range(n):
        samp = rng.choice(len(uniq), size=len(uniq), replace=True)
        rows = [i for k in samp for i in idx_by[uniq[k]]]
        rows = np.array(rows)
        yr = y[rows]
        m = float(np.mean(np.abs(yr - pred_model[rows])))
        b = float(np.mean(np.abs(yr - pred_base[rows])))
        mm.append(m); bb.append(b); diffs.append(b - m)
    diffs = np.array(diffs)
    return {
        "diff_mean": round(float(diffs.mean()), 3),
        "diff_ci95": [round(float(np.percentile(diffs, 2.5)), 3),
                      round(float(np.percentile(diffs, 97.5)), 3)],
        "p_model_beats_base": round(float((diffs > 0).mean()), 3),
        "model_mae_ci95": [round(float(np.percentile(mm, 2.5)), 3),
                           round(float(np.percentile(mm, 97.5)), 3)],
        "base_mae_ci95": [round(float(np.percentile(bb, 2.5)), 3),
                          round(float(np.percentile(bb, 97.5)), 3)],
    }
