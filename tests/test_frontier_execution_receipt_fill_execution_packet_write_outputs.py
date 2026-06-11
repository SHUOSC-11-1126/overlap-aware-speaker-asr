from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_execution_packet import (
    PACKET_COLUMNS,
    build_packet_rows,
    write_outputs,
)


class FrontierExecutionReceiptFillExecutionPacketWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        summary = {
            "combined_fill_status": "fill_queue_in_progress",
            "awaiting_fill_count": "2",
        }
        rows = build_packet_rows(summary)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_execution_packet.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows, summary)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PACKET_COLUMNS)
                parsed = list(reader)
                self.assertEqual(len(parsed), 4)
                self.assertEqual(parsed[0]["section_name"], "fill_queue_status")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["packet_order"], "1")
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn("Fill Execution Packet", md_text)
            self.assertIn("fill_queue_in_progress", md_text)


if __name__ == "__main__":
    unittest.main()
