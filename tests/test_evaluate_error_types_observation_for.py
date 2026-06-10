from __future__ import annotations

import unittest
from typing import Any

from src.evaluate_error_types import observation_for


def _counts(edit_distance: int = 10, dominant: str = "insertion") -> dict[str, Any]:
    return {"edit_distance": edit_distance, "dominant_error_type": dominant}


class EvaluateErrorTypesObservationForTest(unittest.TestCase):
    def test_observation_for_light_overlap_separated_describes_hallucination(self) -> None:
        note = observation_for("LightOverlap", "separated_whisper", _counts(), {}, {})
        self.assertIn("insertion and repetition dominate", note)

    def test_observation_for_separated_benefit_when_edit_distance_improves(self) -> None:
        note = observation_for(
            "HeavyOverlap",
            "separated_whisper",
            _counts(edit_distance=5),
            _counts(edit_distance=12),
            {},
        )
        self.assertIn("separation is beneficial", note)

    def test_observation_for_cleaned_light_overlap_mentions_duplicate_suppression(self) -> None:
        note = observation_for("MidOverlap", "separated_whisper_cleaned", _counts(), {}, _counts())
        self.assertIn("duplicate suppression", note)

    def test_observation_for_cleaned_improvement_when_edit_distance_drops(self) -> None:
        note = observation_for(
            "NoOverlap",
            "separated_whisper_cleaned",
            _counts(edit_distance=4),
            {},
            _counts(edit_distance=8),
        )
        self.assertIn("post-processing reduces", note)


if __name__ == "__main__":
    unittest.main()
