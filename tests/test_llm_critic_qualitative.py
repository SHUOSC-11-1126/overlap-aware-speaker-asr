from __future__ import annotations

import unittest

from src.llm_correct import (
    build_critic_note_lines,
    build_critic_review_bridge_checklist_lines,
    build_critic_review_bridge_checklist_rows,
    build_critic_review_checklist_lines,
    build_critic_review_checklist_rows,
    build_critic_review_queue_lines,
    build_critic_review_queue_rows,
    build_critic_review_receipt_lines,
    build_critic_review_receipt_rows,
    build_critic_rows,
)


class LlmCriticQualitativeTest(unittest.TestCase):
    def test_build_critic_rows_explain_risk_and_repair(self) -> None:
        rows = build_critic_rows(
            risk_rows=[
                {
                    "case_id": "HeavyOverlap",
                    "risk_level": "medium",
                    "risk_flags": "length_inflation_risk;method_disagreement_risk",
                    "recommended_action": "repair separated output with cleaned transcript",
                }
            ],
            profile_rows=[
                {
                    "case_id": "HeavyOverlap",
                    "best_profile_alignment": "swapped",
                    "profile_confidence_gap": 0.411129,
                    "hypothesis_source": "separated_whisper_cleaned",
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertIn("length_inflation_risk", rows[0]["risk_explanation"])
        self.assertIn("cleaned transcript", rows[0]["candidate_repair"])
        self.assertIn("swapped", rows[0]["uncertainty_note"])
        self.assertEqual(rows[0]["label"], "qualitative/demo")

    def test_build_critic_note_lines_render_qualitative_warning(self) -> None:
        lines = build_critic_note_lines(
            [
                {
                    "case_id": "HeavyOverlap",
                    "label": "qualitative/demo",
                    "risk_explanation": "length_inflation_risk and method disagreement both suggest unstable separated output.",
                    "candidate_repair": "Try the cleaned transcript first before treating the separated output as final.",
                    "uncertainty_note": "Profile alignment still prefers swapped, so attribution remains uncertain.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Qualitative Note", rendered)
        self.assertIn("qualitative", rendered)
        self.assertIn("HeavyOverlap", rendered)
        self.assertIn("cleaned transcript", rendered)
        self.assertIn("attribution remains uncertain", rendered)

    def test_build_critic_review_queue_rows_prioritize_highest_uncertainty(self) -> None:
        rows = build_critic_review_queue_rows(
            [
                {
                    "case_id": "HeavyOverlap",
                    "label": "qualitative/demo",
                    "risk_explanation": "length_inflation_risk suggests unstable output.",
                    "candidate_repair": "Try cleaned transcript first.",
                    "uncertainty_note": "Profile alignment still prefers swapped, so attribution remains uncertain.",
                },
                {
                    "case_id": "LightOverlap",
                    "label": "qualitative/demo",
                    "risk_explanation": "The selector reports a medium risk state even without explicit flags.",
                    "candidate_repair": "Try mixed transcript first.",
                    "uncertainty_note": "No profile alignment signal is available, so attribution remains uncertain.",
                },
            ]
        )

        self.assertEqual(rows[0]["queue_order"], "1")
        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertEqual(rows[0]["review_priority"], "high")
        self.assertIn("swapped", rows[0]["why_now"])
        self.assertEqual(rows[1]["review_priority"], "medium")

    def test_build_critic_review_queue_lines_render_ordered_table(self) -> None:
        lines = build_critic_review_queue_lines(
            [
                {
                    "queue_order": "1",
                    "case_id": "HeavyOverlap",
                    "label": "qualitative/demo",
                    "review_priority": "high",
                    "why_now": "Risk flags plus swapped-profile uncertainty make this the strongest first review target.",
                    "candidate_repair": "Try cleaned transcript first.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Queue", rendered)
        self.assertIn("HeavyOverlap", rendered)
        self.assertIn("review_priority", rendered)
        self.assertIn("first review target", rendered)

    def test_build_critic_review_receipt_rows_create_template_evidence_target(self) -> None:
        rows = build_critic_review_receipt_rows(
            [
                {
                    "queue_order": "1",
                    "case_id": "HeavyOverlap",
                    "label": "qualitative/demo",
                    "review_priority": "high",
                    "why_now": "Risk flags plus swapped-profile uncertainty make this the strongest first review target.",
                    "candidate_repair": "Try cleaned transcript first.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["review_scope"], "HeavyOverlap")
        self.assertIn("review queue", rows[0]["expected_inputs"].lower())
        self.assertIn("diagnostic", rows[0]["expected_outputs"].lower())
        self.assertIn("has been executed", rows[0]["writeback_note"].lower())

    def test_build_critic_review_receipt_lines_render_template(self) -> None:
        lines = build_critic_review_receipt_lines(
            [
                {
                    "execution_status": "template_only",
                    "review_scope": "HeavyOverlap",
                    "expected_inputs": "Critic review queue head plus one qualitative review note stub.",
                    "expected_outputs": "Diagnostic critic-pass note and a narrow review writeback.",
                    "writeback_note": "No critic-style review pass has been executed yet; fill this receipt only after the first review.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Receipt", rendered)
        self.assertIn("template_only", rendered)
        self.assertIn("HeavyOverlap", rendered)
        self.assertIn("has been executed yet", rendered)

    def test_build_critic_review_bridge_checklist_rows_link_queue_to_receipt(self) -> None:
        rows = build_critic_review_bridge_checklist_rows(
            [
                {
                    "queue_order": "1",
                    "case_id": "HeavyOverlap",
                    "label": "qualitative/demo",
                    "review_priority": "high",
                    "why_now": "Risk flags plus swapped-profile uncertainty make this the strongest first review target.",
                    "candidate_repair": "Try cleaned transcript first.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/llm_critic_review_queue.md")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/llm_critic_review_receipt.md")
        self.assertIn("bridge", rows[0]["checklist_goal"].lower())

    def test_build_critic_review_bridge_checklist_lines_render_bridge(self) -> None:
        lines = build_critic_review_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "prerequisite_artifact": "results/figures/llm_critic_review_queue.md",
                    "receipt_target": "results/figures/llm_critic_review_receipt.md",
                    "checklist_goal": "Verify the critic review bridge for HeavyOverlap before any repair claim is advanced.",
                    "bridge_note": "Open the review queue first, then write back through the receipt target for the high review pass.",
                    "next_gate": "Confirm this bridge before opening the review receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Bridge Checklist", rendered)
        self.assertIn("HeavyOverlap", rendered)
        self.assertIn("llm_critic_review_queue.md", rendered)
        self.assertIn("llm_critic_review_receipt.md", rendered)

    def test_build_critic_review_checklist_rows_order_preflight_steps(self) -> None:
        rows = build_critic_review_checklist_rows(
            build_critic_review_queue_rows(
                [
                    {
                        "case_id": "HeavyOverlap",
                        "label": "qualitative/demo",
                        "risk_explanation": "length_inflation_risk suggests unstable output.",
                        "candidate_repair": "Try cleaned transcript first.",
                        "uncertainty_note": "Profile alignment still prefers swapped, so attribution remains uncertain.",
                    }
                ]
            )
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertEqual(rows[0]["expected_evidence"], "results/tables/llm_critic_review_receipt.json")
        self.assertIn("critic-style repair note", rows[0]["preflight_step"].lower())
        self.assertIn("receipt", rows[0]["next_gate"].lower())

    def test_build_critic_review_checklist_lines_render_ordered_queue(self) -> None:
        lines = build_critic_review_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "review_priority": "high",
                    "checklist_goal": "Try cleaned transcript first.",
                    "expected_evidence": "results/tables/llm_critic_review_receipt.json",
                    "preflight_step": "Confirm the strongest risk flags before drafting the first critic-style repair note.",
                    "next_gate": "Fill one critic review receipt before promoting any repair claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Checklist", rendered)
        self.assertIn("HeavyOverlap", rendered)
        self.assertIn("results/tables/llm_critic_review_receipt.json", rendered)
        self.assertIn("qualitative only", rendered)


if __name__ == "__main__":
    unittest.main()
