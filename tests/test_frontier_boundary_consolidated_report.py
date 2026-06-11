from __future__ import annotations

import unittest

from src.frontier_boundary_consolidated_report import build_finding_rows, metric_map


class FrontierBoundaryConsolidatedReportTest(unittest.TestCase):
    def test_metric_map_extracts_values(self) -> None:
        rows = [{"metric": "router_oracle_match_rate", "value": "1.0"}]
        self.assertEqual(metric_map(rows)["router_oracle_match_rate"], "1.0")

    def test_build_finding_rows_has_three_findings(self) -> None:
        findings = build_finding_rows()
        self.assertEqual(len(findings), 3)
        self.assertEqual(findings[0]["finding_id"], "F1")


if __name__ == "__main__":
    unittest.main()
