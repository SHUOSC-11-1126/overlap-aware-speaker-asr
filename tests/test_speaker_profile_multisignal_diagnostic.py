from __future__ import annotations

import unittest

from src.speaker_profile_multisignal_diagnostic import (
    build_multisignal_row,
    build_multisignal_summary_row,
)


class SpeakerProfileMultisignalDiagnosticTest(unittest.TestCase):
    def test_build_multisignal_row_marks_weak_audio_support_when_audio_gap_is_tiny(self) -> None:
        row = build_multisignal_row(
            {
                "case_id": "NoOverlap",
                "best_profile_alignment": "swapped",
                "profile_confidence_gap": "0.422118",
                "hypothesis_source": "separated_whisper",
            },
            {
                "case_id": "NoOverlap",
                "best_audio_alignment": "swapped",
                "audio_confidence_gap": "0.000012",
            },
        )

        self.assertEqual(row["alignment_agreement"], "agree")
        self.assertEqual(row["audio_support_level"], "weak_support")
        self.assertEqual(row["combined_signal_status"], "text_swapped_audio_weak")
        self.assertIn("narrow embedding baseline", row["recommended_next_step"])

    def test_build_multisignal_summary_row_counts_weak_support_cases(self) -> None:
        row = build_multisignal_summary_row(
            [
                {
                    "case_id": "NoOverlap",
                    "alignment_agreement": "agree",
                    "audio_support_level": "weak_support",
                    "combined_signal_status": "text_swapped_audio_weak",
                },
                {
                    "case_id": "HeavyOverlap",
                    "alignment_agreement": "agree",
                    "audio_support_level": "weak_support",
                    "combined_signal_status": "text_swapped_audio_weak",
                },
            ]
        )

        self.assertEqual(row["agreement_count"], "2")
        self.assertEqual(row["weak_support_count"], "2")
        self.assertEqual(row["frontier_decision"], "advance_to_narrow_embedding_baseline")


if __name__ == "__main__":
    unittest.main()
