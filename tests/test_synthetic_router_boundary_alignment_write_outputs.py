from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.synthetic_router_boundary_alignment import ALIGNMENT_COLUMNS, write_outputs


class SyntheticRouterBoundaryAlignmentWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "sample_id": "SyntheticLightOverlap_test_01",
            "split": "test",
            "tier": "SyntheticLightOverlap",
            "overlap_ratio": 0.15,
            "selected_method": "mixed_whisper",
            "oracle_method": "mixed_whisper",
            "mixed_cer": 0.1,
            "separated_cer": 0.3,
            "separated_cleaned_cer": 0.2,
            "selected_cer": 0.1,
            "oracle_cer": 0.1,
            "delta_cer_separated": 0.2,
            "separation_helps": False,
            "prefers_separation_route": False,
            "router_matches_oracle": True,
            "router_aligns_with_phase": True,
            "router_regret_cer": 0.0,
            "decision_rule": "fixture",
        }
        summary = [{"scope": "test", "metric": "sample_count", "value": "1", "label": "synthetic/silver"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.synthetic_router_boundary_alignment.PROJECT_ROOT", root):
                paths = write_outputs([row], summary)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ALIGNMENT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
