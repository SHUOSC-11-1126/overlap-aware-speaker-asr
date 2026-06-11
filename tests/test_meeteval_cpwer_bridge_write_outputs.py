from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.meeteval_cpwer_bridge import (
    build_cpwer_bridge_handoff_rows,
    build_cpwer_bridge_receipt_rows,
    build_cpwer_bridge_row,
    build_cpwer_bridge_summary_row,
    write_outputs,
)


class MeetEvalCpwerBridgeWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_writes_bridge_summary_handoff_and_receipt_artifacts(self) -> None:
        bridge_rows = [
            build_cpwer_bridge_row(
                case_id="NoOverlap",
                reference_segments=[
                    {"speaker": "SPEAKER_1", "text": "alpha"},
                    {"speaker": "SPEAKER_2", "text": "beta"},
                ],
                hypothesis_segments=[
                    {"speaker": "SPEAKER_1", "text": "alpha"},
                    {"speaker": "SPEAKER_2", "text": "beta"},
                ],
                hypothesis_source="separated_whisper",
            )
        ]
        summary_row = build_cpwer_bridge_summary_row(bridge_rows, "single_verified_case")
        handoff_rows = build_cpwer_bridge_handoff_rows(bridge_rows, summary_row)
        receipt_rows = build_cpwer_bridge_receipt_rows(handoff_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.meeteval_cpwer_bridge.PROJECT_ROOT", root):
                paths = write_outputs(bridge_rows, summary_row, handoff_rows, receipt_rows)
                bridge_csv, bridge_json, bridge_md = paths[0], paths[1], paths[2]
                summary_md = paths[5]
                receipt_json = paths[9]
                self.assertTrue(bridge_csv.exists())
                self.assertTrue(bridge_json.exists())
                self.assertTrue(bridge_md.exists())
                self.assertTrue(summary_md.exists())
                self.assertTrue(receipt_json.exists())
                with bridge_csv.open(encoding="utf-8-sig", newline="") as handle:
                    loaded_csv = list(csv.DictReader(handle))
                loaded_bridge = json.loads(bridge_json.read_text(encoding="utf-8"))
                bridge_markdown = bridge_md.read_text(encoding="utf-8")
                receipt_payload = json.loads(receipt_json.read_text(encoding="utf-8"))
        self.assertEqual(loaded_csv[0]["case_id"], "NoOverlap")
        self.assertEqual(loaded_bridge[0]["best_mapping"], "direct")
        self.assertIn("experimental/frontier", bridge_markdown)
        self.assertEqual(receipt_payload[0]["execution_status"], "bridge_complete")


if __name__ == "__main__":
    unittest.main()
