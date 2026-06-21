from __future__ import annotations

import inspect
import unittest

from src.build_promptable_acoustic_map_dataset import build_rows
from src.generative_audiodepth_common import load_npy, unique_samples
from src.generative_audiodepth_models import PromptablePrototypeModel, build_promptable_prototype


class GenerativeAudioDepthNoSourceLeakageTest(unittest.TestCase):
    def test_student_predict_signature_has_no_source_track_arguments(self) -> None:
        params = set(inspect.signature(PromptablePrototypeModel.predict).parameters)
        self.assertNotIn("spk1_path", params)
        self.assertNotIn("spk2_path", params)
        self.assertNotIn("source_track_1_path", params)
        self.assertNotIn("source_track_2_path", params)

    def test_prediction_works_after_source_paths_removed(self) -> None:
        rows, _, _ = build_rows(limit=3)
        samples = unique_samples(rows)
        model = build_promptable_prototype(samples, rows, load_npy)
        sample = dict(samples[0])
        sample["source_track_1_path"] = ""
        sample["source_track_2_path"] = ""
        pred = model.predict(sample, "OVERLAP_MAP")
        self.assertEqual(pred.shape, (64, 96))

    def test_dataset_marks_mixed_only_student_policy(self) -> None:
        rows, _, _ = build_rows(limit=1)
        self.assertTrue(all(row["student_input_policy"] == "mixed_audio_or_mixed_logmel_only" for row in rows))


if __name__ == "__main__":
    unittest.main()
