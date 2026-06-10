from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.evaluate_synthetic_routing import dataset_paths, load_cer_lookup, selected_method_v1, to_float, to_int


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

    def test_load_cer_lookup_indexes_sample_method_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cer.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "method", "cer"])
                writer.writeheader()
                writer.writerow({"sample_id": "s1", "method": "mixed_whisper", "cer": "0.12"})

            lookup = load_cer_lookup(csv_path)
            self.assertEqual(lookup[("s1", "mixed_whisper")], 0.12)


if __name__ == "__main__":
    unittest.main()
