from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.rag_repair import CSV_COLUMNS, main


def _sample_rag_rows() -> list[dict[str, object]]:
    return [
        {
            "case_id": "FixtureCase",
            "query_text": "fixture query",
            "retrieved_context": "fixture context",
            "similarity_score": 0.88,
            "retrieval_method": "simple_text_similarity",
        }
    ]


class RagRepairMainTest(unittest.TestCase):
    def test_main_writes_demo_csv_json_and_summary_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "results" / "figures").mkdir(parents=True)
            with patch("src.rag_repair.PROJECT_ROOT", root), patch(
                "src.rag_repair.demo_rag_retrieval", return_value=_sample_rag_rows()
            ):
                main()

            csv_path = root / "results" / "tables" / "rag_retrieval_demo.csv"
            json_path = root / "results" / "tables" / "rag_retrieval_demo.json"
            summary_path = root / "results" / "figures" / "rag_retrieval_demo.md"
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(summary_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["retrieval_method"], "simple_text_similarity")
            self.assertIn("RAG Retrieval Demo", summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
