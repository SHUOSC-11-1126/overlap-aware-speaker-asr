from __future__ import annotations

import unittest
import unittest.mock

from src.evaluate_speaker_cer import METHOD_ORDER, rows_for_cases


class EvaluateSpeakerCerRowsForCasesTest(unittest.TestCase):
    def test_rows_for_cases_skips_missing_transcripts_with_warning(self) -> None:
        def fake_build_row(case_id: str, method: str) -> dict[str, object]:
            if case_id == "MissingCase":
                raise FileNotFoundError(f"missing transcript for {case_id}")
            return {"case_id": case_id, "method": method, "speaker_macro_cer": 0.1}

        with unittest.mock.patch("src.evaluate_speaker_cer.build_row", side_effect=fake_build_row):
            with unittest.mock.patch("builtins.print") as print_mock:
                rows = rows_for_cases(["NoOverlap", "MissingCase"])

        self.assertEqual(len(rows), len(METHOD_ORDER))
        self.assertTrue(any(row["case_id"] == "NoOverlap" for row in rows))
        self.assertFalse(any(row["case_id"] == "MissingCase" for row in rows))
        self.assertTrue(print_mock.called)


if __name__ == "__main__":
    unittest.main()
