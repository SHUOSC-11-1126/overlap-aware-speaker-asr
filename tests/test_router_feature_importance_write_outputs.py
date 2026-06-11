from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.router_feature_importance import plot_feature_importance, render_summary


def _sample_importance_rows() -> list[dict[str, object]]:
    return [
        {
            "feature_name": "overlap_level",
            "importance_score": 0.42,
            "feature_category": "static",
            "interpretation": "fixture interpretation",
        }
    ]


class RouterFeatureImportanceWriteOutputsTest(unittest.TestCase):
    def test_render_summary_writes_markdown_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "results" / "figures").mkdir(parents=True)
            with patch("src.router_feature_importance.PROJECT_ROOT", root):
                output_path = render_summary(_sample_importance_rows())

            self.assertTrue(output_path.exists())
            markdown = output_path.read_text(encoding="utf-8")
            self.assertIn("Router v2 Feature Importance Analysis", markdown)
            self.assertIn("overlap_level", markdown)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib not installed")
    def test_plot_feature_importance_writes_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "results" / "figures").mkdir(parents=True)
            with patch("src.router_feature_importance.PROJECT_ROOT", root):
                output_path = plot_feature_importance(_sample_importance_rows())

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.suffix, ".png")


if __name__ == "__main__":
    unittest.main()
