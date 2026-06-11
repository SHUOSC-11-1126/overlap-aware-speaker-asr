from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_correct import CSV_COLUMNS, write_outputs


def _sample_qualitative_row() -> dict[str, str]:
    return {
        "case_id": "FixtureCase",
        "label": "qualitative/demo",
        "risk_explanation": "fixture risk note",
        "candidate_repair": "narrow qualitative trial",
        "uncertainty_note": "not evaluated on gold",
    }


class LlmCorrectWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_qualitative_summary_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_correct.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_qualitative_row()])

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, md_path = outputs[0], outputs[1], outputs[2]
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["label"], "qualitative/demo")
            self.assertIn("LLM Critic Qualitative", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
