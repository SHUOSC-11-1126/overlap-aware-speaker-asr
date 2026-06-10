from __future__ import annotations

import unittest
from typing import Any

from src.risk_aware_selector import build_selection_row


def _low_risk_features() -> dict[str, Any]:
    return {
        "base_v2_method": "separated_whisper",
        "base_v1_method": "separated_whisper",
        "base_v2_row": {"overlap_level": 0},
        "base_v1_row": {"selected_method": "separated_whisper"},
        "cleaned_text": "",
        "duplicate_removed_count": 0,
        "cleaned_to_separated_ratio": 1.0,
        "text_length_ratio": 1.1,
        "repetition_count": 0,
        "speaker_length_imbalance": 0.1,
        "method_disagreement_score": 0.1,
    }


class RiskAwareSelectorBuildRowTest(unittest.TestCase):
    def test_build_selection_row_assembles_deployable_fields(self) -> None:
        row = build_selection_row("NoOverlap", _low_risk_features())
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["risk_level"], "low")
        self.assertEqual(row["final_selected_method"], "separated_whisper")
        self.assertIn("Reference-free selector", row["notes"])

    def test_build_selection_row_notes_router_disagreement(self) -> None:
        features = _low_risk_features()
        features["base_v1_method"] = "mixed_whisper"
        row = build_selection_row("LightOverlap", features)
        self.assertIn("disagree", row["notes"])


if __name__ == "__main__":
    unittest.main()
