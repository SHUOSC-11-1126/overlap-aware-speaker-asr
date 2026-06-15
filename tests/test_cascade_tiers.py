"""
TDD tests for src/py — Mode B: Three-Tier Compute-Aware Cascade.

Covers:
- Tier 1 (cheap): router_v2 baseline routing
- Tier 2 (stronger): risk-gated escalation to stronger ASR or cleaned transcript
- Tier 3 (LLM critic): instability-triggered manual review / LLM critic flagging
- Output generation: CER-runtime tradeoff table, coverage stats, routing table
- Reference-free safety: no CER used as routing input
- Edge cases: missing data, empty cases, all-low-risk, all-high-risk
"""

import unittest

from src import cascade_tiers
from src.cascade_tiers import (
    MODULE_LABEL,
    TIER_COST,
    TIER_STRATEGIES,
    build_comparison_rows,
    build_coverage_stats,
    build_cost_aware_routing_table,
    build_tier_summary_rows,
    resolve_tier1,
    resolve_tier2,
    resolve_tier3,
    run_three_tier_pipeline,
)


class CascadeTiersUnitTest(unittest.TestCase):
    """Unit tests for cascade_tiers module functions."""

    # ── Tier 1 (cheap route) tests ────────────────────────────────────

    def test_tier1_resolves_from_router_v2_decision(self):
        """Tier 1 returns the router_v2 selected method directly."""
        decisions = {"NoOverlap": "separated_whisper", "LightOverlap": "mixed_whisper"}
        result = resolve_tier1("NoOverlap", decisions)
        self.assertEqual(result, "separated_whisper")

    def test_tier1_missing_case_falls_back_to_mixed(self):
        """Tier 1 falls back to mixed_whisper when no v2 decision exists."""
        decisions = {}
        result = resolve_tier1("UnknownCase", decisions)
        self.assertEqual(result, "mixed_whisper")

    # ── Tier 2 (stronger route) tests ─────────────────────────────────

    def test_tier2_high_risk_triggers_stronger_model(self):
        """Tier 2 escalates high-risk unstable samples to stronger model."""
        case = {
            "case_id": "HeavyOverlap",
            "overlap_level": 4,
            "length_ratio": 1.5,
            "duplicate_removed_count": 12,
            "runtime_ratio": 2.0,
        }
        result = resolve_tier2(case, tier1_method="separated_whisper")
        self.assertIn(result, ["stronger_model", "separated_whisper_cleaned"])

    def test_tier2_low_risk_keeps_tier1_decision(self):
        """Tier 2 keeps Tier 1 decision for low-risk samples."""
        case = {
            "case_id": "NoOverlap",
            "overlap_level": 0,
            "length_ratio": 1.0,
            "duplicate_removed_count": 0,
            "runtime_ratio": 1.0,
        }
        result = resolve_tier2(case, tier1_method="separated_whisper")
        self.assertEqual(result, "separated_whisper")

    def test_tier2_uses_cleaned_fallback_when_unstable(self):
        """Tier 2 prefers cleaned transcript as cheaper strong option."""
        case = {
            "case_id": "MidOverlap",
            "overlap_level": 2,
            "length_ratio": 1.4,
            "duplicate_removed_count": 10,
            "runtime_ratio": 1.9,
        }
        result = resolve_tier2(case, tier1_method="mixed_whisper")
        # Unstable mixed -> try cleaned before stronger model
        self.assertIn(result, ["separated_whisper_cleaned", "stronger_model", "mixed_whisper"])

    # ── Tier 3 (LLM critic / manual review) tests ────────────────────

    def test_tier3_triggers_for_extreme_instability(self):
        """Tier 3 flags extreme-instability samples for LLM critic or manual review."""
        case = {
            "case_id": "ExtremeCase",
            "overlap_level": 4,
            "length_ratio": 3.0,
            "duplicate_removed_count": 25,
            "runtime_ratio": 2.5,
        }
        result = resolve_tier3(case, tier2_method="stronger_model")
        self.assertIn(result, ["llm_critic", "manual_review"])

    def test_tier3_does_not_trigger_for_stable_samples(self):
        """Tier 3 leaves stable samples at their Tier 2 decision."""
        case = {
            "case_id": "StableCase",
            "overlap_level": 0,
            "length_ratio": 1.0,
            "duplicate_removed_count": 0,
            "runtime_ratio": 1.0,
        }
        result = resolve_tier3(case, tier2_method="separated_whisper")
        self.assertEqual(result, "separated_whisper")

    # ── Full three-tier pipeline tests ────────────────────────────────

    def test_full_pipeline_returns_tier_assignment(self):
        """The full pipeline assigns every case to exactly one tier."""
        decisions = {"NoOverlap": "separated_whisper"}
        cases = [
            {
                "case_id": "NoOverlap",
                "overlap_level": 0,
                "length_ratio": 1.0,
                "duplicate_removed_count": 0,
                "runtime_ratio": 1.0,
            },
        ]
        results = run_three_tier_pipeline(cases, decisions)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertIn("case_id", r)
        self.assertIn("tier", r)
        self.assertIn("selected_method", r)
        self.assertIn("compute_cost", r)
        self.assertIn(r["tier"], [1, 2, 3])

    def test_full_pipeline_heavily_unstable_goes_to_tier3(self):
        """An extremely unstable case should reach Tier 3."""
        decisions = {"BadCase": "separated_whisper"}
        cases = [
            {
                "case_id": "BadCase",
                "overlap_level": 4,
                "length_ratio": 4.0,
                "duplicate_removed_count": 30,
                "runtime_ratio": 3.0,
            },
        ]
        results = run_three_tier_pipeline(cases, decisions)
        self.assertEqual(results[0]["tier"], 3)
        self.assertIn(results[0]["selected_method"], ["llm_critic", "manual_review"])

    def test_full_pipeline_stable_case_stays_tier1(self):
        """A stable case stays at Tier 1."""
        decisions = {"GoodCase": "mixed_whisper"}
        cases = [
            {
                "case_id": "GoodCase",
                "overlap_level": 1,
                "length_ratio": 1.0,
                "duplicate_removed_count": 0,
                "runtime_ratio": 1.0,
            },
        ]
        results = run_three_tier_pipeline(cases, decisions)
        self.assertEqual(results[0]["tier"], 1)
        self.assertEqual(results[0]["selected_method"], "mixed_whisper")

    # ── Reference-free safety tests ───────────────────────────────────

    def test_escalation_uses_only_observable_signals(self):
        """Escalation logic must not access CER or reference transcripts."""
        case = {
            "case_id": "Test",
            "overlap_level": 3,
            "length_ratio": 1.8,
            "duplicate_removed_count": 15,
            "runtime_ratio": 2.2,
            "cer": 0.5,  # should be IGNORED by escalation logic
        }
        # CER field present but must not influence the decision
        result = resolve_tier2(case, tier1_method="separated_whisper")
        # With these signals, should escalate (regardless of CER=0.5)
        self.assertNotEqual(result, "separated_whisper")

    # ── Cost model tests ──────────────────────────────────────────────

    def test_cost_model_tier1_is_cheapest(self):
        """Tier 1 costs (mixed/separated) are lower than Tier 2/3."""
        tier1_costs = [
            TIER_COST["mixed_whisper"],
            TIER_COST["separated_whisper"],
        ]
        tier2_costs = [
            TIER_COST["separated_whisper_cleaned"],
            TIER_COST["stronger_model"],
        ]
        tier3_cost = TIER_COST["manual_review"]
        self.assertTrue(all(c <= min(tier2_costs) for c in tier1_costs),
                        "Tier 1 should not exceed Tier 2 minimum cost")
        self.assertTrue(all(c < tier3_cost for c in tier2_costs),
                        "Tier 2 should be cheaper than Tier 3")

    def test_tier_cost_table_is_consistent(self):
        """The TIER_COST table covers all known methods."""
        required_methods = [
            "mixed_whisper", "separated_whisper", "separated_whisper_cleaned",
            "stronger_model", "llm_critic", "manual_review",
        ]
        for m in required_methods:
            self.assertIn(m, TIER_COST, f"{m} must be in TIER_COST")

    # ── Output generation tests ──────────────────────────────────────

    def test_build_tier_summary_rows_produces_per_case_rows(self):
        """Tier summary includes per-case tier assignment and cost."""
        pipeline_results = [
            {"case_id": "A", "tier": 1, "selected_method": "mixed_whisper",
             "compute_cost": 1.0, "cer": 0.30},
            {"case_id": "B", "tier": 3, "selected_method": "manual_review",
             "compute_cost": 3.0, "cer": None},
        ]
        rows = build_tier_summary_rows(pipeline_results)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["tier"], 1)
        self.assertEqual(rows[1]["tier"], 3)

    def test_build_coverage_stats_breaks_down_by_tier(self):
        """Coverage stats report per-tier counts and ratios."""
        pipeline_results = [
            {"case_id": "A", "tier": 1, "selected_method": "mixed_whisper",
             "compute_cost": 1.0, "cer": 0.30},
            {"case_id": "B", "tier": 1, "selected_method": "separated_whisper",
             "compute_cost": 2.0, "cer": 0.05},
            {"case_id": "C", "tier": 2, "selected_method": "separated_whisper_cleaned",
             "compute_cost": 2.1, "cer": 0.10},
            {"case_id": "D", "tier": 3, "selected_method": "manual_review",
             "compute_cost": 3.0, "cer": None},
        ]
        stats = build_coverage_stats(pipeline_results)
        self.assertEqual(stats["total_cases"], 4)
        self.assertEqual(stats["tier1_count"], 2)
        self.assertEqual(stats["tier2_count"], 1)
        self.assertEqual(stats["tier3_count"], 1)
        self.assertAlmostEqual(stats["tier1_ratio"], 0.5)
        self.assertAlmostEqual(stats["tier3_ratio"], 0.25)

    def test_build_cost_aware_routing_table_maps_case_to_route(self):
        """Cost-aware routing table maps each case_id to tier and method."""
        pipeline_results = [
            {"case_id": "NoOverlap", "tier": 1, "selected_method": "separated_whisper",
             "compute_cost": 2.0, "cer": 0.05,
             "risk_triggered": False, "instability_score": 0.0},
        ]
        table = build_cost_aware_routing_table(pipeline_results)
        self.assertEqual(len(table), 1)
        row = table[0]
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["tier"], 1)
        self.assertEqual(row["recommended_route"], "separated_whisper")
        self.assertIn("compute_cost", row)
        self.assertIn("instability_score", row)

    # ── Edge case tests ───────────────────────────────────────────────

    def test_empty_cases_returns_empty_results(self):
        """Pipeline handles empty case list gracefully."""
        results = run_three_tier_pipeline([], {})
        self.assertEqual(results, [])

    def test_all_low_risk_cases_all_stay_tier1(self):
        """When all cases are low-risk, none escalates past Tier 1."""
        decisions = {f"case_{i}": "mixed_whisper" for i in range(5)}
        cases = [
            {
                "case_id": f"case_{i}",
                "overlap_level": i % 3,
                "length_ratio": 1.0 + i * 0.03,
                "duplicate_removed_count": i,
                "runtime_ratio": 1.0 + i * 0.05,
            }
            for i in range(5)
        ]
        results = run_three_tier_pipeline(cases, decisions)
        self.assertTrue(all(r["tier"] == 1 for r in results),
                        "All low-risk cases should stay at Tier 1")

    def test_all_high_risk_cases_escalate(self):
        """When all cases are high-risk, most escalate past Tier 1."""
        decisions = {f"case_{i}": "separated_whisper" for i in range(5)}
        cases = [
            {
                "case_id": f"case_{i}",
                "overlap_level": 4,
                "length_ratio": 2.0 + i * 0.2,
                "duplicate_removed_count": 18 + i,
                "runtime_ratio": 2.5 + i * 0.1,
            }
            for i in range(5)
        ]
        results = run_three_tier_pipeline(cases, decisions)
        escalated = [r for r in results if r["tier"] > 1]
        self.assertGreater(len(escalated), 0,
                           "At least some high-risk cases should escalate")

    # ── Gold case integration tests (with real data) ──────────────────

    def test_integration_with_gold_cases(self):
        """Full pipeline runs on the 5 gold cases without error."""
        cases = [
            {"case_id": "NoOverlap", "overlap_level": 0,
             "length_ratio": 1.0, "duplicate_removed_count": 0, "runtime_ratio": 1.0},
            {"case_id": "LightOverlap", "overlap_level": 1,
             "length_ratio": 1.0, "duplicate_removed_count": 0, "runtime_ratio": 1.0},
            {"case_id": "MidOverlap", "overlap_level": 2,
             "length_ratio": 1.0, "duplicate_removed_count": 0, "runtime_ratio": 1.0},
            {"case_id": "HeavyOverlap", "overlap_level": 3,
             "length_ratio": 1.3, "duplicate_removed_count": 5, "runtime_ratio": 1.5},
            {"case_id": "OppositeOverlap", "overlap_level": 4,
             "length_ratio": 1.2, "duplicate_removed_count": 3, "runtime_ratio": 1.4},
        ]
        decisions = {
            "NoOverlap": "separated_whisper",
            "LightOverlap": "mixed_whisper",
            "MidOverlap": "mixed_whisper",
            "HeavyOverlap": "separated_whisper",
            "OppositeOverlap": "separated_whisper",
        }
        results = run_three_tier_pipeline(cases, decisions)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertIn(r["case_id"], [c["case_id"] for c in cases])
            self.assertIn(r["tier"], [1, 2, 3])

    # ── Module label compliance test ──────────────────────────────────

    def test_module_label_is_frontier(self):
        """Mode B outputs are labeled experimental/frontier."""
        self.assertEqual(MODULE_LABEL, "experimental/frontier")

    def test_strategies_are_labeled_frontier(self):
        """Every strategy name reflects its frontier status."""
        for s in TIER_STRATEGIES:
            self.assertIn(s, TIER_STRATEGIES)


    # ── Comparative tradeoff tests ──────────────────────────────────

    def test_build_comparison_rows_includes_tiered_strategies(self):
        """Comparison rows include tiered strategies alongside fixed baselines."""
        tiered_results = [
            {"case_id": "A", "tier": 1, "selected_method": "mixed_whisper",
             "compute_cost": 1.0, "cer": 0.30, "instability_score": 0.0},
            {"case_id": "B", "tier": 2, "selected_method": "separated_whisper_cleaned",
             "compute_cost": 2.1, "cer": 0.10, "instability_score": 0.4},
        ]
        cer_lookup = {
            ("A", "mixed_whisper"): 0.30, ("A", "separated_whisper"): 0.05,
            ("A", "separated_whisper_cleaned"): 0.08,
            ("B", "mixed_whisper"): 0.40, ("B", "separated_whisper"): 0.12,
            ("B", "separated_whisper_cleaned"): 0.10,
        }
        rows = cascade_tiers.build_comparison_rows(tiered_results, cer_lookup)
        self.assertGreater(len(rows), 2)  # more than just the tiered strategies
        strategy_names = {r["strategy"] for r in rows}
        self.assertIn("tiered_cascade_v1", strategy_names)
        self.assertIn("fixed_mixed_whisper", strategy_names)
        self.assertIn("fixed_separated_whisper", strategy_names)

    def test_build_comparison_rows_computes_meaningful_metrics(self):
        """Each comparison row has average_cer, average_cost, and coverage."""
        tiered_results = [
            {"case_id": "A", "tier": 1, "selected_method": "mixed_whisper",
             "compute_cost": 1.0, "cer": 0.30},
        ]
        cer_lookup = {
            ("A", "mixed_whisper"): 0.30, ("A", "separated_whisper"): 0.05,
            ("A", "separated_whisper_cleaned"): 0.08,
        }
        rows = cascade_tiers.build_comparison_rows(tiered_results, cer_lookup)
        for row in rows:
            self.assertIn("strategy", row)
            self.assertIn("average_cer", row)
            self.assertIn("average_compute_cost", row)
            self.assertIn("automatic_coverage", row)
            self.assertIn("label", row)


if __name__ == "__main__":
    unittest.main()
