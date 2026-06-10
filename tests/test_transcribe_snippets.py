from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.transcribe_snippets import load_existing_rows, snippet_transcript_path


class TranscribeSnippetsTest(unittest.TestCase):
    def test_snippet_transcript_path_under_results(self) -> None:
        path = snippet_transcript_path("demo_snippet")
        self.assertEqual(
            path,
            PROJECT_ROOT / "results" / "snippet_transcripts" / "demo_snippet_whisper.json",
        )

    def test_load_existing_rows_returns_empty_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "__missing_snippet_rows__.csv"
        self.assertEqual(load_existing_rows(missing), [])

    def test_load_existing_rows_reads_csv_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["snippet_id", "model"])
                writer.writeheader()
                writer.writerow({"snippet_id": "s1", "model": "whisper-tiny"})

            rows = load_existing_rows(csv_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["snippet_id"], "s1")
            self.assertEqual(rows[0]["model"], "whisper-tiny")


if __name__ == "__main__":
    unittest.main()
