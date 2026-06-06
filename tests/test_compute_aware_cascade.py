from __future__ import annotations

import unittest

from src.compute_aware_cascade import (
    build_decision_matrix_rows,
    build_artifact_index_lines,
    build_artifact_index_rows,
    build_profile_playbook_lines,
    build_profile_playbook_rows,
    build_benchmark_readiness_lines,
    build_benchmark_plan_lines,
    build_benchmark_plan_rows,
    build_benchmark_readiness_rows,
    build_frontier_report_lines,
    DEFAULT_COST_PROXY,
    build_recommendation_family_stability_rows,
    build_recommendation_rows,
    build_recommendation_stability_rows,
    build_robustness_gap_rows,
    build_strategy_rows,
    build_synthetic_scope_rows,
    choose_cleaned_preferred_method,
    compute_method_cost,
    choose_budget_cascade_method,
    classify_pareto_rows,
    summarize_runtime_normalization,
    summarize_runtime_sources,
)


class ComputeAwareCascadeTest(unittest.TestCase):
    def test_compute_method_cost_prefers_observed_runtime(self) -> None:
        row = {
            "mixed_runtime_sec": "4.0",
            "separated_runtime_sec": "9.0",
            "cleaned_runtime_sec": "9.5",
        }
        self.assertEqual(compute_method_cost("mixed_whisper", row), 4.0)
        self.assertEqual(compute_method_cost("separated_whisper", row), 9.0)
        self.assertEqual(compute_method_cost("separated_whisper_cleaned", row), 9.5)

    def test_compute_method_cost_falls_back_to_proxy(self) -> None:
        self.assertEqual(compute_method_cost("mixed_whisper", {}), DEFAULT_COST_PROXY["mixed_whisper"])
        self.assertEqual(compute_method_cost("manual_review", {}), DEFAULT_COST_PROXY["manual_review"])

    def test_budget_cascade_uses_reference_free_signals(self) -> None:
        self.assertEqual(choose_budget_cascade_method(0, "low"), "separated_whisper")
        self.assertEqual(choose_budget_cascade_method(1, "high"), "mixed_whisper")
        self.assertEqual(choose_budget_cascade_method(3, "medium"), "separated_whisper_cleaned")

    def test_build_strategy_rows_excludes_manual_review_cer_but_counts_coverage(self) -> None:
        cases = [
            {"case_id": "A", "overlap_level": 0, "risk_level": "low"},
            {"case_id": "B", "overlap_level": 2, "risk_level": "high"},
        ]
        decisions = {
            "router_v2_costed": {"A": "separated_whisper", "B": "mixed_whisper"},
            "risk_aware_costed": {"A": "separated_whisper", "B": "manual_review"},
        }
        cer_lookup = {
            ("A", "mixed_whisper"): 0.5,
            ("A", "separated_whisper"): 0.1,
            ("A", "separated_whisper_cleaned"): 0.2,
            ("B", "mixed_whisper"): 0.3,
            ("B", "separated_whisper"): 0.7,
            ("B", "separated_whisper_cleaned"): 0.6,
        }
        runtime_lookup = {
            "A": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.1},
            "B": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.1},
        }

        rows = build_strategy_rows(cases, decisions, cer_lookup, runtime_lookup)
        risk_row = next(row for row in rows if row["strategy"] == "risk_aware_costed")

        self.assertEqual(risk_row["manual_review_count"], 1)
        self.assertEqual(risk_row["automatic_coverage"], 0.5)
        self.assertEqual(risk_row["sample_count"], 1)
        self.assertEqual(risk_row["average_cer"], 0.1)

    def test_cleaned_preferred_method_uses_reference_free_signals(self) -> None:
        self.assertEqual(choose_cleaned_preferred_method(3, 0), "separated_whisper_cleaned")
        self.assertEqual(choose_cleaned_preferred_method(1, 2), "separated_whisper_cleaned")
        self.assertEqual(choose_cleaned_preferred_method(2, 0), "mixed_whisper")
        self.assertEqual(choose_cleaned_preferred_method(0, 0), "separated_whisper")

    def test_build_synthetic_scope_rows_adds_split_breakdown(self) -> None:
        cases = [
            {"case_id": "dev_a", "split": "dev", "tier": "SyntheticNoOverlap", "overlap_level": 0, "duplicate_removed_count": 0},
            {"case_id": "test_b", "split": "test", "tier": "SyntheticHeavyOverlap", "overlap_level": 3, "duplicate_removed_count": 1},
        ]
        decisions = {
            "router_v2_synthetic_costed": {"dev_a": "mixed_whisper", "test_b": "separated_whisper_cleaned"},
        }
        cer_lookup = {
            ("dev_a", "mixed_whisper"): 0.2,
            ("dev_a", "separated_whisper"): 0.1,
            ("dev_a", "separated_whisper_cleaned"): 0.1,
            ("test_b", "mixed_whisper"): 0.6,
            ("test_b", "separated_whisper"): 0.3,
            ("test_b", "separated_whisper_cleaned"): 0.15,
        }
        runtime_lookup = {
            "dev_a": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.2},
            "test_b": {"mixed_runtime_sec": 1.5, "separated_runtime_sec": 3.0, "cleaned_runtime_sec": 3.2},
        }

        rows = build_synthetic_scope_rows(cases, decisions, cer_lookup, runtime_lookup)

        all_cleaned_preferred = next(
            row for row in rows if row["scope"] == "ALL" and row["strategy"] == "cleaned_preferred_cascade"
        )
        test_router = next(
            row for row in rows if row["scope"] == "TEST" and row["strategy"] == "router_v2_synthetic_costed"
        )

        self.assertEqual(all_cleaned_preferred["average_cer"], 0.125)
        self.assertEqual(all_cleaned_preferred["selected_method_mix"], "separated_whisper:1;separated_whisper_cleaned:1")
        self.assertEqual(test_router["sample_count"], 1)
        self.assertEqual(test_router["average_compute_cost"], 3.2)

    def test_summarize_runtime_sources_counts_proxy_fallbacks(self) -> None:
        cases = [
            {"case_id": "A", "overlap_level": 0, "risk_level": "low"},
            {"case_id": "B", "overlap_level": 3, "risk_level": "high"},
        ]
        runtime_lookup = {
            "A": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.1},
            "B": {"mixed_runtime_sec": 1.2, "separated_runtime_sec": 0.0, "cleaned_runtime_sec": 0.0},
        }
        decisions = {
            "router_v2_costed": {"A": "mixed_whisper", "B": "separated_whisper"},
            "risk_aware_costed": {"A": "mixed_whisper", "B": "manual_review"},
        }

        rows = summarize_runtime_sources(cases, ["router_v2_costed", "risk_aware_costed"], decisions, runtime_lookup)
        router_row = next(row for row in rows if row["strategy"] == "router_v2_costed")
        risk_row = next(row for row in rows if row["strategy"] == "risk_aware_costed")

        self.assertEqual(router_row["observed_runtime_count"], 1)
        self.assertEqual(router_row["proxy_runtime_count"], 1)
        self.assertEqual(router_row["manual_review_count"], 0)
        self.assertEqual(risk_row["manual_review_count"], 1)
        self.assertEqual(risk_row["proxy_runtime_count"], 1)

    def test_summarize_runtime_normalization_uses_selected_audio_duration(self) -> None:
        cases = [
            {"case_id": "A", "overlap_level": 0, "risk_level": "low"},
            {"case_id": "B", "overlap_level": 3, "risk_level": "high"},
        ]
        runtime_lookup = {
            "A": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.2},
            "B": {"mixed_runtime_sec": 1.5, "separated_runtime_sec": 3.0, "cleaned_runtime_sec": 3.2},
        }
        duration_lookup = {
            "A": {"mixed_duration_sec": 10.0, "separated_duration_sec": 20.0},
            "B": {"mixed_duration_sec": 5.0, "separated_duration_sec": 10.0},
        }
        decisions = {
            "router_v2_costed": {"A": "mixed_whisper", "B": "separated_whisper"},
        }

        rows = summarize_runtime_normalization(
            cases,
            ["fixed_mixed_whisper", "router_v2_costed"],
            decisions,
            runtime_lookup,
            duration_lookup,
            scope="ALL",
            dataset_label="gold",
        )
        fixed_row = next(row for row in rows if row["strategy"] == "fixed_mixed_whisper")
        router_row = next(row for row in rows if row["strategy"] == "router_v2_costed")

        self.assertEqual(fixed_row["average_rtf"], 0.2)
        self.assertEqual(router_row["average_rtf"], 0.2)
        self.assertEqual(router_row["duration_source"], "selected_audio")

    def test_classify_pareto_rows_marks_dominated_and_frontier(self) -> None:
        rows = [
            {"strategy": "cheap_bad", "average_cer": 0.4, "average_compute_cost": 1.0},
            {"strategy": "mid_good", "average_cer": 0.2, "average_compute_cost": 1.2},
            {"strategy": "expensive_same", "average_cer": 0.2, "average_compute_cost": 1.5},
            {"strategy": "cheap_best", "average_cer": 0.15, "average_compute_cost": 0.9},
        ]

        classified = classify_pareto_rows(rows)
        by_strategy = {row["strategy"]: row for row in classified}

        self.assertEqual(by_strategy["cheap_best"]["pareto_status"], "frontier")
        self.assertEqual(by_strategy["mid_good"]["pareto_status"], "dominated")
        self.assertEqual(by_strategy["mid_good"]["dominated_by"], "cheap_best")
        self.assertEqual(by_strategy["expensive_same"]["pareto_status"], "dominated")
        self.assertEqual(by_strategy["expensive_same"]["dominated_by"], "mid_good")

    def test_build_recommendation_rows_picks_profile_winners(self) -> None:
        pareto_rows = [
            {"dataset": "gold", "scope": "ALL", "strategy": "cheap", "average_cer": 0.35, "average_compute_cost": 0.6, "average_rtf": 0.16, "pareto_status": "frontier"},
            {"dataset": "gold", "scope": "ALL", "strategy": "accurate", "average_cer": 0.10, "average_compute_cost": 1.2, "average_rtf": 0.12, "pareto_status": "frontier"},
            {"dataset": "gold", "scope": "ALL", "strategy": "balanced", "average_cer": 0.18, "average_compute_cost": 0.8, "average_rtf": 0.13, "pareto_status": "frontier"},
            {"dataset": "gold", "scope": "ALL", "strategy": "dominated", "average_cer": 0.20, "average_compute_cost": 1.0, "average_rtf": 0.14, "pareto_status": "dominated"},
        ]

        rows = build_recommendation_rows(pareto_rows)
        by_profile = {row["profile"]: row for row in rows}

        self.assertEqual(by_profile["accuracy_first"]["recommended_strategy"], "accurate")
        self.assertEqual(by_profile["cost_first"]["recommended_strategy"], "cheap")
        self.assertEqual(by_profile["balanced"]["recommended_strategy"], "balanced")

    def test_build_recommendation_stability_rows_counts_scope_consensus(self) -> None:
        rows = [
            {"dataset": "gold", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router"},
            {"dataset": "synthetic_split", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router"},
            {"dataset": "synthetic_split", "scope": "DEV", "profile": "balanced", "recommended_strategy": "router"},
            {"dataset": "synthetic_split", "scope": "TEST", "profile": "balanced", "recommended_strategy": "mixed"},
            {"dataset": "gold", "scope": "ALL", "profile": "cost_first", "recommended_strategy": "mixed"},
            {"dataset": "synthetic_split", "scope": "ALL", "profile": "cost_first", "recommended_strategy": "mixed"},
        ]

        stability = build_recommendation_stability_rows(rows)
        balanced = next(row for row in stability if row["profile"] == "balanced")
        cost_first = next(row for row in stability if row["profile"] == "cost_first")

        self.assertEqual(balanced["distinct_strategy_count"], 2)
        self.assertEqual(balanced["most_common_strategy"], "router")
        self.assertEqual(balanced["consensus_ratio"], 0.75)
        self.assertEqual(cost_first["distinct_strategy_count"], 1)
        self.assertEqual(cost_first["consensus_ratio"], 1.0)

    def test_build_recommendation_family_stability_rows_merges_router_variants(self) -> None:
        rows = [
            {"dataset": "gold", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router_v2_costed"},
            {"dataset": "synthetic_split", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router_v2_synthetic_costed"},
            {"dataset": "synthetic_split", "scope": "DEV", "profile": "balanced", "recommended_strategy": "router_v2_synthetic_costed"},
            {"dataset": "synthetic_split", "scope": "TEST", "profile": "balanced", "recommended_strategy": "router_v2_synthetic_costed"},
        ]

        stability = build_recommendation_family_stability_rows(rows)
        balanced = next(row for row in stability if row["profile"] == "balanced")

        self.assertEqual(balanced["distinct_strategy_count"], 1)
        self.assertEqual(balanced["most_common_strategy"], "router_v2")
        self.assertEqual(balanced["consensus_ratio"], 1.0)

    def test_build_decision_matrix_rows_combines_recommendation_and_robustness(self) -> None:
        gold_recommendations = [
            {"dataset": "gold", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router_v2_costed"},
            {"dataset": "gold", "scope": "ALL", "profile": "cost_first", "recommended_strategy": "fixed_mixed_whisper"},
        ]
        synthetic_recommendations = [
            {"dataset": "synthetic_split", "scope": "ALL", "profile": "balanced", "recommended_strategy": "router_v2_synthetic_costed", "average_cer": 0.28, "average_compute_cost": 0.78, "average_rtf": 0.15},
            {"dataset": "synthetic_split", "scope": "ALL", "profile": "cost_first", "recommended_strategy": "fixed_mixed_whisper", "average_cer": 0.46, "average_compute_cost": 0.67, "average_rtf": 0.16},
        ]
        family_stability = [
            {"profile": "balanced", "most_common_strategy": "router_v2", "consensus_ratio": 1.0},
            {"profile": "cost_first", "most_common_strategy": "fixed_mixed_whisper", "consensus_ratio": 1.0},
        ]
        robustness = [
            {"strategy": "router_v2", "robustness_rank": 3, "cer_gap_vs_gold": 0.165145},
            {"strategy": "fixed_mixed_whisper", "robustness_rank": 2, "cer_gap_vs_gold": 0.163622},
        ]

        rows = build_decision_matrix_rows(gold_recommendations, synthetic_recommendations, family_stability, robustness)
        balanced = next(row for row in rows if row["profile"] == "balanced")

        self.assertEqual(balanced["gold_recommended_strategy"], "router_v2_costed")
        self.assertEqual(balanced["synthetic_all_recommended_strategy"], "router_v2_synthetic_costed")
        self.assertEqual(balanced["family_consensus_ratio"], 1.0)
        self.assertEqual(balanced["robustness_rank"], 3)

    def test_build_frontier_report_lines_mentions_key_sections(self) -> None:
        decision_matrix_rows = [
            {
                "profile": "balanced",
                "gold_recommended_strategy": "router_v2_costed",
                "synthetic_all_recommended_strategy": "router_v2_synthetic_costed",
                "family_most_common_strategy": "router_v2",
                "family_consensus_ratio": 1.0,
                "synthetic_all_average_cer": 0.285187,
                "synthetic_all_average_compute_cost": 0.78127,
                "synthetic_all_average_rtf": 0.148342,
                "robustness_rank": 3,
                "shared_cer_gap_vs_gold": 0.165145,
            }
        ]
        family_stability_rows = [
            {"profile": "balanced", "most_common_strategy": "router_v2", "consensus_ratio": 1.0}
        ]
        robustness_rows = [
            {"strategy": "router_v2", "robustness_rank": 3, "cer_gap_vs_gold": 0.165145}
        ]

        lines = build_frontier_report_lines(decision_matrix_rows, family_stability_rows, robustness_rows)
        text = "\n".join(lines)

        self.assertIn("# Compute-aware Cascade Frontier Report", text)
        self.assertIn("## Decision Matrix", text)
        self.assertIn("router_v2_costed", text)
        self.assertIn("## Stability Highlights", text)
        self.assertIn("## Robustness Highlights", text)

    def test_build_robustness_gap_rows_compares_gold_to_synthetic_all(self) -> None:
        gold_rows = [
            {"dataset": "gold", "scope": "ALL", "strategy": "router", "average_cer": 0.12, "average_compute_cost": 5.5, "average_rtf": 0.08},
            {"dataset": "gold", "scope": "ALL", "strategy": "mixed", "average_cer": 0.30, "average_compute_cost": 5.2, "average_rtf": 0.11},
        ]
        synthetic_rows = [
            {"dataset": "synthetic_split", "scope": "ALL", "strategy": "router", "average_cer": 0.28, "average_compute_cost": 0.78, "average_rtf": 0.15},
            {"dataset": "synthetic_split", "scope": "ALL", "strategy": "mixed", "average_cer": 0.46, "average_compute_cost": 0.67, "average_rtf": 0.16},
        ]

        rows = build_robustness_gap_rows(gold_rows, synthetic_rows)
        router = next(row for row in rows if row["strategy"] == "router")
        mixed = next(row for row in rows if row["strategy"] == "mixed")

        self.assertEqual(router["cer_gap_vs_gold"], 0.16)
        self.assertEqual(router["cost_gap_vs_gold"], -4.72)
        self.assertEqual(mixed["robustness_rank"], 1)
        self.assertEqual(router["robustness_rank"], 2)

    def test_build_robustness_gap_rows_aligns_router_v2_strategy_names(self) -> None:
        gold_rows = [
            {"dataset": "gold", "scope": "ALL", "strategy": "router_v2_costed", "average_cer": 0.12, "average_compute_cost": 5.5, "average_rtf": 0.08},
        ]
        synthetic_rows = [
            {"dataset": "synthetic_split", "scope": "ALL", "strategy": "router_v2_synthetic_costed", "average_cer": 0.28, "average_compute_cost": 0.78, "average_rtf": 0.15},
        ]

        rows = build_robustness_gap_rows(gold_rows, synthetic_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strategy"], "router_v2")
        self.assertEqual(rows[0]["cer_gap_vs_gold"], 0.16)

    def test_build_artifact_index_rows_covers_gold_and_synthetic_frontier_outputs(self) -> None:
        rows = build_artifact_index_rows()

        gold_frontier = next(row for row in rows if row["artifact_id"] == "gold_frontier_report")
        synthetic_recommendations = next(
            row for row in rows if row["artifact_id"] == "synthetic_split_recommendations"
        )
        gold_performance = next(row for row in rows if row["artifact_id"] == "gold_cascade_performance")

        self.assertEqual(gold_frontier["label"], "experimental/frontier")
        self.assertEqual(gold_frontier["dataset"], "gold")
        self.assertEqual(gold_frontier["artifact_path"], "results/figures/cascade_frontier_report.md")
        self.assertEqual(synthetic_recommendations["label"], "synthetic/silver")
        self.assertEqual(synthetic_recommendations["dataset"], "synthetic_split")
        self.assertEqual(gold_performance["label"], "experimental/frontier")
        self.assertTrue(rows == sorted(rows, key=lambda row: (row["dataset"], row["artifact_group"], row["artifact_id"])))

    def test_build_artifact_index_lines_summarizes_registry_as_markdown(self) -> None:
        rows = [
            {
                "artifact_id": "gold_cascade_performance",
                "dataset": "gold",
                "label": "experimental/frontier",
                "artifact_group": "performance",
                "artifact_path": "results/tables/cascade_performance.csv",
                "generator_command": "python -m src.compute_aware_cascade",
                "intended_use": "Primary gold compute-aware performance table.",
            },
            {
                "artifact_id": "synthetic_split_recommendations",
                "dataset": "synthetic_split",
                "label": "synthetic/silver",
                "artifact_group": "recommendation",
                "artifact_path": "results/tables/synthetic_split_cascade_recommendations.csv",
                "generator_command": "python -m src.compute_aware_cascade --dataset synthetic_split",
                "intended_use": "Synthetic split deployment-profile recommendation card.",
            },
        ]

        lines = build_artifact_index_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Artifact Index", rendered)
        self.assertIn("## gold", rendered)
        self.assertIn("## synthetic_split", rendered)
        self.assertIn("gold_cascade_performance", rendered)
        self.assertIn("synthetic/silver", rendered)
        self.assertIn("python -m src.compute_aware_cascade --dataset synthetic_split", rendered)

    def test_build_benchmark_readiness_rows_prioritizes_runtime_facing_artifacts(self) -> None:
        artifact_rows = build_artifact_index_rows()

        rows = build_benchmark_readiness_rows(artifact_rows)
        gold_runtime = next(row for row in rows if row["artifact_id"] == "gold_runtime_normalization")
        gold_frontier = next(row for row in rows if row["artifact_id"] == "gold_frontier_report")
        cross_dataset = next(row for row in rows if row["artifact_id"] == "cross_dataset_decision_matrix")

        self.assertEqual(gold_runtime["benchmark_priority"], "high")
        self.assertEqual(gold_runtime["benchmark_status"], "repo_local_runtime_only")
        self.assertEqual(gold_runtime["readiness_tier"], "benchmark_foundation")
        self.assertEqual(gold_frontier["benchmark_priority"], "medium")
        self.assertEqual(gold_frontier["benchmark_status"], "inherits_repo_local_runtime")
        self.assertEqual(cross_dataset["benchmark_priority"], "medium")
        self.assertEqual(cross_dataset["dataset"], "cross_dataset")
        self.assertTrue(rows == sorted(rows, key=lambda row: (row["benchmark_priority_rank"], row["dataset"], row["artifact_id"])))

    def test_build_benchmark_readiness_lines_render_priority_sections(self) -> None:
        rows = [
            {
                "artifact_id": "gold_runtime_normalization",
                "dataset": "gold",
                "label": "experimental/frontier",
                "artifact_group": "audit",
                "artifact_path": "results/tables/cascade_runtime_normalization.csv",
                "benchmark_priority": "high",
                "benchmark_priority_rank": 0,
                "benchmark_status": "repo_local_runtime_only",
                "readiness_tier": "benchmark_foundation",
                "next_evidence_step": "Run a controlled same-hardware timing sweep for the selected routes.",
            },
            {
                "artifact_id": "cross_dataset_decision_matrix",
                "dataset": "cross_dataset",
                "label": "experimental/frontier",
                "artifact_group": "report",
                "artifact_path": "results/tables/cascade_decision_matrix.csv",
                "benchmark_priority": "medium",
                "benchmark_priority_rank": 1,
                "benchmark_status": "inherits_repo_local_runtime",
                "readiness_tier": "downstream_summary",
                "next_evidence_step": "Refresh after gold and synthetic controlled benchmark evidence lands.",
            },
        ]

        lines = build_benchmark_readiness_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Readiness", rendered)
        self.assertIn("## high priority", rendered)
        self.assertIn("## medium priority", rendered)
        self.assertIn("gold_runtime_normalization", rendered)
        self.assertIn("repo_local_runtime_only", rendered)
        self.assertIn("Refresh after gold and synthetic controlled benchmark evidence lands.", rendered)

    def test_build_benchmark_plan_rows_stages_foundation_surface_and_cross_dataset_refresh(self) -> None:
        readiness_rows = build_benchmark_readiness_rows(build_artifact_index_rows())

        rows = build_benchmark_plan_rows(readiness_rows)
        gold_foundation = next(row for row in rows if row["plan_step_id"] == "phase1_gold_runtime_foundation")
        synthetic_surface = next(row for row in rows if row["plan_step_id"] == "phase4_synthetic_surface_refresh")
        cross_dataset = next(row for row in rows if row["plan_step_id"] == "phase5_cross_dataset_refresh")

        self.assertEqual(gold_foundation["phase"], "foundation")
        self.assertEqual(gold_foundation["command"], "python -m src.compute_aware_cascade")
        self.assertIn("gold_runtime_audit", gold_foundation["refreshed_artifacts"])
        self.assertEqual(synthetic_surface["phase"], "surface")
        self.assertEqual(synthetic_surface["command"], "python -m src.compute_aware_cascade --dataset synthetic_split")
        self.assertIn("synthetic_split_cascade_performance", synthetic_surface["refreshed_artifacts"])
        self.assertEqual(cross_dataset["phase"], "cross_dataset")
        self.assertEqual(cross_dataset["success_signal"], "Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.")
        self.assertTrue(rows == sorted(rows, key=lambda row: row["step_order"]))

    def test_build_benchmark_plan_lines_render_sequenced_handoff(self) -> None:
        rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "command": "python -m src.compute_aware_cascade",
                "prerequisite_artifacts": "gold_runtime_audit;gold_runtime_normalization",
                "refreshed_artifacts": "gold_runtime_audit;gold_runtime_normalization",
                "success_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            },
            {
                "plan_step_id": "phase5_cross_dataset_refresh",
                "step_order": 5,
                "phase": "cross_dataset",
                "dataset_scope": "cross_dataset",
                "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
                "prerequisite_artifacts": "cross_dataset_robustness_gap;cross_dataset_decision_matrix",
                "refreshed_artifacts": "cross_dataset_robustness_gap;cross_dataset_decision_matrix",
                "success_signal": "Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.",
            },
        ]

        lines = build_benchmark_plan_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Plan", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("phase5_cross_dataset_refresh", rendered)
        self.assertIn("python -m src.compute_aware_cascade --dataset synthetic_split", rendered)
        self.assertIn("Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.", rendered)

    def test_build_profile_playbook_rows_turns_decision_matrix_into_deployment_guidance(self) -> None:
        decision_matrix_rows = [
            {
                "profile": "accuracy_first",
                "gold_recommended_strategy": "router_v2_costed",
                "synthetic_all_recommended_strategy": "fixed_separated_whisper_cleaned",
                "family_most_common_strategy": "fixed_separated_whisper_cleaned",
                "family_consensus_ratio": 0.75,
                "synthetic_all_average_cer": 0.179021,
                "synthetic_all_average_compute_cost": 1.10836,
                "synthetic_all_average_rtf": 0.133284,
                "robustness_rank": 1,
                "shared_cer_gap_vs_gold": -0.00266,
            },
            {
                "profile": "balanced",
                "gold_recommended_strategy": "router_v2_costed",
                "synthetic_all_recommended_strategy": "router_v2_synthetic_costed",
                "family_most_common_strategy": "router_v2",
                "family_consensus_ratio": 1.0,
                "synthetic_all_average_cer": 0.285187,
                "synthetic_all_average_compute_cost": 0.78127,
                "synthetic_all_average_rtf": 0.148342,
                "robustness_rank": 3,
                "shared_cer_gap_vs_gold": 0.165145,
            },
            {
                "profile": "cost_first",
                "gold_recommended_strategy": "fixed_mixed_whisper",
                "synthetic_all_recommended_strategy": "fixed_mixed_whisper",
                "family_most_common_strategy": "fixed_mixed_whisper",
                "family_consensus_ratio": 1.0,
                "synthetic_all_average_cer": 0.465715,
                "synthetic_all_average_compute_cost": 0.674,
                "synthetic_all_average_rtf": 0.163361,
                "robustness_rank": 2,
                "shared_cer_gap_vs_gold": 0.163622,
            },
        ]

        rows = build_profile_playbook_rows(decision_matrix_rows)
        balanced = next(row for row in rows if row["profile"] == "balanced")
        accuracy = next(row for row in rows if row["profile"] == "accuracy_first")
        cost = next(row for row in rows if row["profile"] == "cost_first")

        self.assertEqual(balanced["default_role"], "default")
        self.assertIn("router_v2", balanced["when_to_use"])
        self.assertEqual(accuracy["default_role"], "robust_accuracy")
        self.assertIn("lowest shared robustness rank", accuracy["tradeoff_summary"])
        self.assertEqual(cost["default_role"], "budget_floor")
        self.assertTrue(rows == sorted(rows, key=lambda row: row["profile"]))

    def test_build_profile_playbook_lines_render_profile_sections(self) -> None:
        rows = [
            {
                "profile": "balanced",
                "default_role": "default",
                "family_strategy": "router_v2",
                "gold_strategy": "router_v2_costed",
                "synthetic_strategy": "router_v2_synthetic_costed",
                "when_to_use": "Use when you want the cleanest default operating point across scopes.",
                "avoid_when": "Avoid when the absolute best held-out accuracy matters more than consistency.",
                "tradeoff_summary": "Stable family-level default with moderate robustness and lower synthetic cost than accuracy_first.",
            },
        ]

        lines = build_profile_playbook_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Profile Playbook", rendered)
        self.assertIn("## balanced", rendered)
        self.assertIn("router_v2", rendered)
        self.assertIn("Use when you want the cleanest default operating point across scopes.", rendered)


if __name__ == "__main__":
    unittest.main()
