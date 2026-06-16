from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src import project_harness
from src.project_harness import GOLD_CASES, inspect_gold_cases


class InspectGoldTest(unittest.TestCase):
    def _root(self, d):
        return unittest.mock.patch.object(project_harness, "PROJECT_ROOT", Path(d))

    def test_returns_false_when_reference_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d, self._root(d):
            self.assertEqual(inspect_gold_cases(), {c: False for c in GOLD_CASES})

    def test_returns_false_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as d, self._root(d):
            ref = Path(d) / "references"
            ref.mkdir()
            (ref / "reference_transcripts.json").write_text("{bad", encoding="utf-8")
            self.assertEqual(inspect_gold_cases(), {c: False for c in GOLD_CASES})

    def test_returns_false_for_non_dict_payload(self) -> None:
        with tempfile.TemporaryDirectory() as d, self._root(d):
            ref = Path(d) / "references"
            ref.mkdir()
            (ref / "reference_transcripts.json").write_text("[]", encoding="utf-8")
            self.assertEqual(inspect_gold_cases(), {c: False for c in GOLD_CASES})

    def test_marks_verified_reference_cases(self) -> None:
        with tempfile.TemporaryDirectory() as d, self._root(d):
            ref = Path(d) / "references"
            ref.mkdir()
            payload = {c: {"status": "verified_reference"} for c in GOLD_CASES}
            (ref / "reference_transcripts.json").write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(inspect_gold_cases(), {c: True for c in GOLD_CASES})


if __name__ == "__main__":
    unittest.main()
