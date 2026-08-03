"""Leakage-safe feature and target construction for the Tier-A feasibility model.

Unit of analysis: one row per (player, season). The "prediction point" is the
END of that season; features use ONLY seasons up to and including it, targets use
the NEXT season (and beyond, for the experimental remaining-career target).

Only genuinely available Tier-A signals are used: age, season, position group,
domestic-league appearances and goals, and quantities derived from a player's
own past (career-to-date, lags, rolling rates, trends, deltas, experience).
No assists/minutes/xG/ratings/physical/tactical fields are used or invented.

Missing is kept distinct from zero: lag/delta values that do not exist yet are
NaN and carry an explicit `*_missing` indicator, never a silent 0.
"""

import numpy as np
import pandas as pd

COARSE_GROUPS = ["FWD", "WIDE", "MID", "DEF"]

BASE_NUMERIC = [
    "age", "age_sq", "season_year", "years_experience",
    "cur_apps", "cur_goals", "cur_gpa",
    "career_apps", "career_goals", "career_gpa",
    "lag1_apps", "lag2_apps", "lag3_apps", "lag4_apps", "lag5_apps",
    "lag1_goals", "lag2_goals", "lag3_goals", "lag4_goals", "lag5_goals",
    "roll3_apps", "roll3_goals", "roll3_gpa",
    "delta_apps", "delta_goals", "apps_trend3",
]
MISSING_INDICATORS = [
    "lag1_apps_missing", "lag2_apps_missing", "lag3_apps_missing",
    "lag4_apps_missing", "lag5_apps_missing", "delta_missing", "cur_apps_zero",
]
GROUP_DUMMIES = [f"g_{g}" for g in COARSE_GROUPS]

FEATURE_COLUMNS = BASE_NUMERIC + MISSING_INDICATORS + GROUP_DUMMIES

TARGETS = ["y_next_apps", "y_next_goals", "y_next_gpa", "y_continue", "y_remaining"]


def _gpa(goals, apps):
    return (goals / apps) if apps and apps > 0 else 0.0


def _safe_lag(seq, i, k):
    """apps/goals from k seasons ago (i-k); (value, is_missing)."""
    j = i - k
    if j < 0:
        return np.nan, 1.0
    return float(seq[j]), 0.0


def _trend3(seq, i):
    """Availability trend over up to 3 seasons: cur - value 2 seasons ago."""
    if i - 2 < 0:
        return np.nan
    return float(seq[i]) - float(seq[i - 2])


def build_feature_frame(dataset):
    """dataset: list of player records (from build_dataset). Returns a DataFrame
    with FEATURE_COLUMNS + TARGETS + metadata, one row per (player, season)."""
    rows = []
    for rec in dataset:
        seasons = rec.get("seasons") or []
        if not seasons:
            continue
        seasons = sorted(seasons, key=lambda s: s["season"])
        apps = [int(s["appearances"]) for s in seasons]
        goals = [int(s["goals"]) for s in seasons]
        years = [int(s["season"]) for s in seasons]
        birth_year = rec.get("birth_year")
        active = bool(rec.get("active"))
        coarse = rec.get("coarse_group")
        n = len(seasons)

        cum_apps = 0
        cum_goals = 0
        for i in range(n):
            cum_apps += apps[i]
            cum_goals += goals[i]

            has_next = i + 1 < n
            age = (years[i] - birth_year) if birth_year else np.nan

            feats = {
                "player_id": rec["player_id"], "name": rec["name"],
                "season_year": years[i], "coarse_group": coarse,
                "fine_group": rec.get("position_group"), "active": active,
                "is_last_season": not has_next,
                "age": age, "age_sq": (age * age) if age == age else np.nan,
                "years_experience": i + 1,
                "cur_apps": apps[i], "cur_goals": goals[i],
                "cur_gpa": _gpa(goals[i], apps[i]),
                "cur_apps_zero": 1.0 if apps[i] == 0 else 0.0,
                "career_apps": cum_apps, "career_goals": cum_goals,
                "career_gpa": _gpa(cum_goals, cum_apps),
                "roll3_apps": float(np.mean(apps[max(0, i - 2):i + 1])),
                "roll3_goals": float(np.mean(goals[max(0, i - 2):i + 1])),
                "roll3_gpa": _gpa(sum(goals[max(0, i - 2):i + 1]),
                                  sum(apps[max(0, i - 2):i + 1])),
                "apps_trend3": _trend3(apps, i),
            }
            for k in range(1, 6):
                va, ma = _safe_lag(apps, i, k)
                vg, _ = _safe_lag(goals, i, k)
                feats[f"lag{k}_apps"] = va
                feats[f"lag{k}_goals"] = vg
                if k == 1:
                    feats["lag1_apps_missing"] = ma
                else:
                    feats[f"lag{k}_apps_missing"] = ma
            # deltas (season-over-season change)
            if i - 1 >= 0:
                feats["delta_apps"] = float(apps[i] - apps[i - 1])
                feats["delta_goals"] = float(goals[i] - goals[i - 1])
                feats["delta_missing"] = 0.0
            else:
                feats["delta_apps"] = np.nan
                feats["delta_goals"] = np.nan
                feats["delta_missing"] = 1.0
            for g in COARSE_GROUPS:
                feats[f"g_{g}"] = 1.0 if coarse == g else 0.0

            # ---- targets (leakage-safe: use only i+1 and beyond) ----
            if has_next:
                feats["y_next_apps"] = float(apps[i + 1])
                feats["y_next_goals"] = float(goals[i + 1])
                feats["y_next_gpa"] = _gpa(goals[i + 1], apps[i + 1]) if apps[i + 1] > 0 else np.nan
                feats["y_continue"] = 1.0
            else:
                feats["y_next_apps"] = np.nan
                feats["y_next_goals"] = np.nan
                feats["y_next_gpa"] = np.nan
                # last observed season: retired -> 0 (stopped); active -> censored
                feats["y_continue"] = np.nan if active else 0.0
            # remaining-career count (experimental); censored for active players
            feats["y_remaining"] = np.nan if active else float(n - 1 - i)

            rows.append(feats)

    df = pd.DataFrame(rows)
    # ensure all feature columns exist
    for c in FEATURE_COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df


def target_frame(df, target, drop_na=True):
    """Rows usable for a given target (non-null label)."""
    sub = df if not drop_na else df[df[target].notna()].copy()
    return sub
