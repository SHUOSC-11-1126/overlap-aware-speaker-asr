from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.router_feature_importance import read_csv_rows, to_float


class RouterFeatureImportanceHelpersTest(unittest.TestCase):
    def test_to_float_parses_numeric_strings(self) -> None:
        self.assertAlmostEqual(to_float(" 1.25 "), 1.25)

    def test_to_float_returns_zero_for_invalid_values(self) -> None:
        self.assertEqual(to_float("not-a-number"), 0.0)

    def test_read_csv_rows_loads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.csv"
            path.write_text("feature_name,importance_score\noverlap_ratio,0.42\n", encoding="utf-8")
            rows = read_csv_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["feature_name"], "overlap_ratio")
        self.assertEqual(rows[0]["importance_score"], "0.42")


if __name__ == "__main__":
    unittest.main()
