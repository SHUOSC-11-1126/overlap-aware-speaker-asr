import unittest

from src.source_disjoint_v2_common import (
    POLICIES,
    UNIFIED_PREDICTIONS,
    UNIFIED_SUMMARY,
    evaluate_unified_router_benchmark,
    read_csv,
)


class UnifiedRouterEvalTest(unittest.TestCase):
    def test_unified_eval_writes_expected_schema(self):
        evaluate_unified_router_benchmark()
        predictions = read_csv(UNIFIED_PREDICTIONS)
        summary = read_csv(UNIFIED_SUMMARY)
        self.assertTrue(predictions)
        self.assertEqual({row["policy"] for row in summary}, set(POLICIES))
        required = {"sample_id", "policy", "selected_route", "selected_cer", "oracle_cer", "false_safe"}
        self.assertTrue(required.issubset(predictions[0]))


if __name__ == "__main__":
    unittest.main()
