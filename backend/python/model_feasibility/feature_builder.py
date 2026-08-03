"""Canonical Tier-A feature construction, shared by training and inference so
the two paths can NEVER diverge. Given a player's ordered eligible-season
appearance/goal history, `feature_row` returns the exact feature dict for the
season at index i (the prediction point), using only seasons 0..i (no leakage).

The column set/order is FEATURE_COLUMNS (from features.py). sklearn Pipelines
handle imputation/scaling downstream; this module handles the lag/rolling/career
feature engineering only.
"""

import numpy as np

from features import COARSE_GROUPS, FEATURE_COLUMNS, _gpa, _safe_lag, _trend3


def feature_row(apps, goals, years, i, birth_year, coarse):
    """Feature dict for 'current season = index i' from history apps/goals[0..i].
    `years` are season start years (for age)."""
    cum_a = sum(apps[:i + 1])
    cum_g = sum(goals[:i + 1])
    age = (years[i] - birth_year) if birth_year else np.nan
    f = {
        "season_year": years[i],
        "age": age, "age_sq": (age * age) if age == age else np.nan,
        "years_experience": i + 1,
        "cur_apps": apps[i], "cur_goals": goals[i],
        "cur_gpa": _gpa(goals[i], apps[i]),
        "cur_apps_zero": 1.0 if apps[i] == 0 else 0.0,
        "career_apps": cum_a, "career_goals": cum_g, "career_gpa": _gpa(cum_g, cum_a),
        "roll3_apps": float(np.mean(apps[max(0, i - 2):i + 1])),
        "roll3_goals": float(np.mean(goals[max(0, i - 2):i + 1])),
        "roll3_gpa": _gpa(sum(goals[max(0, i - 2):i + 1]), sum(apps[max(0, i - 2):i + 1])),
        "apps_trend3": _trend3(apps, i),
    }
    for k in range(1, 6):
        va, ma = _safe_lag(apps, i, k)
        vg, _ = _safe_lag(goals, i, k)
        f[f"lag{k}_apps"] = va
        f[f"lag{k}_goals"] = vg
        f[f"lag{k}_apps_missing"] = ma
    if i - 1 >= 0:
        f["delta_apps"] = float(apps[i] - apps[i - 1])
        f["delta_goals"] = float(goals[i] - goals[i - 1])
        f["delta_missing"] = 0.0
    else:
        f["delta_apps"] = np.nan
        f["delta_goals"] = np.nan
        f["delta_missing"] = 1.0
    for g in COARSE_GROUPS:
        f[f"g_{g}"] = 1.0 if coarse == g else 0.0
    return f


def feature_vector(apps, goals, years, i, birth_year, coarse):
    """Ordered numpy row matching FEATURE_COLUMNS (for inference)."""
    f = feature_row(apps, goals, years, i, birth_year, coarse)
    return np.array([[f.get(c, np.nan) for c in FEATURE_COLUMNS]], dtype=float)
