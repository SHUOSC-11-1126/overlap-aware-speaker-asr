from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.audit_synthetic_benchmark import issue_for_row


class AuditSyntheticBenchmarkIssueForRowTest(unittest.TestCase):
    def test_issue_for_row_flags_high_length_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ref_path = Path(tmp_dir) / "ref.json"
            hyp_path = Path(tmp_dir) / "hyp.json"
            ref_path.write_text("{}", encoding="utf-8")
            hyp_path.write_text("{}", encoding="utf-8")
            issue = issue_for_row(
                {"reference_length": 10, "hypothesis_length": 20, "cer": 0.5},
                reference_text="参考文本",
                hypothesis_text="假设文本更长",
                reference_path=ref_path,
                hypothesis_path=hyp_path,
            )
        self.assertIn("high_length_ratio", issue or "")

    def test_issue_for_row_flags_high_cer_with_normal_length_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ref_path = Path(tmp_dir) / "ref.json"
            hyp_path = Path(tmp_dir) / "hyp.json"
            ref_path.write_text("{}", encoding="utf-8")
            hyp_path.write_text("{}", encoding="utf-8")
            issue = issue_for_row(
                {"reference_length": 100, "hypothesis_length": 110, "cer": 0.95},
                reference_text="参考",
                hypothesis_text="假设",
                reference_path=ref_path,
                hypothesis_path=hyp_path,
            )
        self.assertEqual(issue, "high_cer_low_length_ratio; possible substitution-heavy ASR error")

    def test_issue_for_row_returns_none_for_benign_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ref_path = Path(tmp_dir) / "ref.json"
            hyp_path = Path(tmp_dir) / "hyp.json"
            ref_path.write_text("{}", encoding="utf-8")
            hyp_path.write_text("{}", encoding="utf-8")
            issue = issue_for_row(
                {"reference_length": 100, "hypothesis_length": 105, "cer": 0.2},
                reference_text="参考",
                hypothesis_text="假设",
                reference_path=ref_path,
                hypothesis_path=hyp_path,
            )
        self.assertIsNone(issue)


if __name__ == "__main__":
    unittest.main()
