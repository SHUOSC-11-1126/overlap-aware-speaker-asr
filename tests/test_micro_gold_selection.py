import unittest

from src.source_disjoint_v2_common import MICRO_GOLD_SHEET, read_csv, select_micro_gold_candidates


class MicroGoldSelectionTest(unittest.TestCase):
    def test_micro_gold_sheet_is_unannotated(self):
        select_micro_gold_candidates()
        rows = read_csv(MICRO_GOLD_SHEET)
        self.assertTrue(rows)
        self.assertTrue(all(row["verification_status"] == "prepared_not_annotated" for row in rows))
        self.assertTrue(all(row["manual_reference_spk1"] == "" and row["manual_reference_spk2"] == "" for row in rows))


if __name__ == "__main__":
    unittest.main()
