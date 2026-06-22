import unittest

from src.source_disjoint_v2_common import BOOTSTRAP_SUMMARY, bootstrap_unified_router_results, read_csv


class BootstrapRouterResultsTest(unittest.TestCase):
    def test_bootstrap_ci_has_ordered_bounds(self):
        bootstrap_unified_router_results(iterations=100)
        rows = read_csv(BOOTSTRAP_SUMMARY)
        self.assertTrue(rows)
        for row in rows:
            self.assertLessEqual(float(row["ci_low"]), float(row["ci_high"]))


if __name__ == "__main__":
    unittest.main()
