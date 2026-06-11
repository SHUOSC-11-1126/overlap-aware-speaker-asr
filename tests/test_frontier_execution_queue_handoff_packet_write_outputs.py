from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_handoff_packet import (
    PACKET_COLUMNS,
    build_packet_rows,
    write_outputs,
)


class FrontierExecutionQueueHandoffPacketWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_packet_csv_json_and_markdown(self) -> None:
        summary = {"queue_status": "queue_complete", "ready_chain_count": "3"}
        rows = build_packet_rows(summary)
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_handoff_packet.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows, summary)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists(), msg=str(path))

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PACKET_COLUMNS)
                self.assertEqual(len(list(reader)), 21)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["section_name"], "execution_queue_status")
            self.assertIn("Frontier Execution Queue Handoff Packet", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
