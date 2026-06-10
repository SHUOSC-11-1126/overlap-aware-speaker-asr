from __future__ import annotations

import unittest

from src.project_harness import exists, frontier_next_artifact, frontier_priority, inspect_synthetic_separation


class ProjectHarnessHelpersTest(unittest.TestCase):
    def test_exists_returns_true_for_verified_references(self) -> None:
        self.assertTrue(exists("references/reference_transcripts.json"))

    def test_exists_returns_false_for_missing_path(self) -> None:
        self.assertFalse(exists("results/__missing_harness_path__.json"))

    def test_frontier_priority_ranks_meeteval_first(self) -> None:
        self.assertLess(frontier_priority("meeteval_compatibility"), frontier_priority("demo_excellence"))
        self.assertEqual(frontier_priority("unknown_frontier"), 99)

    def test_frontier_next_artifact_returns_handoff_paths(self) -> None:
        figure_path, receipt_path = frontier_next_artifact("meeteval_compatibility")
        self.assertIn("meeteval", figure_path)
        self.assertIn("receipt", receipt_path)

    def test_inspect_synthetic_separation_reports_status(self) -> None:
        status = inspect_synthetic_separation()
        self.assertIn("status", status)
        self.assertIn(status["status"], {"synthetic_overlap", "synthetic_overlap_v2", "missing"})


if __name__ == "__main__":
    unittest.main()
