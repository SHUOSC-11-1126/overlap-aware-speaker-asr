from __future__ import annotations

import unittest

from src.config import load_config
from src.prepare_reference_bundle import get_cases_to_bundle, load_reference_cases, required_files_for


class PrepareReferenceBundleHelpersTest(unittest.TestCase):
    def test_load_reference_cases_returns_verified_gold_cases(self) -> None:
        refs = load_reference_cases()
        self.assertIn("NoOverlap", refs)
        self.assertEqual(refs["NoOverlap"].get("status"), "verified_reference")

    def test_get_cases_to_bundle_selects_single_case(self) -> None:
        cases = get_cases_to_bundle("NoOverlap")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["id"], "NoOverlap")

    def test_required_files_for_lists_expected_gold_artifacts(self) -> None:
        config = load_config()
        files = required_files_for("NoOverlap", config)
        names = [path.name for path in files]
        self.assertIn("NoOverlap.wav", names)
        self.assertIn("NoOverlap_mixed_whisper.json", names)


if __name__ == "__main__":
    unittest.main()
