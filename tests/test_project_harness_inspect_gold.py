from __future__ import annotations

import unittest

from src.project_harness import inspect_gold_cases


class ProjectHarnessInspectGoldTest(unittest.TestCase):
    def test_inspect_gold_cases_marks_verified_references_present(self) -> None:
        status = inspect_gold_cases()
        self.assertEqual(len(status), 5)
        self.assertTrue(all(status.values()))


if __name__ == "__main__":
    unittest.main()
