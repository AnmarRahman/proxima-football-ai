"""Mandatory naive baselines. A complex model earns its place only by beating
these clearly and consistently.

  * NaivePrevSeason  - predict next season = current season (persistence).
  * AgePositionAvg   - predict the training mean for the player's
                       (coarse position group, age band).
  * BaseRate         - continuation: predict the training continuation rate.
"""

import numpy as np
import pandas as pd

AGE_BINS = [-np.inf, 21, 25, 29, 33, np.inf]
AGE_LABELS = ["<=21", "22-25", "26-29", "30-33", "34+"]


def age_band(age_series):
    return pd.cut(age_series, bins=AGE_BINS, labels=AGE_LABELS)


class NaivePrevSeason:
    """Persistence baseline: next season equals this season."""
    COL = {"y_next_apps": "cur_apps", "y_next_goals": "cur_goals", "y_next_gpa": "cur_gpa"}

    def __init__(self, target):
        self.target = target

    def fit(self, df):
        return self

    def predict(self, df):
        return np.clip(df[self.COL[self.target]].to_numpy(dtype=float), 0, None)


class AgePositionAvg:
    """Predict the training mean for (coarse_group, age_band)."""

    def __init__(self, target):
        self.target = target

    def fit(self, df):
        d = df.copy()
        d["_ab"] = age_band(d["age"])
        self.table = d.groupby(["coarse_group", "_ab"], observed=True)[self.target].mean().to_dict()
        self.by_group = d.groupby("coarse_group", observed=True)[self.target].mean().to_dict()
        self.global_ = float(d[self.target].mean())
        return self

    def predict(self, df):
        d = df.copy()
        d["_ab"] = age_band(d["age"])
        out = []
        for g, ab in zip(d["coarse_group"], d["_ab"]):
            v = self.table.get((g, ab))
            if v is None or v != v:
                v = self.by_group.get(g, self.global_)
            out.append(v)
        return np.clip(np.array(out, dtype=float), 0, None)


class BaseRate:
    """Continuation baseline: constant training continuation rate."""

    def fit(self, df, target="y_continue"):
        self.p = float(df[target].mean())
        return self

    def predict_proba(self, df):
        return np.full(len(df), self.p, dtype=float)
