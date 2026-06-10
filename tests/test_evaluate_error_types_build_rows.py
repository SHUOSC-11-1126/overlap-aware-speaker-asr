from __future__ import annotations

import unittest

from src.evaluate_error_types import build_rows


class EvaluateErrorTypesBuildRowsTest(unittest.TestCase):
    def test_build_rows_returns_three_methods_for_no_overlap(self) -> None:
        rows = build_rows("NoOverlap")
        methods = {row["method"] for row in rows}
        self.assertEqual(methods, {"mixed_whisper", "separated_whisper", "separated_whisper_cleaned"})

    def test_build_rows_includes_observation_and_dominant_error_type(self) -> None:
        rows = build_rows("NoOverlap")
        for row in rows:
            self.assertIn("dominant_error_type", row)
            self.assertIn("observation", row)
            self.assertTrue(row["observation"])
            self.assertGreaterEqual(row["reference_length"], 0)
            self.assertGreaterEqual(row["cer"], 0.0)


if __name__ == "__main__":
    unittest.main()
