from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.evaluate_synthetic_routing import load_cleaned_rows


class EvaluateSyntheticRoutingLoadCleanedTest(unittest.TestCase):
    def test_load_cleaned_rows_returns_empty_for_missing_directory(self) -> None:
        missing = Path(tempfile.gettempdir()) / "__missing_cleaned_dir__"
        self.assertEqual(load_cleaned_rows(missing), {})

    def test_load_cleaned_rows_indexes_payloads_by_sample_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cleaned_dir = Path(tmp_dir)
            payload_path = cleaned_dir / "sample_001_separated_speaker_transcript_cleaned.json"
            payload_path.write_text(
                json.dumps({"sample_id": "sample_001", "cleaned_full_text": "demo"}),
                encoding="utf-8",
            )
            rows = load_cleaned_rows(cleaned_dir)
        self.assertEqual(rows["sample_001"]["sample_id"], "sample_001")


if __name__ == "__main__":
    unittest.main()
