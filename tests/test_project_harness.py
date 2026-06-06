from __future__ import annotations

import unittest

from src.project_harness import (
    build_frontier_execution_queue_lines,
    build_frontier_execution_queue_rows,
    build_frontier_focus_card_lines,
    build_frontier_focus_card_rows,
    build_frontier_handoff_packet_lines,
    build_frontier_handoff_packet_rows,
    build_frontier_receipt_packet_lines,
    build_frontier_receipt_packet_rows,
    build_report,
)


class ProjectHarnessTest(unittest.TestCase):
    def test_build_report_uses_repo_relative_project_root(self) -> None:
        report = build_report()
        self.assertEqual(report["project_root"], ".")

    def test_build_report_includes_frontier_status_rows(self) -> None:
        report = build_report()

        frontier_rows = report["frontier_status"]
        by_id = {row["frontier_id"]: row for row in frontier_rows}

        self.assertIn("speaker_profile", by_id)
        self.assertIn("meeteval_compatibility", by_id)
        self.assertIn("llm_critic", by_id)
        self.assertIn("external_validation", by_id)
        self.assertIn("demo_excellence", by_id)
        self.assertEqual(by_id["speaker_profile"]["status"], "documented_skill")
        self.assertIn("triage", by_id["speaker_profile"]["expected_output"])
        self.assertIn("stronger profile method", by_id["speaker_profile"]["next_step"])
        self.assertEqual(by_id["meeteval_compatibility"]["evidence_path"], "docs/skills/skill_04_meeteval_compatibility.md")
        self.assertIn("readiness", by_id["meeteval_compatibility"]["expected_output"])
        self.assertIn("dry run", by_id["meeteval_compatibility"]["next_step"])
        self.assertIn("queue", by_id["llm_critic"]["expected_output"])
        self.assertIn("review queue", by_id["llm_critic"]["next_step"])
        self.assertIn("prioritization", by_id["external_validation"]["expected_output"])
        self.assertIn("tiny sanity-check slice", by_id["external_validation"]["next_step"])
        self.assertIn("walkthrough", by_id["demo_excellence"]["expected_output"])
        self.assertIn("demo walk", by_id["demo_excellence"]["next_step"].lower())

    def test_build_frontier_execution_queue_rows_prioritize_actionable_handoffs(self) -> None:
        rows = build_frontier_execution_queue_rows(
            [
                {
                    "frontier_id": "speaker_profile",
                    "status": "documented_skill",
                    "evidence_path": "docs/skills/skill_03_speaker_profile_voiceprint.md",
                    "expected_output": "speaker profile triage card",
                    "next_step": "Use the triage card to justify a stronger profile method while keeping the signal scoped to risk detection.",
                },
                {
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "evidence_path": "docs/skills/skill_04_meeteval_compatibility.md",
                    "expected_output": "MeetEval readiness card",
                    "next_step": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                },
            ]
        )

        self.assertEqual(rows[0]["queue_order"], "1")
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertIn("dry run", rows[0]["why_now"])
        self.assertEqual(rows[1]["frontier_id"], "speaker_profile")

    def test_build_frontier_execution_queue_lines_render_table(self) -> None:
        lines = build_frontier_execution_queue_lines(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "A narrow dry run is now staged without claiming completed evaluation.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Execution Queue", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("entry_artifact", rendered)

    def test_build_frontier_focus_card_rows_pick_queue_head(self) -> None:
        rows = build_frontier_focus_card_rows(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                },
                {
                    "queue_order": "2",
                    "frontier_id": "external_validation",
                    "status": "documented_skill",
                    "entry_artifact": "external sanity-check prioritization card",
                    "why_now": "Use the prioritization card to map one tiny sanity-check slice without claiming a completed benchmark.",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["queue_order"], "1")
        self.assertIn("dry run", rows[0]["current_action"])

    def test_build_frontier_focus_card_lines_render_brief(self) -> None:
        lines = build_frontier_focus_card_lines(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "current_action": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Focus Card", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("MeetEval readiness card", rendered)

    def test_build_frontier_handoff_packet_rows_point_queue_head_to_next_artifact(self) -> None:
        rows = build_frontier_handoff_packet_rows(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["queue_order"], "1")
        self.assertEqual(rows[0]["next_artifact"], "results/figures/meeteval_dry_run_handoff.md")
        self.assertIn("single narrow dry run", rows[0]["execution_intent"].lower())
        self.assertIn("meeteval_dry_run_receipt.json", rows[0]["expected_evidence"])
        self.assertIn("coordination-only", rows[0]["handoff_scope"].lower())

    def test_build_frontier_handoff_packet_lines_render_packet(self) -> None:
        lines = build_frontier_handoff_packet_lines(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "next_artifact": "results/figures/meeteval_dry_run_handoff.md",
                    "execution_intent": "Run a single narrow dry run handoff step before any broader claim.",
                    "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                    "handoff_scope": "Coordination-only packet; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Handoff Packet", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_dry_run_handoff.md", rendered)
        self.assertIn("meeteval_dry_run_receipt.json", rendered)

    def test_build_frontier_receipt_packet_rows_point_queue_head_to_receipt_target(self) -> None:
        rows = build_frontier_receipt_packet_rows(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/meeteval_dry_run_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_dry_run_receipt.json")
        self.assertIn("receipt", rows[0]["execution_note"].lower())
        self.assertIn("coordination-only", rows[0]["packet_scope"].lower())

    def test_build_frontier_receipt_packet_lines_render_packet(self) -> None:
        lines = build_frontier_receipt_packet_lines(
            [
                {
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_dry_run_handoff.md",
                    "receipt_target": "results/tables/meeteval_dry_run_receipt.json",
                    "execution_note": "Open the handoff first, then write back to the receipt target after the narrow dry run.",
                    "packet_scope": "Coordination-only packet; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Packet", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_dry_run_handoff.md", rendered)
        self.assertIn("meeteval_dry_run_receipt.json", rendered)


if __name__ == "__main__":
    unittest.main()
