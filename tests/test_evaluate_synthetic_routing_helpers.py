from __future__ import annotations

import unittest

from src.evaluate_synthetic_routing import dataset_paths, selected_method_v1, to_float, to_int


class EvaluateSyntheticRoutingHelpersTest(unittest.TestCase):
    def test_dataset_paths_returns_expected_keys(self) -> None:
        paths = dataset_paths("synthetic_overlap")
        self.assertIn("manifest", paths)
        self.assertIn("cer", paths)
        self.assertTrue(str(paths["manifest"]).endswith("synthetic_manifest.csv"))

    def test_dataset_paths_rejects_unknown_dataset(self) -> None:
        with self.assertRaises(ValueError):
            dataset_paths("unknown_dataset")

    def test_to_float_and_to_int_parse_numeric_strings(self) -> None:
        self.assertEqual(to_float("0.5"), 0.5)
        self.assertEqual(to_int("3"), 3)
        self.assertEqual(to_float("bad"), 0.0)
        self.assertEqual(to_int("bad"), 0)

    def test_selected_method_v1_delegates_to_router_v1(self) -> None:
        method, _ = selected_method_v1(0)
        self.assertEqual(method, "separated_whisper")


if __name__ == "__main__":
    unittest.main()
