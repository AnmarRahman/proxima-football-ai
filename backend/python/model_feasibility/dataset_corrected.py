"""Corrected modelling dataset (Phase 2C).

Loads collected_player_seasons.csv and builds a leakage-safe feature frame with
CORRECTED targets:

  * only MODEL-ELIGIBLE seasons enter the sequence (amateur / post-retirement
    cameos are excluded from targets and continuation);
  * a partial (ongoing) season is a valid FEATURE but never a regression target,
    and a transition INTO a partial next season is censored;
  * next-season regression targets exist only when the next eligible season is
    GENUINELY CONSECUTIVE (chronology-aware, not start-year arithmetic);
  * y_continue_next_season: 1 if an eligible pro domestic-league season is
    recorded in the immediately-following consecutive canonical season; 0 if the
    player does not return next season and is known retired; null when censored
    (active/unknown, or an ongoing partial next season);
  * y_ever_returns_after_current_season kept as a SEPARATE experimental target.

Removed/censored rows are counted and returned for the leakage report.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chronology as CH                              # noqa: E402
from features import (COARSE_GROUPS, FEATURE_COLUMNS, _gpa,  # noqa: E402
                      _safe_lag, _trend3)

SEASONS_CSV = HERE.parent / "data" / "collected_player_seasons.csv"
CURRENT_SEASON_START = 2026
CORRECTED_TARGETS = ["y_next_apps", "y_next_goals", "y_next_gpa",
                     "y_continue_next_season", "y_ever_returns", "y_remaining"]


def load_players(csv_path=None):
    """Load players from the given CSV path (or the default). The caller passes
    the declared training dataset so training uses exactly those bytes."""
    path = csv_path or SEASONS_CSV
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    by = defaultdict(list)
    meta = {}
    for r in rows:
        by[r["player_id"]].append(r)
        meta[r["player_id"]] = r
    players = []
    for pid, srows in by.items():
        seasons = [{
            "canonical_season": r["canonical_season"],
            "season_start_year": int(r["season_start_year"]),
            "season_end_year": int(r["season_end_year"]),
            "season_format": r["season_format"],
            "appearances": int(r["appearances"]), "goals": int(r["goals"]),
            "is_partial": r["is_partial"] == "True",
            "model_eligible": r["model_eligible"] == "True",
        } for r in srows]
        b = meta[pid].get("birth_date") or ""
        players.append({
            "player_id": pid, "name": meta[pid]["name"],
            "coarse_group": meta[pid]["coarse_group"],
            "position_group": meta[pid]["position_group"],
            "career_status": meta[pid]["career_status"],
            "birth_year": int(b[:4]) if b[:4].isdigit() else None,
            "seasons": seasons,
        })
    return players


def build_frame(players):
    rows = []
    removed = defaultdict(int)
    for rec in players:
        elig = [s for s in rec["seasons"] if s["model_eligible"]]
        removed["ineligible_seasons_excluded"] += len(rec["seasons"]) - len(elig)
        seasons = CH.order_seasons(elig)
        n = len(seasons)
        if n == 0:
            continue
        apps = [s["appearances"] for s in seasons]
        goals = [s["goals"] for s in seasons]
        status = rec["career_status"]
        cum_a = cum_g = 0
        for i in range(n):
            cum_a += apps[i]; cum_g += goals[i]
            yr = seasons[i]["season_start_year"]
            age = (yr - rec["birth_year"]) if rec["birth_year"] else np.nan
            feats = {
                "player_id": rec["player_id"], "name": rec["name"],
                "season_year": yr, "coarse_group": rec["coarse_group"],
                "fine_group": rec["position_group"], "career_status": status,
                "current_is_partial": seasons[i]["is_partial"],
                "age": age, "age_sq": (age * age) if age == age else np.nan,
                "years_experience": i + 1,
                "cur_apps": apps[i], "cur_goals": goals[i],
                "cur_gpa": _gpa(goals[i], apps[i]),
                "cur_apps_zero": 1.0 if apps[i] == 0 else 0.0,
                "career_apps": cum_a, "career_goals": cum_g,
                "career_gpa": _gpa(cum_g, cum_a),
                "roll3_apps": float(np.mean(apps[max(0, i - 2):i + 1])),
                "roll3_goals": float(np.mean(goals[max(0, i - 2):i + 1])),
                "roll3_gpa": _gpa(sum(goals[max(0, i - 2):i + 1]), sum(apps[max(0, i - 2):i + 1])),
                "apps_trend3": _trend3(apps, i),
            }
            for k in range(1, 6):
                va, ma = _safe_lag(apps, i, k)
                vg, _ = _safe_lag(goals, i, k)
                feats[f"lag{k}_apps"] = va
                feats[f"lag{k}_goals"] = vg
                feats[f"lag{k}_apps_missing"] = ma
            if i - 1 >= 0:
                feats["delta_apps"] = float(apps[i] - apps[i - 1])
                feats["delta_goals"] = float(goals[i] - goals[i - 1])
                feats["delta_missing"] = 0.0
            else:
                feats["delta_apps"] = np.nan; feats["delta_goals"] = np.nan
                feats["delta_missing"] = 1.0
            for g in COARSE_GROUPS:
                feats[f"g_{g}"] = 1.0 if rec["coarse_group"] == g else 0.0

            # ---- corrected targets (chronology + partial + status aware) ----
            has_next = i + 1 < n
            consec = has_next and CH.seasons_consecutive(seasons[i], seasons[i + 1])
            next_partial = has_next and seasons[i + 1]["is_partial"]

            if consec and not next_partial:
                feats["y_next_apps"] = float(apps[i + 1])
                feats["y_next_goals"] = float(goals[i + 1])
                feats["y_next_gpa"] = _gpa(goals[i + 1], apps[i + 1]) if apps[i + 1] > 0 else np.nan
            else:
                feats["y_next_apps"] = feats["y_next_goals"] = feats["y_next_gpa"] = np.nan
                if consec and next_partial:
                    removed["target_from_partial_next_excluded"] += 1
                elif has_next and not consec:
                    removed["regression_no_consecutive_next"] += 1

            if consec and not next_partial:
                feats["y_continue_next_season"] = 1.0
            elif consec and next_partial:
                feats["y_continue_next_season"] = np.nan       # ongoing -> censored
                removed["continuation_censored_partial_next"] += 1
            elif has_next and not consec:
                feats["y_continue_next_season"] = 0.0          # did NOT play next season
            else:                                              # last eligible season
                if status == "retired":
                    feats["y_continue_next_season"] = 0.0
                else:
                    feats["y_continue_next_season"] = np.nan   # active/unknown -> censored
                    removed["continuation_censored_active_or_unknown"] += 1

            feats["y_ever_returns"] = 1.0 if has_next else (0.0 if status == "retired" else np.nan)
            feats["y_remaining"] = float(n - 1 - i) if status == "retired" else np.nan
            rows.append(feats)

    df = pd.DataFrame(rows)
    for c in FEATURE_COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df, dict(removed)
