"""Run every backend Python test directory as one suite."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_DIRS = (
    ROOT / "data" / "acquisition" / "tests",
    ROOT / "data" / "collection" / "tests",
    ROOT / "model_feasibility" / "tests",
    ROOT / "tests",
)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_dir in TEST_DIRS:
        suite.addTests(
            loader.discover(
                start_dir=str(test_dir),
                pattern="test_*.py",
                top_level_dir=str(test_dir),
            )
        )

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
