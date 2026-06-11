from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_card import (
    ACTION_COLUMNS,
    SUMMARY_COLUMNS,
    build_action_rows,
    build_summary_row,
    write_outputs,
)


class FrontierOperatorNextActionCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_card_and_summary_artifacts(self) -> None:
        board_rows = [
            {
                "frontier_name": "meeteval_compatibility",
                "go_no_go_state": "go",
                "current_state": "receipt_ready_to_fill",
                "recommended_next_action": "Fill the official receipt with real evidence.",
                "evidence_artifact": "results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md",
                "primary_boundary": "official_benchmark_claims_still_blocked_until_receipt_fill",
            },
            {
                "frontier_name": "external_validation",
                "go_no_go_state": "no_go",
                "current_state": "blocked_by_license_confirmation",
                "recommended_next_action": "Record the license confirmation decision.",
                "evidence_artifact": "results/figures/external_validation_go_no_go_summary.md",
                "primary_boundary": "license_confirmation_pending",
            },
        ]
        go_no_go_summary = {
            "coordination_state": "mixed_ready_state",
            "highest_priority_ready_frontier": "meeteval_compatibility",
            "highest_priority_blocked_frontier": "external_validation",
        }
        action_rows = build_action_rows(board_rows, go_no_go_summary)
        summary_row = build_summary_row(action_rows, go_no_go_summary)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_operator_next_action_card.PROJECT_ROOT", root):
                (
                    card_csv,
                    card_json,
                    summary_csv,
                    summary_json,
                    card_md,
                    summary_md,
                ) = write_outputs(action_rows, summary_row)

            for path in (card_csv, card_json, summary_csv, summary_json, card_md, summary_md):
                self.assertTrue(path.exists())
            with card_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ACTION_COLUMNS)
                self.assertEqual(list(reader)[0]["action_lane"], "ready_lane")
            with summary_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["ready_frontier"], "meeteval_compatibility")
            payload = json.loads(card_json.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["frontier_name"], "meeteval_compatibility")
            self.assertIn("Next-Action Card", card_md.read_text(encoding="utf-8"))
            self.assertIn("Next-Action Summary", summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
