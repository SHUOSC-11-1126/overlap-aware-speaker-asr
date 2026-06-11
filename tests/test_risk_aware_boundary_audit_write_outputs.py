from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.risk_aware_boundary_audit import AUDIT_COLUMNS, write_outputs


class RiskAwareBoundaryAuditWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "case_id": "LightOverlap",
            "overlap_ratio_anchor": 0.15,
            "base_router_method": "mixed_whisper",
            "final_selected_method": "mixed_whisper",
            "risk_level": "high",
            "oracle_method": "mixed_whisper",
            "mixed_cer": 0.21,
            "separated_cer": 0.48,
            "separated_cleaned_cer": 0.38,
            "selected_cer": 0.21,
            "oracle_cer": 0.21,
            "delta_cer_separated": 0.27,
            "separation_helps": False,
            "prefers_separation_route": False,
            "selector_matches_oracle": True,
            "selector_aligns_with_phase": True,
            "selector_regret_cer": 0.0,
            "risk_layer_changed_method": False,
            "recommended_action": "keep mixed",
        }
        summary = [{"metric": "selector_oracle_match_rate", "value": "1.0", "label": "experimental/frontier"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.risk_aware_boundary_audit.PROJECT_ROOT", root):
                paths = write_outputs([row], summary)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, AUDIT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
