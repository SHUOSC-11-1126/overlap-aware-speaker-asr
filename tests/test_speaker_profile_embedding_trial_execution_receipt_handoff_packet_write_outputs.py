from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_handoff_packet import (
    PACKET_COLUMNS,
    build_packet_rows,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptHandoffPacketWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_packet_artifacts(self) -> None:
        summary = {
            "case_id": "NoOverlap",
            "readiness_status": "receipt_not_ready",
            "receipt_template_status": "missing",
        }
        rows = build_packet_rows(summary)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_handoff_packet.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows, summary)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PACKET_COLUMNS)
                packet_rows = list(reader)
                self.assertGreater(len(packet_rows), 0)
                self.assertEqual(packet_rows[0]["section_name"], "receipt_readiness")
            self.assertIn("Handoff Packet", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
