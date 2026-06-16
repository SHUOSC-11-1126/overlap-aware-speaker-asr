from __future__ import annotations

import unittest

from src.project_harness import CORE_FILES, GOLD_CASES, build_report


class BuildReportTest(unittest.TestCase):
    def test_report_has_expected_structure(self) -> None:
        report = build_report()
        self.assertIn("project_root", report)
        self.assertIn("core_files_present", report)
        self.assertEqual(set(report["gold_cases"]), set(GOLD_CASES))
        self.assertIn("status", report["synthetic_separation"])

    def test_core_files_present_covers_core_files(self) -> None:
        report = build_report()
        self.assertEqual(set(report["core_files_present"]), set(CORE_FILES))
        # On main, every listed authority doc / gold table should exist.
        self.assertTrue(all(report["core_files_present"].values()))


if __name__ == "__main__":
    unittest.main()
