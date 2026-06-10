from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.postprocess_transcript import load_json


class PostprocessTranscriptLoadJsonTest(unittest.TestCase):
    def test_load_json_reads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "payload.json"
            path.write_text(json.dumps({"segments": []}), encoding="utf-8")
            payload = load_json(path)
        self.assertEqual(payload["segments"], [])

    def test_load_json_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "__missing_postprocess_transcript__.json"
        with self.assertRaises(FileNotFoundError):
            load_json(missing)


if __name__ == "__main__":
    unittest.main()
