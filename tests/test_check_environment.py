import unittest

from scripts.check_environment import collect_report


class CheckEnvironmentTest(unittest.TestCase):
    def test_collect_report_has_core_rows(self):
        rows, ok = collect_report()
        names = {row.name for row in rows}
        self.assertIn("python", names)
        self.assertIn("test-runner", names)
        self.assertIsInstance(ok, bool)


if __name__ == "__main__":
    unittest.main()
