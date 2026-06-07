from __future__ import annotations

import unittest

from src.compute_aware_cascade import (
    build_decision_matrix_rows,
    build_artifact_index_lines,
    build_artifact_index_rows,
    build_benchmark_checklist_lines,
    build_benchmark_checklist_rows,
    build_benchmark_manifest_template_rows,
    build_benchmark_packet_lines,
    build_benchmark_execution_summary_lines,
    build_benchmark_execution_summary_rows,
    build_benchmark_execution_queue_lines,
    build_benchmark_execution_queue_rows,
    build_benchmark_dependency_graph_lines,
    build_benchmark_dependency_graph_rows,
    build_benchmark_blocker_matrix_lines,
    build_benchmark_blocker_matrix_rows,
    build_benchmark_runbook_card_lines,
    build_benchmark_runbook_card_rows,
    build_benchmark_milestone_card_lines,
    build_benchmark_milestone_card_rows,
    build_benchmark_phase_checkpoint_card_lines,
    build_benchmark_phase_checkpoint_card_rows,
    build_benchmark_completion_dashboard_lines,
    build_benchmark_completion_dashboard_rows,
    build_benchmark_evidence_receipt_lines,
    build_benchmark_evidence_receipt_rows,
    build_benchmark_evidence_checklist_lines,
    build_benchmark_evidence_checklist_rows,
    build_benchmark_receipt_bridge_lines,
    build_benchmark_receipt_bridge_rows,
    build_benchmark_frontier_bridge_lines,
    build_benchmark_frontier_bridge_checklist_lines,
    build_benchmark_frontier_bridge_checklist_rows,
    build_benchmark_frontier_bridge_rows,
    build_benchmark_operator_brief_lines,
    build_benchmark_operator_brief_rows,
    build_benchmark_session_ledger_lines,
    build_benchmark_session_ledger_rows,
    build_benchmark_status_lines,
    build_benchmark_status_rows,
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

    def test_build_benchmark_checklist_rows_turns_plan_steps_into_session_requirements(self) -> None:
        plan_rows = [
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

        rows = build_benchmark_checklist_rows(plan_rows)
        foundation = next(row for row in rows if row["plan_step_id"] == "phase1_gold_runtime_foundation")
        cross_dataset = next(row for row in rows if row["plan_step_id"] == "phase5_cross_dataset_refresh")

        self.assertEqual(foundation["session_type"], "timing_capture")
        self.assertIn("hardware_label", foundation["required_metadata"])
        self.assertIn("repeat_count", foundation["required_metadata"])
        self.assertEqual(cross_dataset["session_type"], "derived_refresh")
        self.assertIn("source_timing_manifest", cross_dataset["required_metadata"])
        self.assertIn("Cross-dataset decision-support artifacts", cross_dataset["acceptance_check"])
        self.assertTrue(rows == sorted(rows, key=lambda row: row["step_order"]))

    def test_build_benchmark_checklist_lines_render_run_metadata_requirements(self) -> None:
        rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "command": "python -m src.compute_aware_cascade",
                "session_type": "timing_capture",
                "required_metadata": "hardware_label;device;repeat_count;warmup_count",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            },
        ]

        lines = build_benchmark_checklist_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Checklist", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("hardware_label;device;repeat_count;warmup_count", rendered)
        self.assertIn("Gold runtime foundation artifacts are rebuilt from controlled timing.", rendered)

    def test_build_benchmark_manifest_template_rows_expand_checklist_metadata_placeholders(self) -> None:
        checklist_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "command": "python -m src.compute_aware_cascade",
                "session_type": "timing_capture",
                "required_metadata": "hardware_label;device;repeat_count;warmup_count",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            },
            {
                "plan_step_id": "phase5_cross_dataset_refresh",
                "step_order": 5,
                "phase": "cross_dataset",
                "dataset_scope": "cross_dataset",
                "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
                "session_type": "derived_refresh",
                "required_metadata": "source_timing_manifest;cross_dataset_scope;refresh_command;consistency_notes",
                "acceptance_check": "Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.",
            },
        ]

        rows = build_benchmark_manifest_template_rows(checklist_rows)
        foundation = next(row for row in rows if row["plan_step_id"] == "phase1_gold_runtime_foundation")
        cross_dataset = next(row for row in rows if row["plan_step_id"] == "phase5_cross_dataset_refresh")

        self.assertEqual(foundation["hardware_label"], "TODO")
        self.assertEqual(foundation["device"], "TODO")
        self.assertEqual(foundation["acceptance_check"], "Gold runtime foundation artifacts are rebuilt from controlled timing.")
        self.assertEqual(cross_dataset["source_timing_manifest"], "TODO")
        self.assertEqual(cross_dataset["cross_dataset_scope"], "TODO")
        self.assertTrue(rows == sorted(rows, key=lambda row: row["step_order"]))

    def test_build_benchmark_status_rows_marks_template_only_steps_as_pending(self) -> None:
        manifest_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "session_type": "timing_capture",
                "command": "python -m src.compute_aware_cascade",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "hardware_label": "TODO",
                "device": "TODO",
                "repeat_count": "TODO",
                "warmup_count": "TODO",
                "batch_shape": "TODO",
                "timing_notes": "TODO",
                "source_timing_manifest": "",
                "refresh_command": "",
                "diff_review_notes": "",
                "cross_dataset_scope": "",
                "consistency_notes": "",
            },
            {
                "plan_step_id": "phase5_cross_dataset_refresh",
                "step_order": 5,
                "phase": "cross_dataset",
                "dataset_scope": "cross_dataset",
                "session_type": "derived_refresh",
                "command": "python -m src.compute_aware_cascade --dataset synthetic_split",
                "acceptance_check": "Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.",
                "hardware_label": "",
                "device": "",
                "repeat_count": "",
                "warmup_count": "",
                "batch_shape": "",
                "timing_notes": "",
                "source_timing_manifest": "TODO",
                "refresh_command": "TODO",
                "diff_review_notes": "",
                "cross_dataset_scope": "TODO",
                "consistency_notes": "TODO",
            },
        ]

        rows = build_benchmark_status_rows(manifest_rows)
        foundation = next(row for row in rows if row["plan_step_id"] == "phase1_gold_runtime_foundation")
        cross_dataset = next(row for row in rows if row["plan_step_id"] == "phase5_cross_dataset_refresh")

        self.assertEqual(foundation["execution_status"], "template_only")
        self.assertEqual(foundation["readiness_signal"], "pending_execution")
        self.assertEqual(foundation["pending_field_count"], 6)
        self.assertEqual(foundation["blocking_category"], "runtime_capture_missing")
        self.assertEqual(foundation["next_action"], "collect_controlled_runtime")
        self.assertEqual(cross_dataset["execution_status"], "template_only")
        self.assertEqual(cross_dataset["pending_field_count"], 4)
        self.assertEqual(cross_dataset["blocking_category"], "derived_refresh_missing")
        self.assertIn("source_timing_manifest", cross_dataset["missing_fields"])
        self.assertEqual(cross_dataset["next_action"], "refresh_cross_dataset_stack")
        self.assertTrue(rows == sorted(rows, key=lambda row: row["step_order"]))

    def test_build_benchmark_status_lines_render_phase_board(self) -> None:
        rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 3,
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
                "missing_fields": "hardware_label;device;repeat_count",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        lines = build_benchmark_status_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Status Board", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("pending_execution", rendered)
        self.assertIn("runtime_capture_missing", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("hardware_label;device;repeat_count", rendered)

    def test_build_benchmark_execution_summary_rows_aggregate_phase_totals(self) -> None:
        status_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 6,
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
            },
            {
                "plan_step_id": "phase2_synthetic_runtime_foundation",
                "step_order": 2,
                "phase": "foundation",
                "dataset_scope": "synthetic_split",
                "execution_status": "filled",
                "readiness_signal": "ready_for_review",
                "pending_field_count": 0,
                "blocking_category": "ready_for_review",
                "next_action": "review_completed_manifest",
            },
            {
                "plan_step_id": "phase5_cross_dataset_refresh",
                "step_order": 5,
                "phase": "cross_dataset",
                "dataset_scope": "cross_dataset",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 4,
                "blocking_category": "derived_refresh_missing",
                "next_action": "refresh_cross_dataset_stack",
            },
        ]

        rows = build_benchmark_execution_summary_rows(status_rows)
        foundation = next(row for row in rows if row["phase"] == "foundation")
        cross_dataset = next(row for row in rows if row["phase"] == "cross_dataset")

        self.assertEqual(foundation["step_count"], 2)
        self.assertEqual(foundation["filled_step_count"], 1)
        self.assertEqual(foundation["template_only_step_count"], 1)
        self.assertEqual(foundation["total_pending_field_count"], 6)
        self.assertEqual(foundation["primary_blocking_category"], "runtime_capture_missing")
        self.assertEqual(foundation["recommended_next_action"], "collect_controlled_runtime")
        self.assertEqual(cross_dataset["total_pending_field_count"], 4)
        self.assertEqual(cross_dataset["readiness_label"], "pending_execution")

    def test_build_benchmark_execution_summary_lines_render_phase_rollup(self) -> None:
        rows = [
            {
                "phase": "foundation",
                "step_count": 2,
                "filled_step_count": 1,
                "template_only_step_count": 1,
                "total_pending_field_count": 6,
                "readiness_label": "pending_execution",
                "primary_blocking_category": "runtime_capture_missing",
                "recommended_next_action": "collect_controlled_runtime",
                "covered_datasets": "gold;synthetic_split",
            }
        ]

        lines = build_benchmark_execution_summary_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Execution Summary", rendered)
        self.assertIn("foundation", rendered)
        self.assertIn("runtime_capture_missing", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("gold;synthetic_split", rendered)

    def test_build_benchmark_execution_queue_rows_prioritize_pending_steps(self) -> None:
        status_rows = [
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "step_order": 3,
                "phase": "surface",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 3,
                "blocking_category": "artifact_refresh_missing",
                "next_action": "refresh_timing_backed_artifacts",
                "missing_fields": "source_timing_manifest;refresh_command;diff_review_notes",
            },
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 6,
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
                "missing_fields": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
            },
            {
                "plan_step_id": "phase2_synthetic_runtime_foundation",
                "step_order": 2,
                "phase": "foundation",
                "dataset_scope": "synthetic_split",
                "execution_status": "filled",
                "readiness_signal": "ready_for_review",
                "pending_field_count": 0,
                "blocking_category": "ready_for_review",
                "next_action": "review_completed_manifest",
                "missing_fields": "",
            },
        ]

        rows = build_benchmark_execution_queue_rows(status_rows)

        self.assertEqual(rows[0]["queue_rank"], 1)
        self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["priority_bucket"], "do_now")
        self.assertEqual(rows[0]["queue_reason"], "runtime_capture_missing with 6 pending fields")
        self.assertEqual(rows[1]["plan_step_id"], "phase3_gold_surface_refresh")
        self.assertEqual(rows[2]["plan_step_id"], "phase2_synthetic_runtime_foundation")
        self.assertEqual(rows[2]["priority_bucket"], "ready_for_review")

    def test_build_benchmark_execution_queue_lines_render_ordered_queue(self) -> None:
        rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "priority_bucket": "do_now",
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
                "pending_field_count": 6,
                "queue_reason": "runtime_capture_missing with 6 pending fields",
            }
        ]

        lines = build_benchmark_execution_queue_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Execution Queue", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("do_now", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("runtime_capture_missing with 6 pending fields", rendered)

    def test_build_benchmark_session_ledger_rows_join_queue_and_manifest(self) -> None:
        queue_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "priority_bucket": "do_now",
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
                "pending_field_count": 6,
                "queue_reason": "runtime_capture_missing with 6 pending fields",
            }
        ]
        manifest_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "session_type": "timing_capture",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "hardware_label": "TODO",
                "device": "TODO",
                "repeat_count": "TODO",
                "warmup_count": "TODO",
                "batch_shape": "TODO",
                "timing_notes": "TODO",
                "source_timing_manifest": "",
                "refresh_command": "",
                "diff_review_notes": "",
                "cross_dataset_scope": "",
                "consistency_notes": "",
            }
        ]

        rows = build_benchmark_session_ledger_rows(queue_rows, manifest_rows)

        self.assertEqual(rows[0]["queue_rank"], 1)
        self.assertEqual(rows[0]["plan_step_id"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["session_type"], "timing_capture")
        self.assertEqual(rows[0]["evidence_anchor"], "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes")
        self.assertEqual(rows[0]["todo_field_count"], 6)
        self.assertEqual(rows[0]["completion_note"], "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.")

    def test_build_benchmark_session_ledger_lines_render_evidence_bridge(self) -> None:
        rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "session_type": "timing_capture",
                "priority_bucket": "do_now",
                "evidence_anchor": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "todo_field_count": 6,
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        lines = build_benchmark_session_ledger_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Session Ledger", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("timing_capture", rendered)
        self.assertIn("hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes", rendered)
        self.assertIn("collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.", rendered)

    def test_build_benchmark_dependency_graph_rows_connect_predecessors(self) -> None:
        plan_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "success_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            },
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "step_order": 3,
                "phase": "surface",
                "dataset_scope": "gold",
                "success_signal": "Gold surface artifacts are rebuilt from controlled timing-backed inputs.",
            },
        ]
        queue_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "priority_bucket": "do_now",
            },
            {
                "queue_rank": 3,
                "plan_step_id": "phase3_gold_surface_refresh",
                "priority_bucket": "next_after_runtime",
            },
        ]

        rows = build_benchmark_dependency_graph_rows(plan_rows, queue_rows)
        foundation = next(row for row in rows if row["plan_step_id"] == "phase1_gold_runtime_foundation")
        surface = next(row for row in rows if row["plan_step_id"] == "phase3_gold_surface_refresh")

        self.assertEqual(foundation["depends_on_step"], "")
        self.assertEqual(foundation["dependency_status"], "root")
        self.assertEqual(surface["depends_on_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(surface["dependency_status"], "blocked_by_predecessor")
        self.assertEqual(surface["unlocks_step"], "")
        self.assertEqual(surface["dependency_note"], "Wait for phase1_gold_runtime_foundation before phase3_gold_surface_refresh can produce timing-backed surface outputs.")

    def test_build_benchmark_dependency_graph_lines_render_unlock_chain(self) -> None:
        rows = [
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "step_order": 3,
                "phase": "surface",
                "dataset_scope": "gold",
                "queue_rank": 3,
                "priority_bucket": "next_after_runtime",
                "depends_on_step": "phase1_gold_runtime_foundation",
                "dependency_status": "blocked_by_predecessor",
                "unlocks_step": "",
                "dependency_note": "Wait for phase1_gold_runtime_foundation before phase3_gold_surface_refresh can produce timing-backed surface outputs.",
            }
        ]

        lines = build_benchmark_dependency_graph_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Dependency Graph", rendered)
        self.assertIn("phase3_gold_surface_refresh", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("blocked_by_predecessor", rendered)
        self.assertIn("timing-backed surface outputs", rendered)

    def test_build_benchmark_blocker_matrix_rows_join_status_queue_and_dependency(self) -> None:
        status_rows = [
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "phase": "surface",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "pending_field_count": 3,
                "blocking_category": "artifact_refresh_missing",
                "next_action": "refresh_timing_backed_artifacts",
            }
        ]
        queue_rows = [
            {
                "queue_rank": 3,
                "plan_step_id": "phase3_gold_surface_refresh",
                "priority_bucket": "next_after_runtime",
                "queue_reason": "artifact_refresh_missing with 3 pending fields",
            }
        ]
        dependency_rows = [
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "depends_on_step": "phase2_synthetic_runtime_foundation",
                "dependency_status": "blocked_by_predecessor",
                "unlocks_step": "phase4_synthetic_surface_refresh",
            }
        ]

        rows = build_benchmark_blocker_matrix_rows(status_rows, queue_rows, dependency_rows)

        self.assertEqual(rows[0]["plan_step_id"], "phase3_gold_surface_refresh")
        self.assertEqual(rows[0]["queue_rank"], 3)
        self.assertEqual(rows[0]["priority_bucket"], "next_after_runtime")
        self.assertEqual(rows[0]["blocking_category"], "artifact_refresh_missing")
        self.assertEqual(rows[0]["dependency_status"], "blocked_by_predecessor")
        self.assertEqual(rows[0]["severity_band"], "medium")
        self.assertEqual(rows[0]["matrix_note"], "next_after_runtime / blocked_by_predecessor / 3 pending fields")

    def test_build_benchmark_blocker_matrix_lines_render_joined_triage_view(self) -> None:
        rows = [
            {
                "plan_step_id": "phase3_gold_surface_refresh",
                "phase": "surface",
                "dataset_scope": "gold",
                "queue_rank": 3,
                "priority_bucket": "next_after_runtime",
                "blocking_category": "artifact_refresh_missing",
                "dependency_status": "blocked_by_predecessor",
                "pending_field_count": 3,
                "severity_band": "medium",
                "matrix_note": "next_after_runtime / blocked_by_predecessor / 3 pending fields",
            }
        ]

        lines = build_benchmark_blocker_matrix_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Blocker Matrix", rendered)
        self.assertIn("phase3_gold_surface_refresh", rendered)
        self.assertIn("artifact_refresh_missing", rendered)
        self.assertIn("blocked_by_predecessor", rendered)
        self.assertIn("next_after_runtime / blocked_by_predecessor / 3 pending fields", rendered)

    def test_build_benchmark_runbook_card_rows_summarize_first_action(self) -> None:
        blocker_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "queue_rank": 1,
                "priority_bucket": "do_now",
                "blocking_category": "runtime_capture_missing",
                "dependency_status": "root",
                "pending_field_count": 6,
                "severity_band": "high",
                "matrix_note": "do_now / root / 6 pending fields",
            }
        ]
        queue_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "next_action": "collect_controlled_runtime",
                "queue_reason": "runtime_capture_missing with 6 pending fields",
            }
        ]
        ledger_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "session_type": "timing_capture",
                "evidence_anchor": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        rows = build_benchmark_runbook_card_rows(blocker_rows, queue_rows, ledger_rows)

        self.assertEqual(rows[0]["recommended_start_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["recommended_action"], "collect_controlled_runtime")
        self.assertEqual(rows[0]["required_evidence"], "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes")
        self.assertEqual(rows[0]["session_type"], "timing_capture")
        self.assertEqual(rows[0]["urgency"], "high")
        self.assertEqual(rows[0]["runbook_note"], "Start with phase1_gold_runtime_foundation because it is do_now and root.")

    def test_build_benchmark_runbook_card_lines_render_one_page_card(self) -> None:
        rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "recommended_action": "collect_controlled_runtime",
                "session_type": "timing_capture",
                "required_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "urgency": "high",
                "runbook_note": "Start with phase1_gold_runtime_foundation because it is do_now and root.",
            }
        ]

        lines = build_benchmark_runbook_card_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Runbook Card", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("timing_capture", rendered)
        self.assertIn("Start with phase1_gold_runtime_foundation because it is do_now and root.", rendered)

    def test_build_benchmark_milestone_card_rows_summarize_next_milestone(self) -> None:
        runbook_rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "recommended_action": "collect_controlled_runtime",
                "session_type": "timing_capture",
                "required_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "urgency": "high",
                "runbook_note": "Start with phase1_gold_runtime_foundation because it is do_now and root.",
            }
        ]
        dependency_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "unlocks_step": "phase2_synthetic_runtime_foundation",
            }
        ]
        summary_rows = [
            {"phase": "foundation", "readiness_label": "pending_execution"},
            {"phase": "surface", "readiness_label": "pending_execution"},
            {"phase": "cross_dataset", "readiness_label": "pending_execution"},
        ]

        rows = build_benchmark_milestone_card_rows(runbook_rows, dependency_rows, summary_rows)

        self.assertEqual(rows[0]["current_start_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["next_milestone_step"], "phase2_synthetic_runtime_foundation")
        self.assertEqual(rows[0]["remaining_phase_count"], 3)
        self.assertEqual(rows[0]["current_urgency"], "high")
        self.assertEqual(rows[0]["milestone_note"], "phase1_gold_runtime_foundation unlocks phase2_synthetic_runtime_foundation and leaves 3 pending phases.")

    def test_build_benchmark_milestone_card_lines_render_progress_snapshot(self) -> None:
        rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "next_milestone_step": "phase2_synthetic_runtime_foundation",
                "remaining_phase_count": 3,
                "current_urgency": "high",
                "milestone_note": "phase1_gold_runtime_foundation unlocks phase2_synthetic_runtime_foundation and leaves 3 pending phases.",
            }
        ]

        lines = build_benchmark_milestone_card_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Milestone Card", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("phase2_synthetic_runtime_foundation", rendered)
        self.assertIn("3", rendered)
        self.assertIn("unlocks phase2_synthetic_runtime_foundation", rendered)

    def test_build_benchmark_phase_checkpoint_card_rows_pair_summary_with_plan(self) -> None:
        summary_rows = [
            {
                "phase": "foundation",
                "readiness_label": "pending_execution",
                "primary_blocking_category": "runtime_capture_missing",
                "recommended_next_action": "collect_controlled_runtime",
            }
        ]
        plan_rows = [
            {
                "phase": "foundation",
                "success_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        rows = build_benchmark_phase_checkpoint_card_rows(summary_rows, plan_rows)

        self.assertEqual(rows[0]["phase"], "foundation")
        self.assertEqual(rows[0]["readiness_label"], "pending_execution")
        self.assertEqual(rows[0]["primary_blocking_category"], "runtime_capture_missing")
        self.assertEqual(rows[0]["checkpoint_action"], "collect_controlled_runtime")
        self.assertEqual(rows[0]["completion_signal"], "Gold runtime foundation artifacts are rebuilt from controlled timing.")

    def test_build_benchmark_phase_checkpoint_card_lines_render_phase_gate(self) -> None:
        rows = [
            {
                "phase": "foundation",
                "readiness_label": "pending_execution",
                "primary_blocking_category": "runtime_capture_missing",
                "checkpoint_action": "collect_controlled_runtime",
                "completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        lines = build_benchmark_phase_checkpoint_card_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Phase Checkpoint Card", rendered)
        self.assertIn("foundation", rendered)
        self.assertIn("runtime_capture_missing", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("Gold runtime foundation artifacts are rebuilt from controlled timing.", rendered)

    def test_build_benchmark_completion_dashboard_rows_summarize_overall_progress(self) -> None:
        summary_rows = [
            {
                "phase": "foundation",
                "primary_blocking_category": "runtime_capture_missing",
                "readiness_label": "pending_execution",
            },
            {
                "phase": "surface",
                "primary_blocking_category": "artifact_refresh_missing",
                "readiness_label": "pending_execution",
            },
        ]
        runbook_rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "urgency": "high",
            }
        ]
        milestone_rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "remaining_phase_count": 2,
            }
        ]

        rows = build_benchmark_completion_dashboard_rows(summary_rows, runbook_rows, milestone_rows)

        self.assertEqual(rows[0]["current_start_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["pending_phase_count"], 2)
        self.assertEqual(rows[0]["dominant_blocker_family"], "runtime_capture_missing")
        self.assertEqual(rows[0]["current_urgency"], "high")
        self.assertEqual(rows[0]["dashboard_note"], "phase1_gold_runtime_foundation leads a 2-phase pending stack with dominant blocker runtime_capture_missing.")

    def test_build_benchmark_completion_dashboard_lines_render_overall_snapshot(self) -> None:
        rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "pending_phase_count": 2,
                "dominant_blocker_family": "runtime_capture_missing",
                "current_urgency": "high",
                "dashboard_note": "phase1_gold_runtime_foundation leads a 2-phase pending stack with dominant blocker runtime_capture_missing.",
            }
        ]

        lines = build_benchmark_completion_dashboard_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Completion Dashboard", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("2", rendered)
        self.assertIn("runtime_capture_missing", rendered)
        self.assertIn("dominant blocker runtime_capture_missing", rendered)

    def test_build_benchmark_operator_brief_rows_summarize_operator_context(self) -> None:
        dashboard_rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "pending_phase_count": 3,
                "dominant_blocker_family": "runtime_capture_missing",
                "current_urgency": "high",
            }
        ]
        runbook_rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "recommended_action": "collect_controlled_runtime",
            }
        ]
        ledger_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "session_type": "timing_capture",
                "evidence_anchor": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
            }
        ]

        rows = build_benchmark_operator_brief_rows(dashboard_rows, runbook_rows, ledger_rows)

        self.assertEqual(rows[0]["operator_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["operator_action"], "collect_controlled_runtime")
        self.assertEqual(rows[0]["operator_session_type"], "timing_capture")
        self.assertEqual(rows[0]["operator_evidence"], "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes")
        self.assertEqual(rows[0]["operator_note"], "Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.")

    def test_build_benchmark_operator_brief_lines_render_plain_language_card(self) -> None:
        rows = [
            {
                "operator_step": "phase1_gold_runtime_foundation",
                "operator_action": "collect_controlled_runtime",
                "operator_session_type": "timing_capture",
                "operator_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "operator_note": "Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.",
            }
        ]

        lines = build_benchmark_operator_brief_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Operator Brief", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("timing_capture", rendered)
        self.assertIn("blocked by runtime_capture_missing", rendered)

    def test_build_benchmark_frontier_bridge_rows_connect_operator_and_frontier_queue(self) -> None:
        rows = build_benchmark_frontier_bridge_rows(
            operator_rows=[
                {
                    "operator_step": "phase1_gold_runtime_foundation",
                    "operator_action": "collect_controlled_runtime",
                    "operator_session_type": "timing_capture",
                    "operator_evidence": "hardware_label;device",
                    "operator_note": "Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.",
                }
            ],
            frontier_queue_rows=[
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["benchmark_operator_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["frontier_queue_head"], "meeteval_compatibility")
        self.assertIn("runtime", rows[0]["bridge_reason"].lower())

    def test_build_benchmark_frontier_bridge_lines_render_summary_card(self) -> None:
        lines = build_benchmark_frontier_bridge_lines(
            [
                {
                    "benchmark_operator_step": "phase1_gold_runtime_foundation",
                    "benchmark_operator_action": "collect_controlled_runtime",
                    "frontier_queue_head": "meeteval_compatibility",
                    "bridge_reason": "The benchmark runtime foundation still matters because it is the strongest shared evidence layer before narrower frontier follow-ups.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Frontier Bridge", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("meeteval_compatibility", rendered)

    def test_build_benchmark_frontier_bridge_checklist_rows_verify_operator_to_queue_bridge(self) -> None:
        rows = build_benchmark_frontier_bridge_checklist_rows(
            [
                {
                    "operator_step": "phase1_gold_runtime_foundation",
                    "operator_action": "collect_controlled_runtime",
                    "operator_session_type": "timing_capture",
                    "operator_evidence": "hardware_label;device",
                    "operator_note": "Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.",
                }
            ],
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["benchmark_operator_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["frontier_queue_head"], "meeteval_compatibility")
        self.assertIn("bridge", rows[0]["checklist_goal"].lower())
        self.assertIn("shared evidence layer", rows[0]["bridge_reason"].lower())

    def test_build_benchmark_frontier_bridge_checklist_lines_render_bridge(self) -> None:
        lines = build_benchmark_frontier_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "benchmark_operator_step": "phase1_gold_runtime_foundation",
                    "benchmark_operator_action": "collect_controlled_runtime",
                    "frontier_queue_head": "meeteval_compatibility",
                    "checklist_goal": "Verify the frontier bridge for phase1_gold_runtime_foundation before advancing the benchmark stack.",
                    "bridge_reason": "The benchmark runtime foundation still matters because it is the strongest shared evidence layer before narrower frontier follow-ups.",
                    "next_gate": "Confirm this bridge before opening the frontier queue head.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Frontier Bridge Checklist", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("shared evidence layer", rendered)

    def test_build_benchmark_evidence_receipt_rows_capture_writeback_expectations(self) -> None:
        dashboard_rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
            }
        ]
        operator_brief_rows = [
            {
                "operator_step": "phase1_gold_runtime_foundation",
                "operator_action": "collect_controlled_runtime",
                "operator_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
            }
        ]
        ledger_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]
        phase_checkpoint_rows = [
            {
                "phase": "foundation",
                "checkpoint_action": "collect_controlled_runtime",
                "completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]

        rows = build_benchmark_evidence_receipt_rows(
            dashboard_rows,
            operator_brief_rows,
            ledger_rows,
            phase_checkpoint_rows,
        )

        self.assertEqual(rows[0]["receipt_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["receipt_action"], "collect_controlled_runtime")
        self.assertEqual(rows[0]["receipt_evidence"], "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes")
        self.assertEqual(rows[0]["receipt_completion_signal"], "Gold runtime foundation artifacts are rebuilt from controlled timing.")
        self.assertEqual(rows[0]["receipt_followup"], "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.")
        self.assertIn("phase1_gold_runtime_foundation", rows[0]["receipt_note"])

    def test_build_benchmark_evidence_receipt_lines_render_closeout_card(self) -> None:
        rows = [
            {
                "receipt_step": "phase1_gold_runtime_foundation",
                "receipt_action": "collect_controlled_runtime",
                "receipt_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "receipt_completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_followup": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_note": "After phase1_gold_runtime_foundation, write back the evidence payload and confirm the foundation completion signal.",
            }
        ]

        lines = build_benchmark_evidence_receipt_lines(rows)
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Evidence Receipt", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("collect_controlled_runtime", rendered)
        self.assertIn("Gold runtime foundation artifacts are rebuilt from controlled timing.", rendered)
        self.assertIn("write back the evidence payload", rendered)

    def test_build_benchmark_evidence_checklist_rows_order_writeback_steps(self) -> None:
        rows = build_benchmark_evidence_checklist_rows(
            [
                {
                    "receipt_step": "phase1_gold_runtime_foundation",
                    "receipt_action": "collect_controlled_runtime",
                    "receipt_evidence": "hardware_label;device;repeat_count;warmup_count",
                    "receipt_completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                    "receipt_followup": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                    "receipt_note": "After phase1_gold_runtime_foundation, write back the evidence payload and confirm the foundation completion signal.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["receipt_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["expected_evidence"], "results/tables/cascade_benchmark_evidence_receipt.json")
        self.assertIn("handoff packet", rows[0]["preflight_step"].lower())
        self.assertIn("completion signal", rows[0]["next_gate"].lower())

    def test_build_benchmark_evidence_checklist_lines_render_writeback_queue(self) -> None:
        lines = build_benchmark_evidence_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "receipt_step": "phase1_gold_runtime_foundation",
                    "receipt_action": "collect_controlled_runtime",
                    "checklist_goal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                    "expected_evidence": "results/tables/cascade_benchmark_evidence_receipt.json",
                    "preflight_step": "Open the handoff packet and verify the receipt payload before the benchmark writeback.",
                    "next_gate": "Write back the evidence receipt and confirm the completion signal before the next step.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Evidence Checklist", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("results/tables/cascade_benchmark_evidence_receipt.json", rendered)
        self.assertIn("writeback path", rendered)

    def test_build_benchmark_receipt_bridge_rows_link_packet_to_receipt(self) -> None:
        runbook_rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "recommended_action": "collect_controlled_runtime",
                "session_type": "timing_capture",
                "required_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "urgency": "high",
                "runbook_note": "Start with phase1_gold_runtime_foundation because it is do_now and root.",
            }
        ]
        receipt_rows = [
            {
                "receipt_step": "phase1_gold_runtime_foundation",
                "receipt_action": "collect_controlled_runtime",
                "receipt_evidence": "hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes",
                "receipt_completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_followup": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_note": "After phase1_gold_runtime_foundation, write back the evidence payload and confirm the foundation completion signal.",
            }
        ]

        rows = build_benchmark_receipt_bridge_rows(runbook_rows, receipt_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["benchmark_step"], "phase1_gold_runtime_foundation")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/cascade_benchmark_handoff_packet.md")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/cascade_benchmark_evidence_receipt.md")
        self.assertIn("write back", rows[0]["bridge_note"].lower())

    def test_build_benchmark_receipt_bridge_lines_render_bridge(self) -> None:
        lines = build_benchmark_receipt_bridge_lines(
            [
                {
                    "benchmark_step": "phase1_gold_runtime_foundation",
                    "prerequisite_artifact": "results/figures/cascade_benchmark_handoff_packet.md",
                    "receipt_target": "results/figures/cascade_benchmark_evidence_receipt.md",
                    "bridge_note": "Open the handoff packet first, then write back through the evidence receipt after the current benchmark step.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Receipt Bridge", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("cascade_benchmark_handoff_packet.md", rendered)
        self.assertIn("cascade_benchmark_evidence_receipt.md", rendered)

    def test_build_artifact_index_rows_include_benchmark_status_board(self) -> None:
        rows = build_artifact_index_rows()
        status_row = next(row for row in rows if row["artifact_id"] == "cross_dataset_benchmark_status")
        frontier_bridge_checklist_row = next(
            row for row in rows if row["artifact_id"] == "cross_dataset_benchmark_frontier_bridge_checklist"
        )

        self.assertEqual(status_row["dataset"], "cross_dataset")
        self.assertEqual(status_row["artifact_path"], "results/figures/cascade_benchmark_status.md")
        self.assertIn("status board", status_row["intended_use"])
        self.assertEqual(frontier_bridge_checklist_row["artifact_path"], "results/figures/cascade_benchmark_frontier_bridge_checklist.md")
        self.assertIn("Verification checklist", frontier_bridge_checklist_row["intended_use"])

    def test_build_benchmark_packet_lines_consolidate_execution_artifacts(self) -> None:
        readiness_rows = [
            {
                "artifact_id": "gold_runtime_normalization",
                "benchmark_priority": "high",
                "benchmark_status": "repo_local_runtime_only",
                "next_evidence_step": "Run a controlled same-hardware timing sweep for the selected routes.",
            }
        ]
        plan_rows = [
            {
                "step_order": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "command": "python -m src.compute_aware_cascade",
            }
        ]
        checklist_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "session_type": "timing_capture",
                "required_metadata": "hardware_label;device;repeat_count;warmup_count",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]
        manifest_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "hardware_label": "TODO",
                "device": "TODO",
                "repeat_count": "TODO",
                "warmup_count": "TODO",
            }
        ]
        status_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "execution_status": "template_only",
                "readiness_signal": "pending_execution",
                "missing_fields": "hardware_label;device;repeat_count;warmup_count",
                "acceptance_check": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]
        execution_summary_rows = [
            {
                "phase": "foundation",
                "step_count": 1,
                "filled_step_count": 0,
                "template_only_step_count": 1,
                "total_pending_field_count": 4,
                "readiness_label": "pending_execution",
                "primary_blocking_category": "runtime_capture_missing",
                "recommended_next_action": "collect_controlled_runtime",
                "covered_datasets": "gold",
            }
        ]

        execution_queue_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "priority_bucket": "do_now",
                "blocking_category": "runtime_capture_missing",
                "next_action": "collect_controlled_runtime",
                "pending_field_count": 4,
                "queue_reason": "runtime_capture_missing with 4 pending fields",
            }
        ]
        session_ledger_rows = [
            {
                "queue_rank": 1,
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "session_type": "timing_capture",
                "priority_bucket": "do_now",
                "evidence_anchor": "hardware_label;device;repeat_count;warmup_count",
                "todo_field_count": 4,
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]
        dependency_graph_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "step_order": 1,
                "phase": "foundation",
                "dataset_scope": "gold",
                "queue_rank": 1,
                "priority_bucket": "do_now",
                "depends_on_step": "",
                "dependency_status": "root",
                "unlocks_step": "phase3_gold_surface_refresh",
                "dependency_note": "phase1_gold_runtime_foundation unlocks the first gold surface refresh step.",
            }
        ]
        blocker_matrix_rows = [
            {
                "plan_step_id": "phase1_gold_runtime_foundation",
                "phase": "foundation",
                "dataset_scope": "gold",
                "queue_rank": 1,
                "priority_bucket": "do_now",
                "blocking_category": "runtime_capture_missing",
                "dependency_status": "root",
                "pending_field_count": 4,
                "severity_band": "high",
                "matrix_note": "do_now / root / 4 pending fields",
            }
        ]
        runbook_card_rows = [
            {
                "recommended_start_step": "phase1_gold_runtime_foundation",
                "recommended_action": "collect_controlled_runtime",
                "session_type": "timing_capture",
                "required_evidence": "hardware_label;device;repeat_count;warmup_count",
                "completion_note": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "urgency": "high",
                "runbook_note": "Start with phase1_gold_runtime_foundation because it is do_now and root.",
            }
        ]
        milestone_card_rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "next_milestone_step": "phase2_synthetic_runtime_foundation",
                "remaining_phase_count": 3,
                "current_urgency": "high",
                "milestone_note": "phase1_gold_runtime_foundation unlocks phase2_synthetic_runtime_foundation and leaves 3 pending phases.",
            }
        ]
        phase_checkpoint_card_rows = [
            {
                "phase": "foundation",
                "readiness_label": "pending_execution",
                "primary_blocking_category": "runtime_capture_missing",
                "checkpoint_action": "collect_controlled_runtime",
                "completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
            }
        ]
        completion_dashboard_rows = [
            {
                "current_start_step": "phase1_gold_runtime_foundation",
                "pending_phase_count": 3,
                "dominant_blocker_family": "runtime_capture_missing",
                "current_urgency": "high",
                "dashboard_note": "phase1_gold_runtime_foundation leads a 3-phase pending stack with dominant blocker runtime_capture_missing.",
            }
        ]
        operator_brief_rows = [
            {
                "operator_step": "phase1_gold_runtime_foundation",
                "operator_action": "collect_controlled_runtime",
                "operator_session_type": "timing_capture",
                "operator_evidence": "hardware_label;device;repeat_count;warmup_count",
                "operator_note": "Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.",
            }
        ]
        frontier_bridge_checklist_rows = [
            {
                "checklist_order": "1",
                "benchmark_operator_step": "phase1_gold_runtime_foundation",
                "benchmark_operator_action": "collect_controlled_runtime",
                "frontier_queue_head": "meeteval_compatibility",
                "checklist_goal": "Verify the frontier bridge for phase1_gold_runtime_foundation before advancing the benchmark stack.",
                "bridge_reason": "The benchmark runtime foundation still matters because it is the strongest shared evidence layer before narrower frontier follow-ups.",
                "next_gate": "Confirm this bridge before opening the frontier queue head.",
            }
        ]
        evidence_receipt_rows = [
            {
                "receipt_step": "phase1_gold_runtime_foundation",
                "receipt_action": "collect_controlled_runtime",
                "receipt_evidence": "hardware_label;device;repeat_count;warmup_count",
                "receipt_completion_signal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_followup": "collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "receipt_note": "After phase1_gold_runtime_foundation, write back the evidence payload and confirm the foundation completion signal.",
            }
        ]
        evidence_checklist_rows = [
            {
                "checklist_order": "1",
                "receipt_step": "phase1_gold_runtime_foundation",
                "receipt_action": "collect_controlled_runtime",
                "checklist_goal": "Gold runtime foundation artifacts are rebuilt from controlled timing.",
                "expected_evidence": "results/tables/cascade_benchmark_evidence_receipt.json",
                "preflight_step": "Open the handoff packet and verify the receipt payload before the benchmark writeback.",
                "next_gate": "Write back the evidence receipt and confirm the completion signal before the next step.",
            }
        ]

        lines = build_benchmark_packet_lines(
            readiness_rows,
            plan_rows,
            checklist_rows,
            manifest_rows,
            status_rows,
            execution_summary_rows,
            execution_queue_rows,
            session_ledger_rows,
            dependency_graph_rows,
            blocker_matrix_rows,
            runbook_card_rows,
            milestone_card_rows,
            phase_checkpoint_card_rows,
            completion_dashboard_rows,
            operator_brief_rows,
            frontier_bridge_checklist_rows,
            evidence_receipt_rows,
            evidence_checklist_rows,
        )
        rendered = "\n".join(lines)

        self.assertIn("# Cascade Benchmark Handoff Packet", rendered)
        self.assertIn("## Readiness Snapshot", rendered)
        self.assertIn("## Execution Summary", rendered)
        self.assertIn("## Execution Queue", rendered)
        self.assertIn("## Session Ledger", rendered)
        self.assertIn("## Dependency Graph", rendered)
        self.assertIn("## Blocker Matrix", rendered)
        self.assertIn("## Runbook Card", rendered)
        self.assertIn("## Milestone Card", rendered)
        self.assertIn("## Phase Checkpoint Card", rendered)
        self.assertIn("## Completion Dashboard", rendered)
        self.assertIn("## Operator Brief", rendered)
        self.assertIn("## Frontier Bridge Checklist", rendered)
        self.assertIn("## Evidence Receipt", rendered)
        self.assertIn("## Evidence Checklist", rendered)
        self.assertIn("## Execution Status", rendered)
        self.assertIn("phase1_gold_runtime_foundation", rendered)
        self.assertIn("runtime_capture_missing", rendered)
        self.assertIn("pending_execution", rendered)
        self.assertIn("do_now", rendered)
        self.assertIn("hardware_label;device;repeat_count;warmup_count", rendered)
        self.assertIn("phase1_gold_runtime_foundation unlocks the first gold surface refresh step.", rendered)
        self.assertIn("do_now / root / 4 pending fields", rendered)
        self.assertIn("Start with phase1_gold_runtime_foundation because it is do_now and root.", rendered)
        self.assertIn("phase1_gold_runtime_foundation unlocks phase2_synthetic_runtime_foundation and leaves 3 pending phases.", rendered)
        self.assertIn("Gold runtime foundation artifacts are rebuilt from controlled timing.", rendered)
        self.assertIn("phase1_gold_runtime_foundation leads a 3-phase pending stack with dominant blocker runtime_capture_missing.", rendered)
        self.assertIn("Run phase1_gold_runtime_foundation now; it is blocked by runtime_capture_missing and carries high urgency.", rendered)
        self.assertIn("After phase1_gold_runtime_foundation, write back the evidence payload and confirm the foundation completion signal.", rendered)
        self.assertIn("Write back the evidence receipt and confirm the completion signal before the next step.", rendered)
        self.assertIn("hardware_label;device;repeat_count;warmup_count", rendered)
        self.assertIn("Manifest template fields: hardware_label, device, repeat_count, warmup_count", rendered)


if __name__ == "__main__":
    unittest.main()
