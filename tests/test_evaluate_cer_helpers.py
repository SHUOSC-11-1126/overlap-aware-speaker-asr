from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.config import PROJECT_ROOT
from src import evaluate_cer as evaluate_cer_module
from src.evaluate_cer import (
    build_row,
    compute_cer,
    levenshtein_distance,
    list_verified_cases,
    load_json,
    load_reference,
    normalize_text,
    read_existing_rows,
    rows_for_case,
    sanitize_existing_rows,
    upsert_row,
)


class EvaluateCerHelpersTest(unittest.TestCase):
    def test_normalize_text_strips_speaker_tags_and_punctuation(self) -> None:
        self.assertEqual(normalize_text("[SPEAKER_1] 你好，世界"), "你好世界")

    def test_compute_cer_returns_edit_distance_ratio(self) -> None:
        result = compute_cer("你好世界", "你好世")
        self.assertEqual(result["edit_distance"], 1)
        self.assertEqual(result["reference_length"], 4)
        self.assertEqual(result["cer"], 0.25)

    def test_list_verified_cases_returns_five_gold_cases(self) -> None:
        cases = list_verified_cases()
        self.assertEqual(len(cases), 5)
        self.assertIn("NoOverlap", cases)

    def test_levenshtein_distance_counts_minimum_edits(self) -> None:
        self.assertEqual(levenshtein_distance("你好世界", "你好世"), 1)
        self.assertEqual(levenshtein_distance("", "abc"), 3)

    def test_sanitize_existing_rows_skips_incomplete_rows(self) -> None:
        rows = sanitize_existing_rows(
            [
                {"case_id": "Demo", "method": "mixed_whisper"},
                {"case_id": "", "method": "mixed_whisper"},
            ]
        )
        self.assertEqual(len(rows), 1)

    def test_upsert_row_replaces_matching_case_method(self) -> None:
        rows = [{"case_id": "A", "method": "mixed_whisper", "cer": 0.1}]
        updated = upsert_row(rows, {"case_id": "A", "method": "mixed_whisper", "cer": 0.2})
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["cer"], 0.2)

    def test_build_row_includes_cer_metrics(self) -> None:
        row = build_row(
            "NoOverlap",
            "mixed_whisper",
            "你好世界",
            "你好世",
            PROJECT_ROOT / "results" / "demo.json",
        )
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["method"], "mixed_whisper")
        self.assertEqual(row["cer"], 0.25)

    def test_read_existing_rows_returns_empty_for_missing_path(self) -> None:
        missing = Path("/tmp/__missing_cer_rows__.json")
        self.assertEqual(read_existing_rows(missing), [])

    def test_read_existing_rows_loads_json_list_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "rows.json"
            json_path.write_text(json.dumps([{"case_id": "A", "method": "mixed_whisper"}]), encoding="utf-8")
            rows = read_existing_rows(json_path)
        self.assertEqual(len(rows), 1)

    def test_load_reference_supports_nested_cases_layout(self) -> None:
        nested_cases = {
            "NestedCase": {
                "status": "verified_reference",
                "full_text": "示例文本",
            }
        }
        with unittest.mock.patch.object(evaluate_cer_module, "_load_reference_cases", return_value=nested_cases):
            reference = load_reference("NestedCase")
            self.assertEqual(reference.get("status"), "verified_reference")
            cases = list_verified_cases()
            self.assertEqual(cases, ["NestedCase"])

    def test_load_reference_returns_verified_gold_case(self) -> None:
        reference = load_reference("NoOverlap")
        self.assertEqual(reference.get("status"), "verified_reference")
        self.assertIn("full_text", reference)

    def test_load_json_raises_for_missing_transcript(self) -> None:
        missing = PROJECT_ROOT / "results" / "__missing_transcript__.json"
        with self.assertRaises(FileNotFoundError):
            load_json(missing)

    def test_rows_for_case_includes_mixed_and_separated_methods(self) -> None:
        rows = rows_for_case("NoOverlap")
        methods = {row["method"] for row in rows}
        self.assertIn("mixed_whisper", methods)
        self.assertIn("separated_whisper", methods)
        self.assertTrue(all(row["case_id"] == "NoOverlap" for row in rows))


if __name__ == "__main__":
    unittest.main()
