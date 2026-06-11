from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass_final_bridge_checklist import (
    BRIDGE_CHECKLIST_COLUMNS,
    build_bridge_checklist_rows,
    write_outputs,
)


class LlmCriticReviewPassFinalBridgeChecklistWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_bridge_checklist_rows({"case_id": "OppositeOverlap", "completed_pass_count": "4"})
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_final_bridge_checklist.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)
            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(csv.DictReader(handle).fieldnames, BRIDGE_CHECKLIST_COLUMNS)
            self.assertIn("LLM Critic Review Pass Final Bridge Checklist", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
