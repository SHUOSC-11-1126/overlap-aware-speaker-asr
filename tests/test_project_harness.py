from __future__ import annotations

import unittest

from src.project_harness import (
    build_frontier_execution_queue_lines,
    build_frontier_execution_queue_checklist_lines,
    build_frontier_execution_queue_checklist_rows,
    build_frontier_execution_queue_rows,
    build_frontier_status_checklist_lines,
    build_frontier_status_checklist_rows,
    build_frontier_focus_card_lines,
    build_frontier_focus_card_checklist_lines,
    build_frontier_focus_card_checklist_rows,
    build_frontier_focus_card_rows,
    build_frontier_handoff_packet_lines,
    build_frontier_handoff_packet_rows,
    build_frontier_handoff_checklist_lines,
    build_frontier_handoff_checklist_rows,
    build_frontier_parallel_picklist_lines,
    build_frontier_parallel_picklist_rows,
    build_frontier_parallel_picklist_checklist_lines,
    build_frontier_parallel_picklist_checklist_rows,
    build_frontier_coordination_checklist_lines,
    build_frontier_coordination_checklist_rows,
    build_frontier_coordination_matrix_lines,
    build_frontier_coordination_matrix_rows,
    build_frontier_receipt_board_lines,
    build_frontier_receipt_board_rows,
    build_frontier_receipt_board_checklist_lines,
    build_frontier_receipt_board_checklist_rows,
    build_frontier_receipt_checklist_lines,
    build_frontier_receipt_checklist_rows,
    build_frontier_receipt_map_lines,
    build_frontier_receipt_map_checklist_lines,
    build_frontier_receipt_map_checklist_rows,
    build_frontier_receipt_map_rows,
    build_frontier_receipt_packet_lines,
    build_frontier_receipt_packet_rows,
    build_frontier_writeback_index_lines,
    build_frontier_writeback_index_rows,
    build_frontier_writeback_checklist_lines,
    build_frontier_writeback_checklist_rows,
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

    def test_build_frontier_status_checklist_rows_preserve_frontier_order(self) -> None:
        rows = build_frontier_status_checklist_rows(
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

        self.assertEqual([row["checklist_order"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["frontier_id"], "speaker_profile")
        self.assertIn("status entry", rows[0]["checklist_goal"].lower())

    def test_build_frontier_status_checklist_lines_render_table(self) -> None:
        lines = build_frontier_status_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "frontier_id": "speaker_profile",
                    "status": "documented_skill",
                    "evidence_path": "docs/skills/skill_03_speaker_profile_voiceprint.md",
                    "expected_output": "speaker profile triage card",
                    "next_step": "Use the triage card to justify a stronger profile method while keeping the signal scoped to risk detection.",
                    "checklist_goal": "Verify the frontier status entry for speaker_profile before it is converted into queue order.",
                    "status_note": "Read the evidence path first, then confirm the expected output and next step before advancing.",
                    "next_gate": "Confirm this status row before building the execution queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Status Checklist", rendered)
        self.assertIn("speaker_profile", rendered)
        self.assertIn("evidence_path", rendered)

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

    def test_build_frontier_execution_queue_checklist_rows_preserve_queue_order(self) -> None:
        rows = build_frontier_execution_queue_checklist_rows(
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

        self.assertEqual([row["checklist_order"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertIn("queue entry", rows[0]["checklist_goal"].lower())

    def test_build_frontier_execution_queue_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_execution_queue_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "why_now": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                    "checklist_goal": "Verify the execution queue entry for meeteval_compatibility before opening the next frontier artifact.",
                    "queue_note": "Read the queue order first, then keep the entry artifact and why-now note visible while you confirm priority.",
                    "next_gate": "Confirm this queue row before moving to the next frontier entry.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Execution Queue Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("why_now", rendered)

    def test_build_frontier_parallel_picklist_checklist_rows_point_queue_head_to_pickup_step(self) -> None:
        rows = build_frontier_parallel_picklist_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertIn("parallel", rows[0]["checklist_goal"].lower())
        self.assertIn("pickup artifact", rows[0]["parallelism_note"].lower())

    def test_build_frontier_parallel_picklist_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_parallel_picklist_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Pick up meeteval_compatibility in parallel only after confirming queue order.",
                    "parallelism_note": "Check the queue head first, then open the pickup artifact before any parallel action.",
                    "next_gate": "Complete the pickup artifact and keep the receipt target visible for writeback.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Parallel Picklist Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("pickup path", rendered)

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

    def test_build_frontier_focus_card_checklist_rows_point_queue_head_to_focus_step(self) -> None:
        rows = build_frontier_focus_card_checklist_rows(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "current_action": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertIn("focus card", rows[0]["checklist_goal"].lower())
        self.assertIn("current action", rows[0]["focus_note"].lower())

    def test_build_frontier_focus_card_checklist_lines_render_card(self) -> None:
        lines = build_frontier_focus_card_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "current_action": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
                    "checklist_goal": "Confirm the current focus card for meeteval_compatibility before reading farther.",
                    "focus_note": "Read the queue head first, then keep the entry artifact and current action visible while you decide the next pass.",
                    "next_gate": "Confirm the focus card snapshot before moving to the next frontier.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Focus Card Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("current action", rendered)

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
        self.assertEqual(rows[0]["next_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertIn("single narrow dry run", rows[0]["execution_intent"].lower())
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rows[0]["expected_evidence"])
        self.assertIn("coordination-only", rows[0]["handoff_scope"].lower())

    def test_build_frontier_handoff_packet_lines_render_packet(self) -> None:
        lines = build_frontier_handoff_packet_lines(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "next_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "execution_intent": "Run a single narrow dry run handoff step before any broader claim.",
                    "expected_evidence": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "handoff_scope": "Coordination-only packet; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Handoff Packet", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_handoff_checklist_rows_point_queue_head_to_open_artifact_step(self) -> None:
        rows = build_frontier_handoff_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["next_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertIn("handoff packet", rows[0]["checklist_goal"].lower())
        self.assertIn("receipt target", rows[0]["execution_intent"].lower())

    def test_build_frontier_handoff_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_handoff_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "next_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Use the handoff packet to stage the next frontier pass for meeteval_compatibility.",
                    "execution_intent": "Open the next artifact first, then keep the receipt target visible for the narrow follow-up step.",
                    "next_gate": "Confirm the handoff packet snapshot before advancing the queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Handoff Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("open-artifact path", rendered)

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
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("receipt", rows[0]["execution_note"].lower())
        self.assertIn("coordination-only", rows[0]["packet_scope"].lower())

    def test_build_frontier_receipt_packet_lines_render_packet(self) -> None:
        lines = build_frontier_receipt_packet_lines(
            [
                {
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "execution_note": "Open the handoff first, then write back to the receipt target after the narrow dry run.",
                    "packet_scope": "Coordination-only packet; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Packet", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_receipt_checklist_rows_point_queue_head_to_writeback_step(self) -> None:
        rows = build_frontier_receipt_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("write back", rows[0]["checklist_goal"].lower())
        self.assertIn("receipt target", rows[0]["next_gate"].lower())

    def test_build_frontier_receipt_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_receipt_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Write back the receipt for meeteval_compatibility before any broader frontier claim.",
                    "preflight_step": "Open the prerequisite artifact and confirm the receipt target before the writeback step.",
                    "next_gate": "Fill the receipt target and confirm the frontier writeback before advancing the queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)
        self.assertIn("writeback path", rendered)

    def test_build_frontier_receipt_map_rows_cover_all_current_frontiers(self) -> None:
        rows = build_frontier_receipt_map_rows(
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

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertEqual(rows[1]["current_frontier"], "external_validation")
        self.assertEqual(rows[1]["receipt_target"], "results/tables/external_validation_slice_receipt.json")
        self.assertIn("coordination-only", rows[1]["map_scope"].lower())

    def test_build_frontier_receipt_map_lines_render_table(self) -> None:
        lines = build_frontier_receipt_map_lines(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "map_note": "Open the handoff first, then use the receipt target for writeback.",
                    "map_scope": "Coordination-only map; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Map", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_receipt_map_checklist_rows_preserve_map_order(self) -> None:
        rows = build_frontier_receipt_map_checklist_rows(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "map_note": "Open the prerequisite artifact first, then use the receipt target for writeback.",
                    "map_scope": "Coordination-only map; not a claim of completed frontier execution.",
                },
                {
                    "queue_order": "2",
                    "current_frontier": "external_validation",
                    "prerequisite_artifact": "results/figures/external_validation_prioritization.md",
                    "receipt_target": "results/tables/external_validation_slice_receipt.json",
                    "map_note": "Open the prerequisite artifact first, then use the receipt target for writeback.",
                    "map_scope": "Coordination-only map; not a claim of completed frontier execution.",
                },
            ]
        )

        self.assertEqual([row["checklist_order"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertIn("receipt map", rows[0]["checklist_goal"].lower())

    def test_build_frontier_receipt_map_checklist_lines_render_table(self) -> None:
        lines = build_frontier_receipt_map_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Verify the receipt map entry for meeteval_compatibility before opening the next frontier artifact.",
                    "map_note": "Open the prerequisite artifact first, then use the receipt target for writeback.",
                    "next_gate": "Confirm this map row before moving to the next receipt path.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Map Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("receipt_target", rendered)

    def test_build_frontier_parallel_picklist_rows_cover_all_current_frontiers(self) -> None:
        rows = build_frontier_parallel_picklist_rows(
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

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["current_frontier"], "meeteval_compatibility")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("parallel", rows[0]["pickup_note"].lower())
        self.assertEqual(rows[1]["current_frontier"], "external_validation")
        self.assertIn("coordination-only", rows[1]["picklist_scope"].lower())

    def test_build_frontier_parallel_picklist_lines_render_table(self) -> None:
        lines = build_frontier_parallel_picklist_lines(
            [
                {
                    "queue_order": "1",
                    "current_frontier": "meeteval_compatibility",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "pickup_note": "Safe to pick up in parallel after checking queue order and opening the pickup artifact first.",
                    "picklist_scope": "Coordination-only picklist; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Parallel Picklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_receipt_board_rows_cover_all_current_frontiers(self) -> None:
        rows = build_frontier_receipt_board_rows(
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

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertEqual(rows[1]["frontier_id"], "external_validation")
        self.assertEqual(rows[1]["receipt_target"], "results/tables/external_validation_slice_receipt.json")
        self.assertIn("breadth-first", rows[0]["board_note"].lower())

    def test_build_frontier_receipt_board_lines_render_table(self) -> None:
        lines = build_frontier_receipt_board_lines(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "board_status": "documented_skill",
                    "board_note": "Use this board as the single breadth-first receipt snapshot before moving to the next queue head.",
                    "board_scope": "Coordination-only board; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Board", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_receipt_board_checklist_rows_point_queue_head_to_snapshot_step(self) -> None:
        rows = build_frontier_receipt_board_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertIn("receipt board", rows[0]["checklist_goal"].lower())
        self.assertIn("board snapshot", rows[0]["board_note"].lower())

    def test_build_frontier_receipt_board_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_receipt_board_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Use the receipt board to stage the next frontier pass for meeteval_compatibility.",
                    "board_note": "Open the board snapshot first, then keep the pickup artifact visible while writing back.",
                    "next_gate": "Confirm the board snapshot and receipt target before the next queue head advances.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Receipt Board Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("snapshot path", rendered)

    def test_build_frontier_coordination_matrix_rows_cover_all_current_frontiers(self) -> None:
        rows = build_frontier_coordination_matrix_rows(
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

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["entry_artifact"], "MeetEval readiness card")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertEqual(rows[1]["frontier_id"], "external_validation")
        self.assertIn("coordination-only", rows[0]["coordination_scope"].lower())

    def test_build_frontier_coordination_matrix_lines_render_table(self) -> None:
        lines = build_frontier_coordination_matrix_lines(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "status": "documented_skill",
                    "entry_artifact": "MeetEval readiness card",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "coordination_note": "Coordinate this frontier by opening the pickup artifact first and writing back to the receipt target after the narrow next step.",
                    "coordination_scope": "Coordination-only matrix; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Coordination Matrix", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("MeetEval readiness card", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)

    def test_build_frontier_coordination_checklist_rows_point_queue_head_to_scan_step(self) -> None:
        rows = build_frontier_coordination_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["entry_artifact"], "MeetEval readiness card")
        self.assertEqual(rows[0]["pickup_artifact"], "results/figures/meeteval_cpwer_bridge_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("coordination matrix", rows[0]["checklist_goal"].lower())

    def test_build_frontier_coordination_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_coordination_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "pickup_artifact": "results/figures/meeteval_cpwer_bridge_handoff.md",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Use the coordination matrix to stage the next frontier pass for meeteval_compatibility.",
                    "coordination_note": "Open the entry artifact first, then keep the pickup artifact and receipt target visible for the next step.",
                    "next_gate": "Confirm the coordination matrix snapshot before advancing the queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Coordination Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)
        self.assertIn("scan path", rendered)

    def test_build_frontier_writeback_index_rows_cover_all_current_frontiers(self) -> None:
        rows = build_frontier_writeback_index_rows(
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

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("open results/figures/meeteval_cpwer_bridge_handoff.md first", rows[0]["writeback_note"].lower())
        self.assertEqual(rows[1]["frontier_id"], "external_validation")
        self.assertIn("coordination-only", rows[0]["writeback_scope"].lower())

    def test_build_frontier_writeback_index_lines_render_table(self) -> None:
        lines = build_frontier_writeback_index_lines(
            [
                {
                    "queue_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "writeback_note": "Open results/figures/meeteval_cpwer_bridge_handoff.md first, then write back to results/tables/meeteval_cpwer_bridge_receipt.json.",
                    "writeback_scope": "Coordination-only index; not a claim of completed frontier execution.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Writeback Index", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)
        self.assertIn("meeteval_cpwer_bridge_handoff.md", rendered)

    def test_build_frontier_writeback_checklist_rows_point_queue_head_to_closeout_step(self) -> None:
        rows = build_frontier_writeback_checklist_rows(
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
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["frontier_id"], "meeteval_compatibility")
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_bridge_receipt.json")
        self.assertIn("writeback path", rows[0]["checklist_goal"].lower())
        self.assertIn("open results/figures/meeteval_cpwer_bridge_handoff.md first", rows[0]["writeback_note"].lower())

    def test_build_frontier_writeback_checklist_lines_render_queue(self) -> None:
        lines = build_frontier_writeback_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "frontier_id": "meeteval_compatibility",
                    "entry_artifact": "MeetEval readiness card",
                    "receipt_target": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "checklist_goal": "Use the writeback index to complete the frontier writeback path for meeteval_compatibility.",
                    "writeback_note": "Open results/figures/meeteval_cpwer_bridge_handoff.md first, then write back to results/tables/meeteval_cpwer_bridge_receipt.json after the narrow next step.",
                    "next_gate": "Confirm the writeback index snapshot before advancing the queue.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Frontier Writeback Checklist", rendered)
        self.assertIn("meeteval_compatibility", rendered)
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rendered)
        self.assertIn("closeout path", rendered)


if __name__ == "__main__":
    unittest.main()
