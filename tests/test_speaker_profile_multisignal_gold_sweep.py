from __future__ import annotations

import unittest

from src.speaker_profile_multisignal_gold_sweep import build_summary_rows, build_sweep_row


class SpeakerProfileMultisignalGoldSweepTest(unittest.TestCase):
    def test_build_sweep_row_includes_overlap_tier(self) -> None:
        row = build_sweep_row(
            {
                "case_id": "NoOverlap",
                "best_profile_alignment": "swapped",
                "profile_confidence_gap": "0.42",
                "hypothesis_source": "separated_whisper",
            },
            {
                "case_id": "NoOverlap",
                "best_audio_alignment": "swapped",
                "audio_confidence_gap": "0.00001",
            },
        )
        self.assertEqual(row["overlap_tier"], "NoOverlap")
        self.assertEqual(row["combined_signal_status"], "text_swapped_audio_weak")

    def test_build_summary_rows_reports_consensus_rates(self) -> None:
        rows = [
            {
                "alignment_agreement": "agree",
                "audio_support_level": "weak_support",
                "text_best_alignment": "swapped",
                "combined_signal_status": "text_swapped_audio_weak",
            },
            {
                "alignment_agreement": "agree",
                "audio_support_level": "weak_support",
                "text_best_alignment": "swapped",
                "combined_signal_status": "text_swapped_audio_weak",
            },
        ]
        summary = {row["metric"]: row["value"] for row in build_summary_rows(rows)}
        self.assertEqual(summary["gold_case_count"], "2")
        self.assertEqual(summary["signal_agreement_rate"], "1.0")
        self.assertEqual(summary["swapped_text_consensus_rate"], "1.0")
        self.assertEqual(summary["frontier_decision"], "advance_to_narrow_embedding_baseline")


if __name__ == "__main__":
    unittest.main()
