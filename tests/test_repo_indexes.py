import csv
import unittest
from pathlib import Path

from scripts.generate_repo_indexes import classify_module


ROOT = Path(__file__).resolve().parents[1]


class RepoIndexesTest(unittest.TestCase):
    def test_module_lifecycle_index_exists(self):
        path = ROOT / "docs" / "module_lifecycle.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("stable-mainline", text)
        self.assertIn("frontier-audiodepth", text)

    def test_results_manifest_has_required_fields(self):
        path = ROOT / "results" / "tables" / "results_manifest.csv"
        self.assertTrue(path.exists())
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(rows)
        for field in ["path", "evidence_label", "generated_by", "reviewer_priority", "keep_action"]:
            self.assertIn(field, rows[0])

    def test_package_init_is_stable_mainline(self):
        self.assertEqual(classify_module(ROOT / "src" / "__init__.py"), "stable-mainline")


if __name__ == "__main__":
    unittest.main()
