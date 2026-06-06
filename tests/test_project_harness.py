from __future__ import annotations

import unittest

from src.project_harness import build_report


class ProjectHarnessTest(unittest.TestCase):
    def test_build_report_uses_repo_relative_project_root(self) -> None:
        report = build_report()
        self.assertEqual(report["project_root"], ".")


if __name__ == "__main__":
    unittest.main()
