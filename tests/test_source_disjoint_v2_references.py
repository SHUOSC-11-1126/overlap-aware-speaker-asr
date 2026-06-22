import unittest

from src.source_disjoint_v2_common import audit_source_disjoint_v2_references, read_csv, REFERENCE_AUDIT


class SourceDisjointV2ReferenceAuditTest(unittest.TestCase):
    def test_silver_plus_is_not_claimed_as_gold(self):
        audit_source_disjoint_v2_references()
        rows = read_csv(REFERENCE_AUDIT)
        self.assertTrue(rows)
        self.assertTrue(all(row["claimed_as_gold"] == "False" for row in rows))
        self.assertEqual(sum(row["reference_type"] == "manual_gold" for row in rows), 0)


if __name__ == "__main__":
    unittest.main()
