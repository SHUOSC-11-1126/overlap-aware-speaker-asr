from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_operator_brief import (
    OPERATOR_BRIEF_COLUMNS,
    build_operator_brief_row,
    write_outputs,
)


class FrontierExecutionQueueOperatorBriefBuildRowTest(unittest.TestCase):
    def test_build_operator_brief_row_returns_empty_without_handoff_rows(self) -> None:
        self.assertEqual(build_operator_brief_row({"queue_status": "queue_in_progress"}, []), {})

    def test_build_operator_brief_row_uses_first_handoff_frontier(self) -> None:
        row = build_operator_brief_row(
            {"queue_status": "queue_in_progress", "ready_chain_count": "2", "pending_chain_count": "3"},
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "recommended_action": "fill receipt",
                    "expected_outputs": "receipt.md",
                    "chain_status": "execution_chain_ready",
                }
            ],
        )
        self.assertEqual(row["operator_frontier"], "meeteval_compatibility")
        self.assertIn("queue_status=queue_in_progress", row["operator_urgency"])


class FrontierExecutionQueueOperatorBriefWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_operator_brief_row(
            {"queue_status": "queue_complete", "ready_chain_count": "5", "pending_chain_count": "0"},
            [{"frontier_name": "meeteval_compatibility", "recommended_action": "fill", "expected_outputs": "r.md", "chain_status": "ready"}],
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_operator_brief.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, OPERATOR_BRIEF_COLUMNS)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["operator_frontier"], "meeteval_compatibility")
            self.assertIn("Frontier Execution Queue Operator Brief", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
