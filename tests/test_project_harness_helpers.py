from __future__ import annotations

import unittest

from src.project_harness import exists, inspect_synthetic_separation


class HelpersTest(unittest.TestCase):
    def test_exists_returns_true_for_verified_references(self) -> None:
        self.assertTrue(exists("references/reference_transcripts.json"))

    def test_exists_returns_false_for_missing_path(self) -> None:
        self.assertFalse(exists("does/not/exist.xyz"))

    def test_inspect_synthetic_separation_reports_status(self) -> None:
        status = inspect_synthetic_separation()["status"]
        self.assertIn(status, {"synthetic_overlap", "synthetic_overlap_v2", "missing"})


if __name__ == "__main__":
    unittest.main()
