from __future__ import annotations

import unittest

from src.project_harness import build_report


class ProjectHarnessTest(unittest.TestCase):
    def test_build_report_uses_repo_relative_project_root(self) -> None:
        report = build_report()
        self.assertEqual(report["project_root"], ".")

    def test_build_report_includes_frontier_status_rows(self) -> None:
        report = build_report()

        frontier_rows = report["frontier_status"]
        by_id = {row["frontier_id"]: row for row in frontier_rows}

        self.assertIn("speaker_profile", by_id)
        self.assertIn("meeteval_compatibility", by_id)
        self.assertIn("llm_critic", by_id)
        self.assertIn("external_validation", by_id)
        self.assertIn("demo_excellence", by_id)
        self.assertEqual(by_id["speaker_profile"]["status"], "documented_skill")
        self.assertEqual(by_id["meeteval_compatibility"]["evidence_path"], "docs/skills/skill_04_meeteval_compatibility.md")
        self.assertIn("output", by_id["llm_critic"]["next_step"])
        self.assertIn("prioritization", by_id["external_validation"]["expected_output"])
        self.assertIn("tiny sanity-check slice", by_id["external_validation"]["next_step"])


if __name__ == "__main__":
    unittest.main()
