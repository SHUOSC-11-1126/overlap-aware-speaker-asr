from __future__ import annotations

import unittest

from src.adaptive_router_v2 import load_synthetic_inputs


class AdaptiveRouterV2LoadSyntheticInputsTest(unittest.TestCase):
    def test_load_synthetic_inputs_returns_manifest_cleaned_and_cer_lookup(self) -> None:
        manifest_rows, cleaned_rows, cer_lookup = load_synthetic_inputs()
        self.assertGreater(len(manifest_rows), 0)
        self.assertGreater(len(cer_lookup), 0)
        sample_ids = {str(row.get("sample_id", "")).strip() for row in manifest_rows}
        self.assertIn("SyntheticNoOverlap_01", sample_ids)


if __name__ == "__main__":
    unittest.main()
