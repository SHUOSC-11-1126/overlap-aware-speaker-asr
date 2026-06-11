from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_handoff_packet import (
    HANDOFF_PACKET_COLUMNS,
    build_handoff_packet_rows,
    write_outputs,
)


class FrontierOperatorNextActionHandoffPacketWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_packet_rows()

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_handoff_packet.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_PACKET_COLUMNS)
                parsed = list(reader)
                self.assertEqual(len(parsed), 6)
                self.assertEqual(parsed[0]["packet_section"], "operator_card")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["packet_section"], "operator_card")
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn("Handoff Packet", md_text)
            self.assertIn("Recommended first-open sequence", md_text)


if __name__ == "__main__":
    unittest.main()
