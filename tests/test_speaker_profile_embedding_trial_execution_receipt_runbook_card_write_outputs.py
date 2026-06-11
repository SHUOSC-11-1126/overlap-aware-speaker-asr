from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_runbook_card import (
    RUNBOOK_COLUMNS,
    build_runbook_card_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptRunbookCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_runbook_card_artifacts(self) -> None:
        row = build_runbook_card_row(
            {
                "operator_case": "NoOverlap",
                "operator_status": "receipt_not_ready",
                "operator_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
                "operator_action": "Reopen readiness rollup after bridge confirmation.",
                "operator_evidence": "results/figures/speaker_profile_embedding_trial_execution_receipt_operator_brief.md",
            },
            {"checklist_order": "1", "next_gate": "Confirm bridge before opening readiness."},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_runbook_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RUNBOOK_COLUMNS)
                self.assertEqual(list(reader)[0]["recommended_case"], "NoOverlap")
            self.assertIn("Runbook Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
