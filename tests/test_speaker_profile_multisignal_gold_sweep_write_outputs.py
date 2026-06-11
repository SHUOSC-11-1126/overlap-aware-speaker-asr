from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_multisignal_gold_sweep import SWEEP_COLUMNS, write_outputs


class SpeakerProfileMultisignalGoldSweepWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "case_id": "LightOverlap",
            "overlap_tier": "LightOverlap",
            "overlap_ratio_anchor": "0.15",
            "hypothesis_source": "separated_whisper_cleaned",
            "text_best_alignment": "swapped",
            "audio_best_alignment": "swapped",
            "text_confidence_gap": "0.41",
            "audio_confidence_gap": "0.00001",
            "alignment_agreement": "agree",
            "audio_support_level": "weak_support",
            "combined_signal_status": "text_swapped_audio_weak",
            "recommended_next_step": "narrow baseline",
            "result_label": "experimental/frontier",
        }
        summary = [{"metric": "gold_case_count", "value": "1", "label": "stable/gold"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_multisignal_gold_sweep.PROJECT_ROOT", root):
                paths = write_outputs([row], summary)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SWEEP_COLUMNS)


if __name__ == "__main__":
    unittest.main()
