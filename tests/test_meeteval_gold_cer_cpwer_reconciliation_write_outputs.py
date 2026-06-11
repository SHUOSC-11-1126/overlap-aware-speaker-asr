from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_gold_cer_cpwer_reconciliation import RECONCILIATION_COLUMNS, write_outputs


class MeetevalGoldCerCpwerReconciliationWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "case_id": "NoOverlap",
            "hypothesis_source": "separated_whisper",
            "gold_cer": 0.053957,
            "official_cpwer": 0.053957,
            "absolute_gap": 0.0,
            "gap_direction": "match",
            "reconciled": True,
            "tokenization_mode": "character_spaced",
            "result_label": "experimental/frontier",
            "observation": "fixture",
        }
        summary = [{"metric": "reconciliation_rate", "value": "1.0", "label": "experimental/frontier"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_gold_cer_cpwer_reconciliation.PROJECT_ROOT", root):
                paths = write_outputs([row], summary)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RECONCILIATION_COLUMNS)


if __name__ == "__main__":
    unittest.main()
