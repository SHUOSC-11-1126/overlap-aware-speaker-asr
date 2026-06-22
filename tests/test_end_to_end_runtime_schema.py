import unittest

from src.source_disjoint_v2_common import RUNTIME_COMPONENTS, benchmark_end_to_end_runtime, read_csv


class EndToEndRuntimeSchemaTest(unittest.TestCase):
    def test_runtime_components_have_levels_and_provenance(self):
        benchmark_end_to_end_runtime()
        rows = read_csv(RUNTIME_COMPONENTS)
        self.assertTrue(rows)
        levels = {row["level"] for row in rows}
        self.assertIn("head_only_router", levels)
        self.assertIn("feature_ready_router", levels)
        self.assertIn("end_to_end_asr_reuse", levels)
        self.assertTrue(all(row["provenance"] for row in rows))


if __name__ == "__main__":
    unittest.main()
