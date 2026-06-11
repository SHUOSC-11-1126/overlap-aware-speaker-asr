from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_tokenization_adaptation_handoff_packet import (
    PACKET_COLUMNS,
    build_packet_rows,
    write_outputs,
)


class MeetEvalTokenizationAdaptationHandoffPacketWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_packet_artifacts(self) -> None:
        summary = {
            "handoff_status": "tokenization_adaptation_handoff_ready",
            "aligned_count": "5",
            "total_count": "5",
            "queue_status": "queue_complete",
        }
        rows = build_packet_rows(summary)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_tokenization_adaptation_handoff_packet.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows, summary)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PACKET_COLUMNS)
                self.assertGreater(len(list(reader)), 10)
            self.assertIn("Handoff Packet", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
