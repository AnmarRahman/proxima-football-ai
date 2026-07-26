"""Compare candidate regressors using the predictor's player-held-out split."""

from typing import Any, Dict

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import MinMaxScaler

import main


def metrics(prediction: np.ndarray, truth: np.ndarray, baseline: np.ndarray) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for name in ("goals", "assists", "rating"):
        index = main.FEATURE_NAMES.index(name)
        result[f"mae_{name}"] = float(np.mean(np.abs(prediction[:, index] - truth[:, index])))
        result[f"baseline_{name}"] = float(np.mean(np.abs(baseline[:, index] - truth[:, index])))
    result["mae_all"] = float(np.mean(np.abs(prediction - truth)))
    result["baseline_all"] = float(np.mean(np.abs(baseline - truth)))
    return result


def evaluate() -> None:
    frame = main.load_all_players_df_from_files()
    x_rows, y_rows, groups = main.build_training_sequences(frame, window_size=4)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_indices, validation_indices = next(splitter.split(x_rows, y_rows, groups=groups))

    x_train = x_rows[train_indices].reshape(len(train_indices), -1)
    x_validation = x_rows[validation_indices].reshape(len(validation_indices), -1)
    truth = y_rows[validation_indices]
    train_baseline = x_rows[train_indices, -1, : len(main.FEATURE_NAMES)]
    validation_baseline = x_rows[validation_indices, -1, : len(main.FEATURE_NAMES)]

    candidates: Dict[str, Any] = {
        "random_forest_leaf_1": RandomForestRegressor(
            n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=1, max_features=0.75
        ),
        "random_forest_leaf_2": RandomForestRegressor(
            n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=2, max_features=0.75
        ),
        "extra_trees_leaf_1": ExtraTreesRegressor(
            n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=1, max_features=0.75
        ),
        "extra_trees_leaf_2": ExtraTreesRegressor(
            n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=2, max_features=0.75
        ),
    }

    for target_mode in ("absolute", "residual"):
        train_target = y_rows[train_indices]
        if target_mode == "residual":
            train_target = train_target - train_baseline

        target_scaler = MinMaxScaler().fit(train_target)
        scaled_target = target_scaler.transform(train_target)

        for candidate_name, candidate in candidates.items():
            candidate.fit(x_train, scaled_target)
            target_prediction = target_scaler.inverse_transform(candidate.predict(x_validation))
            if target_mode == "residual":
                target_prediction = validation_baseline + target_prediction

            for blend in (1.0, 0.75, 0.5):
                prediction = validation_baseline + blend * (target_prediction - validation_baseline)
                result = metrics(prediction, truth, validation_baseline)
                print(f"{target_mode}:{candidate_name}:blend={blend}: {result}")


if __name__ == "__main__":
    evaluate()
