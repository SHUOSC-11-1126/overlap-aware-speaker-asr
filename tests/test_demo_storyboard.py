from __future__ import annotations

import unittest

from src.demo_storyboard import (
    build_demo_storyboard_cards,
    build_demo_storyboard_lines,
    build_demo_walkthrough_bridge_checklist_lines,
    build_demo_walkthrough_bridge_checklist_rows,
    build_demo_walkthrough_checklist_lines,
    build_demo_walkthrough_checklist_rows,
    build_demo_walkthrough_receipt_lines,
    build_demo_walkthrough_receipt_rows,
    build_demo_walkthrough_lines,
    build_demo_walkthrough_steps,
)


class DemoStoryboardTest(unittest.TestCase):
    def test_build_demo_storyboard_cards_cover_story_sections(self) -> None:
        cards = build_demo_storyboard_cards(
            {
                "baseline": "Selective separation beats blind separation.",
                "cascade": "router_v2 is the balanced default.",
                "frontier": "Breadth-first artifacts now exist across multiple frontiers.",
            }
        )

        titles = [card["title"] for card in cards]
        self.assertIn("Problem", titles)
        self.assertIn("Pipeline", titles)
        self.assertIn("Findings", titles)
        self.assertIn("Frontier", titles)
        findings = next(card for card in cards if card["title"] == "Findings")
        self.assertIn("router_v2", findings["body"])

    def test_build_demo_storyboard_lines_render_mermaid_and_cards(self) -> None:
        lines = build_demo_storyboard_lines(
            [
                {"title": "Problem", "body": "Overlap-aware ASR should separate selectively."},
                {"title": "Pipeline", "body": "Mixed ASR, separated ASR, routing, and evaluation compose the main flow."},
                {"title": "Findings", "body": "router_v2 is the balanced default and cleaned separation is the robust fallback."},
                {"title": "Frontier", "body": "Compute-aware, MeetEval, speaker profile, and critic bridges now exist."},
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Demo Storyboard", rendered)
        self.assertIn("```mermaid", rendered)
        self.assertIn("Problem", rendered)
        self.assertIn("router_v2", rendered)
        self.assertIn("critic bridges now exist", rendered)

    def test_build_demo_walkthrough_steps_cover_short_demo_flow(self) -> None:
        steps = build_demo_walkthrough_steps(
            {
                "baseline": "Selective separation beats blind separation on the gold benchmark.",
                "router": "router_v2 matches oracle-best average CER.",
                "frontier": "Frontier artifacts now cover external prioritization and qualitative critics.",
            }
        )

        self.assertEqual(steps[0]["step_id"], "1")
        self.assertIn("problem", steps[0]["focus"].lower())
        self.assertIn("oracle-best", steps[2]["talk_track"])
        self.assertIn("external prioritization", steps[3]["talk_track"])
        self.assertEqual(steps[-1]["step_id"], "5")

    def test_build_demo_walkthrough_lines_render_ordered_script(self) -> None:
        lines = build_demo_walkthrough_lines(
            [
                {
                    "step_id": "1",
                    "focus": "Problem framing",
                    "talk_track": "Start by explaining why overlap does not always justify separation.",
                    "artifact_anchor": "README.md",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Demo Walkthrough", rendered)
        self.assertIn("Problem framing", rendered)
        self.assertIn("artifact_anchor", rendered)

    def test_build_demo_walkthrough_receipt_rows_create_template_evidence_target(self) -> None:
        rows = build_demo_walkthrough_receipt_rows(
            [
                {
                    "step_id": "1",
                    "focus": "Problem framing",
                    "talk_track": "Start by explaining why overlap does not always justify separation.",
                    "artifact_anchor": "README.md",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["walkthrough_scope"], "step_1_problem_framing")
        self.assertIn("walkthrough", rows[0]["expected_inputs"].lower())
        self.assertIn("diagnostic", rows[0]["expected_outputs"].lower())
        self.assertIn("has been executed", rows[0]["writeback_note"].lower())

    def test_build_demo_walkthrough_receipt_lines_render_template(self) -> None:
        lines = build_demo_walkthrough_receipt_lines(
            [
                {
                    "execution_status": "template_only",
                    "walkthrough_scope": "step_1_problem_framing",
                    "expected_inputs": "Demo walkthrough head plus one narration note stub.",
                    "expected_outputs": "Diagnostic walkthrough note and a narrow presentation writeback.",
                    "writeback_note": "No demo walkthrough pass has been executed yet; fill this receipt only after the first run.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Demo Walkthrough Receipt", rendered)
        self.assertIn("template_only", rendered)
        self.assertIn("step_1_problem_framing", rendered)
        self.assertIn("has been executed yet", rendered)

    def test_build_demo_walkthrough_bridge_checklist_rows_link_walkthrough_to_receipt(self) -> None:
        rows = build_demo_walkthrough_bridge_checklist_rows(
            [
                {
                    "step_id": "1",
                    "focus": "Problem framing",
                    "talk_track": "Start by explaining why overlap does not always justify separation.",
                    "artifact_anchor": "README.md",
                }
            ],
            [
                {
                    "execution_status": "template_only",
                    "walkthrough_scope": "step_1_problem_framing",
                    "expected_inputs": "Demo walkthrough head plus one narration note stub.",
                    "expected_outputs": "Diagnostic walkthrough note and a narrow presentation writeback.",
                    "writeback_note": "No demo walkthrough pass has been executed yet; fill this receipt only after the first run.",
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["step_id"], "1")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/demo_walkthrough.md")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/demo_walkthrough_receipt.md")
        self.assertIn("bridge", rows[0]["checklist_goal"].lower())

    def test_build_demo_walkthrough_bridge_checklist_lines_render_bridge(self) -> None:
        lines = build_demo_walkthrough_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "step_id": "1",
                    "prerequisite_artifact": "results/figures/demo_walkthrough.md",
                    "receipt_target": "results/figures/demo_walkthrough_receipt.md",
                    "checklist_goal": "Verify the demo walkthrough bridge before any presentation claim is advanced.",
                    "bridge_note": "Open the walkthrough first, then write back through the receipt target for step_1_problem_framing and the Problem framing focus.",
                    "next_gate": "Confirm this bridge before opening the walkthrough receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Demo Walkthrough Bridge Checklist", rendered)
        self.assertIn("results/figures/demo_walkthrough.md", rendered)
        self.assertIn("results/figures/demo_walkthrough_receipt.md", rendered)
        self.assertIn("presentation support only", rendered)

    def test_build_demo_walkthrough_checklist_rows_order_execution_path(self) -> None:
        rows = build_demo_walkthrough_checklist_rows(
            [
                {
                    "step_id": "1",
                    "focus": "Problem framing",
                    "talk_track": "Start by explaining why overlap does not always justify separation.",
                    "artifact_anchor": "README.md",
                },
                {
                    "step_id": "2",
                    "focus": "Baseline evidence",
                    "talk_track": "Show the gold benchmark evidence and highlight the selected-route tradeoff.",
                    "artifact_anchor": "REPORT.md",
                },
            ]
        )

        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["step_id"], "1")
        self.assertIn("open readme.md", rows[0]["preflight_step"].lower())
        self.assertIn("receipt", rows[0]["expected_evidence"])
        self.assertEqual(rows[1]["checklist_order"], "2")
        self.assertIn("REPORT.md", rows[1]["artifact_anchor"])

    def test_build_demo_walkthrough_checklist_lines_render_ordered_script(self) -> None:
        lines = build_demo_walkthrough_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "step_id": "1",
                    "focus": "Problem framing",
                    "artifact_anchor": "README.md",
                    "checklist_goal": "Start by explaining why overlap does not always justify separation.",
                    "expected_evidence": "results/tables/demo_walkthrough_receipt.json",
                    "preflight_step": "Open README.md before presenting the problem framing step.",
                    "next_gate": "Fill the walkthrough receipt after the first presentation run.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Demo Walkthrough Checklist", rendered)
        self.assertIn("README.md", rendered)
        self.assertIn("presentation-ready execution path", rendered)
        self.assertIn("results/tables/demo_walkthrough_receipt.json", rendered)


if __name__ == "__main__":
    unittest.main()
