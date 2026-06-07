from __future__ import annotations

import unittest

from src.external_validation_candidates import (
    build_external_validation_candidate_lines,
    build_external_validation_candidate_rows,
    build_external_validation_checklist_lines,
    build_external_validation_checklist_rows,
    build_external_validation_slice_handoff_lines,
    build_external_validation_slice_handoff_rows,
    build_external_validation_slice_bridge_checklist_lines,
    build_external_validation_slice_bridge_checklist_rows,
    build_external_validation_slice_receipt_lines,
    build_external_validation_slice_receipt_rows,
    build_external_validation_prioritization_lines,
    build_external_validation_prioritization_rows,
)


class ExternalValidationCandidatesTest(unittest.TestCase):
    def test_build_external_validation_candidate_rows_cover_named_datasets(self) -> None:
        rows = build_external_validation_candidate_rows()

        by_name = {row["dataset_name"]: row for row in rows}

        self.assertIn("AISHELL-4", by_name)
        self.assertIn("AliMeeting", by_name)
        self.assertIn("AMI", by_name)
        self.assertIn("LibriCSS", by_name)
        self.assertEqual(by_name["AISHELL-4"]["label"], "external/sanity-check")
        self.assertIn("license", by_name["AISHELL-4"]["license_note"].lower())
        self.assertIn("overlap", by_name["LibriCSS"]["fit_note"].lower())

    def test_build_external_validation_candidate_lines_render_summary(self) -> None:
        lines = build_external_validation_candidate_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "source_note": "Official AISHELL-4 release page.",
                    "license_note": "Check the official license before use.",
                    "fit_note": "Multi-speaker meeting data with realistic overlap.",
                    "first_preprocessing_step": "Map one small subset into the repository speaker-reference format.",
                    "next_action": "Confirm license and select a tiny sanity-check subset.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Candidates", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("external/sanity-check", rendered)
        self.assertIn("Confirm license", rendered)

    def test_build_external_validation_prioritization_rows_recommend_first_dataset(self) -> None:
        rows = build_external_validation_prioritization_rows(build_external_validation_candidate_rows())

        by_name = {row["dataset_name"]: row for row in rows}

        self.assertEqual(by_name["AISHELL-4"]["priority_tier"], "start_here")
        self.assertEqual(by_name["AISHELL-4"]["recommended_order"], "1")
        self.assertIn("Chinese", by_name["AISHELL-4"]["why_now"])
        self.assertIn("license", by_name["AMI"]["readiness_note"].lower())
        self.assertEqual(by_name["LibriCSS"]["priority_tier"], "specialized_followup")

    def test_build_external_validation_prioritization_lines_render_ordered_card(self) -> None:
        lines = build_external_validation_prioritization_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "priority_tier": "start_here",
                    "recommended_order": "1",
                    "readiness_note": "License check plus small-format mapping are still required.",
                    "why_now": "Chinese meeting overlap makes this the closest first sanity-check target.",
                    "next_action": "Confirm license and stage one tiny meeting slice.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Prioritization", rendered)
        self.assertIn("start_here", rendered)
        self.assertIn("closest first sanity-check target", rendered)
        self.assertIn("recommended_order", rendered)

    def test_build_external_validation_slice_handoff_rows_turn_priority_head_into_first_slice(self) -> None:
        rows = build_external_validation_slice_handoff_rows(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "priority_tier": "start_here",
                    "recommended_order": "1",
                    "readiness_note": "License check plus a tiny repo-format mapping are still required before use.",
                    "why_now": "Chinese meeting overlap and domain fit make this the closest first sanity-check target.",
                    "next_action": "Confirm license and choose a tiny sanity-check slice.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertEqual(rows[0]["label"], "external/sanity-check")
        self.assertEqual(rows[0]["first_slice_shape"], "single_short_meeting_excerpt")
        self.assertIn("license", rows[0]["license_gate"].lower())
        self.assertIn("repo mapping", rows[0]["mapping_artifact"].lower())
        self.assertIn("dry run", rows[0]["dry_run_goal"].lower())

    def test_build_external_validation_slice_handoff_lines_render_packet(self) -> None:
        lines = build_external_validation_slice_handoff_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "first_slice_shape": "single_short_meeting_excerpt",
                    "license_gate": "Confirm official license terms before any local slice staging.",
                    "mapping_artifact": "Create one repo mapping stub for the first external slice.",
                    "dry_run_goal": "Run one narrow external sanity-check dry run without claiming a benchmark result.",
                    "handoff_note": "No external benchmark has been run yet; this card only frames the first slice.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Handoff", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("single_short_meeting_excerpt", rendered)
        self.assertIn("No external benchmark has been run yet", rendered)

    def test_build_external_validation_slice_receipt_rows_create_template_evidence_target(self) -> None:
        rows = build_external_validation_slice_receipt_rows(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "first_slice_shape": "single_short_meeting_excerpt",
                    "license_gate": "Confirm official license terms before any local slice staging.",
                    "mapping_artifact": "Create one repo mapping stub for the first external slice.",
                    "dry_run_goal": "Run one narrow external sanity-check dry run for AISHELL-4 without claiming a benchmark result.",
                    "handoff_note": "No external benchmark has been run yet; this card only frames the first slice.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["slice_scope"], "single_short_meeting_excerpt")
        self.assertIn("license confirmation", rows[0]["expected_inputs"].lower())
        self.assertIn("diagnostic", rows[0]["expected_outputs"].lower())
        self.assertIn("has been executed yet", rows[0]["writeback_note"].lower())

    def test_build_external_validation_slice_receipt_lines_render_template(self) -> None:
        lines = build_external_validation_slice_receipt_lines(
            [
                {
                    "execution_status": "template_only",
                    "slice_scope": "single_short_meeting_excerpt",
                    "expected_inputs": "License confirmation plus one repo mapping stub for AISHELL-4.",
                    "expected_outputs": "Diagnostic external-slice staging confirmation and a narrow run note.",
                    "writeback_note": "No external validation slice has been executed yet; fill this receipt only after the first dry run.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Receipt", rendered)
        self.assertIn("template_only", rendered)
        self.assertIn("single_short_meeting_excerpt", rendered)
        self.assertIn("No external validation slice has been executed yet", rendered)

    def test_build_external_validation_slice_bridge_checklist_rows_link_handoff_to_receipt(self) -> None:
        handoff_rows = [
            {
                "dataset_name": "AISHELL-4",
                "label": "external/sanity-check",
                "first_slice_shape": "single_short_meeting_excerpt",
                "license_gate": "Confirm official license terms before any local slice staging.",
                "mapping_artifact": "Create one repo mapping stub for the first external slice.",
                "dry_run_goal": "Run one narrow external sanity-check dry run for AISHELL-4 without claiming a benchmark result.",
                "handoff_note": "No external benchmark has been run yet; this card only frames the first slice.",
            }
        ]
        receipt_rows = [
            {
                "execution_status": "template_only",
                "slice_scope": "single_short_meeting_excerpt",
                "expected_inputs": "License confirmation plus one repo mapping stub for AISHELL-4.",
                "expected_outputs": "Diagnostic external-slice staging confirmation and a narrow run note.",
                "writeback_note": "No external validation slice has been executed yet; fill this receipt only after the first dry run.",
            }
        ]

        rows = build_external_validation_slice_bridge_checklist_rows(handoff_rows, receipt_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/external_validation_slice_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/external_validation_slice_receipt.md")
        self.assertIn("dry-run writeback", rows[0]["checklist_goal"].lower())

    def test_build_external_validation_slice_bridge_checklist_lines_render_bridge(self) -> None:
        lines = build_external_validation_slice_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "dataset_name": "AISHELL-4",
                    "prerequisite_artifact": "results/figures/external_validation_slice_handoff.md",
                    "receipt_target": "results/figures/external_validation_slice_receipt.md",
                    "checklist_goal": "Verify the first external slice bridge for AISHELL-4 before any dry-run writeback is advanced.",
                    "bridge_note": "Open the handoff packet first, then write back through the slice receipt for single_short_meeting_excerpt.",
                    "next_gate": "Confirm this bridge before opening the slice receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Bridge Checklist", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("external_validation_slice_handoff.md", rendered)
        self.assertIn("external_validation_slice_receipt.md", rendered)

    def test_build_external_validation_checklist_rows_order_preflight_steps(self) -> None:
        rows = build_external_validation_checklist_rows(
            build_external_validation_prioritization_rows(build_external_validation_candidate_rows())
        )

        by_name = {row["dataset_name"]: row for row in rows}

        self.assertEqual(by_name["AISHELL-4"]["checklist_order"], "1")
        self.assertEqual(by_name["AISHELL-4"]["expected_evidence"], "results/tables/external_validation_slice_receipt.json")
        self.assertIn("license", by_name["AMI"]["next_gate"].lower())
        self.assertIn("overlap", by_name["LibriCSS"]["validation_note"].lower())

    def test_build_external_validation_checklist_lines_render_ordered_queue(self) -> None:
        lines = build_external_validation_checklist_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "checklist_order": "1",
                    "preflight_step": "Confirm license and choose a tiny sanity-check slice.",
                    "expected_evidence": "results/tables/external_validation_slice_receipt.json",
                    "next_gate": "Confirm license, then stage one tiny slice before any evaluation claim.",
                    "validation_note": "Closest meeting-style target, so keep it at the front of the external sanity-check queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Checklist", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("external/sanity-check", rendered)
        self.assertIn("results/tables/external_validation_slice_receipt.json", rendered)


if __name__ == "__main__":
    unittest.main()
