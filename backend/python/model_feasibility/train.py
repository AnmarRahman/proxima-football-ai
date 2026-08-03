"""Model factories (lightweight tabular models only; no GRU/TensorFlow).

All models take a fixed random seed for reproducibility. Linear/Poisson/RF/
Logistic run inside an imputing pipeline (median impute; explicit missing
indicators are already in the feature matrix). HistGradientBoosting receives
raw NaN and handles missingness natively.
"""

from sklearn.compose import TransformedTargetRegressor  # noqa: F401 (available if needed)
from sklearn.ensemble import (HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import (ElasticNet, LogisticRegression, PoissonRegressor,
                                  Ridge)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42


def _linear(model):
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", model),
    ])


def _tree_impute(model):
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", model),
    ])


def make_regressors(seed=SEED):
    """Count/continuous regressors. HGB handles NaN natively (no pipeline)."""
    return {
        "ridge": _linear(Ridge(alpha=1.0)),
        "elasticnet": _linear(ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=seed, max_iter=5000)),
        "poisson": _linear(PoissonRegressor(alpha=1.0, max_iter=1000)),
        "randomforest": _tree_impute(RandomForestRegressor(
            n_estimators=200, min_samples_leaf=2, random_state=seed, n_jobs=-1)),
        "histgb": HistGradientBoostingRegressor(random_state=seed, max_depth=3, learning_rate=0.08),
    }


def make_quantile_regressors(seed=SEED):
    return {
        "q10": HistGradientBoostingRegressor(loss="quantile", quantile=0.1,
                                             random_state=seed, max_depth=3),
        "q90": HistGradientBoostingRegressor(loss="quantile", quantile=0.9,
                                             random_state=seed, max_depth=3),
    }


def make_classifiers(seed=SEED):
    return {
        "logistic": _linear(LogisticRegression(max_iter=2000, class_weight="balanced",
                                               random_state=seed)),
        "histgb_clf": HistGradientBoostingClassifier(random_state=seed, max_depth=3,
                                                     learning_rate=0.08),
    }
