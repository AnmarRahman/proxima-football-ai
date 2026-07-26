import sys
import unittest
from pathlib import Path

import pandas as pd

PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

import main  # noqa: E402


class PredictorDataTests(unittest.TestCase):
    def test_position_features_support_hybrid_roles(self) -> None:
        winger_forward = main.position_features("Left Wing / Second Striker")
        self.assertEqual(winger_forward["position_winger"], 1.0)
        self.assertEqual(winger_forward["position_striker"], 1.0)

        holding_midfielder = main.position_features("Defensive Midfield")
        self.assertEqual(holding_midfielder["position_defensive_midfield"], 1.0)
        self.assertEqual(holding_midfielder["position_winger"], 0.0)

    def test_training_windows_retain_player_groups(self) -> None:
        rows = []
        for player_id in ("player-a", "player-b", "player-c"):
            for season in range(2020, 2025):
                row = {
                    "player_id": player_id,
                    "player_name": player_id,
                    "is_retired": False,
                    "season": season,
                }
                row.update({name: 0.0 for name in main.MODEL_INPUT_NAMES})
                row["age"] = season - 2000
                row["rating"] = 7.0
                rows.append(row)

        frame = main.postprocess_loaded_df(pd.DataFrame(rows))
        x_rows, y_rows, groups = main.build_training_sequences(frame, window_size=4)

        self.assertEqual(x_rows.shape[0], 3)
        self.assertEqual(y_rows.shape[0], 3)
        self.assertEqual(set(groups), {"player-a", "player-b", "player-c"})

    def test_prediction_postprocessing_prevents_negative_counts(self) -> None:
        raw = [-10.0] * len(main.FEATURE_NAMES)
        prediction = main.postprocess_prediction(raw, age=29)

        self.assertEqual(prediction["goals"], 0.0)
        self.assertEqual(prediction["assists"], 0.0)
        self.assertEqual(prediction["age"], 29.0)
        self.assertGreaterEqual(prediction["rating"], 4.0)


if __name__ == "__main__":
    unittest.main()
