from __future__ import annotations

import unittest

from src.build_promptable_acoustic_map_dataset import build_rows
from src.generative_audiodepth_common import TASKS


class GenerativeAudioDepthDatasetTest(unittest.TestCase):
    def test_build_rows_emits_all_tasks_per_sample(self) -> None:
        rows, quality, audit = build_rows(limit=2)
        self.assertEqual(audit["usable_samples"], 2)
        self.assertEqual(len(rows), 2 * len(TASKS))
        self.assertEqual(len(quality), len(rows))
        self.assertEqual({row["target_task"] for row in rows}, set(TASKS))

    def test_route_regret_is_sample_level_not_local_map(self) -> None:
        rows, _, _ = build_rows(limit=1)
        route_regret = next(row for row in rows if row["target_task"] == "ROUTE_REGRET")
        self.assertEqual(route_regret["target_scope"], "sample_level_vector")
        self.assertIn("real_whisper", route_regret["target_quality"])


if __name__ == "__main__":
    unittest.main()
