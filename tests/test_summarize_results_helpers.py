from __future__ import annotations

import unittest

from src.summarize_results import to_float


class SummarizeResultsHelpersTest(unittest.TestCase):
    def test_to_float_parses_numeric_strings(self) -> None:
        self.assertEqual(to_float("0.12"), 0.12)

    def test_to_float_returns_none_for_empty_or_invalid(self) -> None:
        self.assertIsNone(to_float(None))
        self.assertIsNone(to_float(""))
        self.assertIsNone(to_float("bad"))


if __name__ == "__main__":
    unittest.main()
