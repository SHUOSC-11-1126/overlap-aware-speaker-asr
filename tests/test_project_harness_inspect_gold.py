from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.project_harness import GOLD_CASES, inspect_gold_cases


class ProjectHarnessInspectGoldTest(unittest.TestCase):
    def test_inspect_gold_cases_returns_false_when_reference_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                result = inspect_gold_cases()
        self.assertEqual(result, {case: False for case in GOLD_CASES})

    def test_inspect_gold_cases_returns_false_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            ref_dir = root / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "reference_transcripts.json").write_text("{not valid json", encoding="utf-8")
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                result = inspect_gold_cases()
        self.assertEqual(result, {case: False for case in GOLD_CASES})

    def test_inspect_gold_cases_returns_false_for_non_dict_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            ref_dir = root / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "reference_transcripts.json").write_text(json.dumps(["bad"]), encoding="utf-8")
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                result = inspect_gold_cases()
        self.assertEqual(result, {case: False for case in GOLD_CASES})

    def test_inspect_gold_cases_marks_verified_reference_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            ref_dir = root / "references"
            ref_dir.mkdir(parents=True)
            payload = {
                "cases": {
                    "NoOverlap": {"status": "verified_reference"},
                    "LightOverlap": {"status": "draft"},
                }
            }
            (ref_dir / "reference_transcripts.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                result = inspect_gold_cases()
        self.assertTrue(result["NoOverlap"])
        self.assertFalse(result["LightOverlap"])
        self.assertFalse(result["MidOverlap"])


if __name__ == "__main__":
    unittest.main()
