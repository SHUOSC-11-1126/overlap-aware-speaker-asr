from __future__ import annotations

import json
import unittest

from src.export_meeteval_compatibility import (
    load_hypothesis_payload,
    load_reference_payload,
    build_meeteval_compatibility_lines,
    build_meeteval_compatibility_rows,
    build_meeteval_dry_run_handoff_lines,
    build_meeteval_dry_run_handoff_rows,
    build_meeteval_dry_run_bridge_checklist_lines,
    build_meeteval_dry_run_bridge_checklist_rows,
    build_meeteval_dry_run_checklist_lines,
    build_meeteval_dry_run_checklist_rows,
    build_meeteval_dry_run_receipt_board_lines,
    build_meeteval_dry_run_receipt_board_rows,
    build_meeteval_dry_run_receipt_checklist_lines,
    build_meeteval_dry_run_receipt_checklist_rows,
    build_meeteval_dry_run_receipt_map_lines,
    build_meeteval_dry_run_receipt_map_rows,
    build_meeteval_dry_run_receipt_lines,
    build_meeteval_dry_run_receipt_rows,
    build_meeteval_readiness_lines,
    build_meeteval_readiness_rows,
    build_meeteval_segment_lines,
)


class MeetEvalCompatibilityTest(unittest.TestCase):
    def test_build_meeteval_compatibility_rows_summarize_reference_and_hypothesis(self) -> None:
        rows = build_meeteval_compatibility_rows(
            case_ids=["NoOverlap"],
            reference_payloads={
                "NoOverlap": {
                    "segments": [
                        {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                        {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
                    ]
                }
            },
            hypothesis_payloads={
                "NoOverlap": {
                    "segments": [
                        {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                        {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
                    ]
                }
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertEqual(rows[0]["reference_segment_count"], 2)
        self.assertEqual(rows[0]["hypothesis_segment_count"], 2)
        self.assertEqual(rows[0]["speaker_count"], 2)
        self.assertIn("compatibility bridge", rows[0]["observation"])

    def test_build_meeteval_segment_lines_render_jsonl_export(self) -> None:
        lines = build_meeteval_segment_lines(
            case_id="NoOverlap",
            source="reference",
            segments=[
                {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
            ],
        )

        payload = [json.loads(line) for line in lines]

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["session_id"], "NoOverlap")
        self.assertEqual(payload[0]["speaker"], "SPEAKER_1")
        self.assertEqual(payload[0]["source"], "reference")
        self.assertEqual(payload[1]["text"], "beta")

    def test_build_meeteval_compatibility_lines_render_note(self) -> None:
        lines = build_meeteval_compatibility_lines(
            [
                {
                    "case_id": "NoOverlap",
                    "reference_segment_count": 2,
                    "hypothesis_segment_count": 2,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "Compatibility bridge only; no cpWER claim yet.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Compatibility Note", rendered)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("meeteval_reference_segments.jsonl", rendered)
        self.assertIn("no cpWER claim yet", rendered)

    def test_build_meeteval_readiness_rows_summarize_fallback_and_next_step(self) -> None:
        rows = build_meeteval_readiness_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "reference_segment_count": 25,
                    "hypothesis_segment_count": 25,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "compatibility bridge only; this export does not claim cpWER evaluation yet.",
                },
                {
                    "case_id": "LightOverlap",
                    "reference_segment_count": 25,
                    "hypothesis_segment_count": 26,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper_cleaned",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "compatibility bridge only; this export does not claim cpWER evaluation yet.",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bridge_status"], "ready_for_dry_run")
        self.assertEqual(rows[0]["raw_source_count"], "1")
        self.assertEqual(rows[0]["cleaned_fallback_count"], "1")
        self.assertIn("cleaned fallback", rows[0]["readiness_note"].lower())
        self.assertIn("dry run", rows[0]["next_action"].lower())

    def test_build_meeteval_readiness_lines_render_summary_card(self) -> None:
        lines = build_meeteval_readiness_lines(
            [
                {
                    "bridge_status": "ready_for_dry_run",
                    "case_count": "5",
                    "raw_source_count": "1",
                    "cleaned_fallback_count": "4",
                    "readiness_note": "The bridge is export-complete, but cleaned fallback is still common.",
                    "next_action": "Use one narrow dry run before claiming any cpWER-style evaluation.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Readiness", rendered)
        self.assertIn("ready_for_dry_run", rendered)
        self.assertIn("cleaned fallback is still common", rendered)

    def test_build_meeteval_dry_run_handoff_rows_turn_readiness_into_next_step(self) -> None:
        rows = build_meeteval_dry_run_handoff_rows(
            [
                {
                    "bridge_status": "ready_for_dry_run",
                    "case_count": "5",
                    "raw_source_count": "1",
                    "cleaned_fallback_count": "4",
                    "readiness_note": "The bridge is export-complete, but cleaned fallback is still common.",
                    "next_action": "Use one narrow dry run before claiming any cpWER-style evaluation.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bridge_status"], "ready_for_dry_run")
        self.assertEqual(rows[0]["source_mix"], "cleaned_fallback_dominant")
        self.assertEqual(rows[0]["recommended_slice"], "single_verified_case")
        self.assertIn("diagnostic", rows[0]["dry_run_goal"].lower())
        self.assertIn("cleaned fallback", rows[0]["primary_blocker"].lower())
        self.assertIn("meeteval_dry_run", rows[0]["expected_evidence"])
        self.assertIn("not been run yet", rows[0]["handoff_note"].lower())

    def test_build_meeteval_dry_run_handoff_lines_render_packet(self) -> None:
        lines = build_meeteval_dry_run_handoff_lines(
            [
                {
                    "bridge_status": "ready_for_dry_run",
                    "source_mix": "cleaned_fallback_dominant",
                    "recommended_slice": "single_verified_case",
                    "dry_run_goal": "Run one narrow diagnostic pass to validate the export path before any broader claim.",
                    "primary_blocker": "Cleaned fallback still dominates the current hypothesis mix.",
                    "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                    "handoff_note": "MeetEval / cpWER has not been run yet; this card only frames the first dry run.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Handoff", rendered)
        self.assertIn("cleaned_fallback_dominant", rendered)
        self.assertIn("single_verified_case", rendered)
        self.assertIn("meeteval_dry_run_receipt.json", rendered)

    def test_build_meeteval_dry_run_receipt_rows_create_template_evidence_target(self) -> None:
        rows = build_meeteval_dry_run_receipt_rows(
            [
                {
                    "bridge_status": "ready_for_dry_run",
                    "source_mix": "cleaned_fallback_dominant",
                    "recommended_slice": "single_verified_case",
                    "dry_run_goal": "Run one narrow diagnostic pass to validate the export path before any broader MeetEval or cpWER claim.",
                    "primary_blocker": "Cleaned fallback still dominates the current hypothesis mix, so the first dry run should stay diagnostic.",
                    "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                    "handoff_note": "MeetEval / cpWER has not been run yet; this card only frames the first dry run.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["run_scope"], "single_verified_case")
        self.assertIn("meeteval_reference_segments.jsonl", rows[0]["expected_inputs"])
        self.assertIn("diagnostic", rows[0]["expected_outputs"].lower())
        self.assertIn("not been executed", rows[0]["writeback_note"].lower())

    def test_build_meeteval_dry_run_receipt_lines_render_template(self) -> None:
        lines = build_meeteval_dry_run_receipt_lines(
            [
                {
                    "execution_status": "template_only",
                    "run_scope": "single_verified_case",
                    "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
                    "expected_outputs": "Diagnostic export-path confirmation and a narrow run note.",
                    "writeback_note": "MeetEval / cpWER has not been executed yet; fill this receipt only after the first dry run.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Receipt", rendered)
        self.assertIn("template_only", rendered)
        self.assertIn("single_verified_case", rendered)
        self.assertIn("not been executed yet", rendered)

    def test_build_meeteval_dry_run_bridge_checklist_rows_link_handoff_to_receipt(self) -> None:
        handoff_rows = [
            {
                "bridge_status": "ready_for_dry_run",
                "source_mix": "cleaned_fallback_dominant",
                "recommended_slice": "single_verified_case",
                "dry_run_goal": "Run one narrow diagnostic pass to validate the export path before any broader MeetEval or cpWER claim.",
                "primary_blocker": "Cleaned fallback still dominates the current hypothesis mix, so the first dry run should stay diagnostic.",
                "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                "handoff_note": "MeetEval / cpWER has not been run yet; this card only frames the first dry run.",
            }
        ]
        receipt_rows = [
            {
                "execution_status": "template_only",
                "run_scope": "single_verified_case",
                "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
                "expected_outputs": "Diagnostic export-path confirmation and a narrow run note.",
                "writeback_note": "MeetEval / cpWER has not been executed yet; fill this receipt only after the first dry run.",
            }
        ]

        rows = build_meeteval_dry_run_bridge_checklist_rows(handoff_rows, receipt_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checklist_order"], "1")
        self.assertEqual(rows[0]["bridge_status"], "ready_for_dry_run")
        self.assertEqual(rows[0]["prerequisite_artifact"], "results/figures/meeteval_dry_run_handoff.md")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/meeteval_dry_run_receipt.md")
        self.assertIn("dry run", rows[0]["checklist_goal"].lower())

    def test_build_meeteval_dry_run_bridge_checklist_lines_render_bridge(self) -> None:
        lines = build_meeteval_dry_run_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "bridge_status": "ready_for_dry_run",
                    "prerequisite_artifact": "results/figures/meeteval_dry_run_handoff.md",
                    "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
                    "checklist_goal": "Verify the first MeetEval dry run bridge before any writeback is advanced.",
                    "bridge_note": "Open the handoff packet first, then write back through the receipt target for single_verified_case.",
                    "next_gate": "Confirm this bridge before opening the receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Bridge Checklist", rendered)
        self.assertIn("ready_for_dry_run", rendered)
        self.assertIn("meeteval_dry_run_handoff.md", rendered)
        self.assertIn("meeteval_dry_run_receipt.md", rendered)

    def test_build_meeteval_dry_run_checklist_rows_rank_verified_cases(self) -> None:
        rows = build_meeteval_dry_run_checklist_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "hypothesis_source": "separated_whisper",
                },
                {
                    "case_id": "LightOverlap",
                    "hypothesis_source": "separated_whisper_cleaned",
                },
            ]
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["dry_run_priority"], "preferred")
        self.assertEqual(rows[1]["dry_run_priority"], "secondary")
        self.assertIn("end-to-end", rows[0]["operator_step"])
        self.assertIn("dry-run", rows[1]["validation_note"].lower())

    def test_build_meeteval_dry_run_receipt_checklist_rows_link_receipt_to_checklist(self) -> None:
        rows = build_meeteval_dry_run_receipt_checklist_rows(
            [
                {
                    "execution_status": "template_only",
                    "run_scope": "single_verified_case",
                    "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
                    "expected_outputs": "Diagnostic export-path confirmation and a narrow run note.",
                    "writeback_note": "MeetEval / cpWER has not been executed yet; fill this receipt only after the first dry run.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dry_run_scope"], "single_verified_case")
        self.assertEqual(rows[0]["receipt_state"], "template_only")
        self.assertEqual(rows[0]["receipt_target"], "results/figures/meeteval_dry_run_receipt.md")
        self.assertIn("cpwer", rows[0]["checklist_goal"].lower())

    def test_build_meeteval_dry_run_receipt_checklist_lines_render_checklist(self) -> None:
        lines = build_meeteval_dry_run_receipt_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "dry_run_scope": "single_verified_case",
                    "receipt_state": "template_only",
                    "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
                    "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
                    "checklist_goal": "Verify the dry-run receipt path for single_verified_case before any cpWER claim is advanced.",
                    "preflight_step": "Open the dry-run checklist and confirm the preferred case export before filling the receipt.",
                    "next_gate": "Fill the receipt before promoting any MeetEval evaluation claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Receipt Checklist", rendered)
        self.assertIn("single_verified_case", rendered)
        self.assertIn("meeteval_dry_run_receipt.md", rendered)

    def test_build_meeteval_dry_run_receipt_board_rows_condense_receipt_path(self) -> None:
        receipt_rows = [
            {
                "execution_status": "diagnostic_complete",
                "run_scope": "single_verified_case",
            }
        ]
        checklist_rows = [
            {
                "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
                "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
            }
        ]

        rows = build_meeteval_dry_run_receipt_board_rows(receipt_rows, checklist_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["receipt_state"], "diagnostic_complete")
        self.assertIn("cpwer", rows[0]["board_note"].lower())

    def test_build_meeteval_dry_run_receipt_board_lines_render_board(self) -> None:
        lines = build_meeteval_dry_run_receipt_board_lines(
            [
                {
                    "board_order": "1",
                    "dry_run_scope": "single_verified_case",
                    "receipt_state": "diagnostic_complete",
                    "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
                    "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
                    "board_note": "Keep the dry-run receipt path visible for single_verified_case while cpWER evaluation remains pending.",
                    "next_gate": "Open the receipt checklist before advancing any MeetEval evaluation claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Receipt Board", rendered)
        self.assertIn("diagnostic_complete", rendered)

    def test_build_meeteval_dry_run_receipt_map_rows_merge_layers(self) -> None:
        receipt_rows = [{"execution_status": "diagnostic_complete", "run_scope": "single_verified_case"}]
        checklist_rows = [{"receipt_target": "results/figures/meeteval_dry_run_receipt.md"}]
        board_rows = [
            {
                "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
                "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
            }
        ]

        rows = build_meeteval_dry_run_receipt_map_rows(receipt_rows, checklist_rows, board_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["receipt_state"], "diagnostic_complete")
        self.assertIn("receipt, checklist, and board", rows[0]["map_note"].lower())

    def test_build_meeteval_dry_run_receipt_map_lines_render_map(self) -> None:
        lines = build_meeteval_dry_run_receipt_map_lines(
            [
                {
                    "map_order": "1",
                    "dry_run_scope": "single_verified_case",
                    "receipt_state": "diagnostic_complete",
                    "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
                    "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
                    "map_note": "Keep the dry-run receipt path visible across the receipt, checklist, and board views for single_verified_case.",
                    "next_gate": "Open the receipt board and checklist before advancing any MeetEval evaluation claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Receipt Map", rendered)
        self.assertIn("single_verified_case", rendered)

    def test_build_meeteval_dry_run_checklist_lines_render_queue(self) -> None:
        lines = build_meeteval_dry_run_checklist_lines(
            [
                {
                    "case_id": "NoOverlap",
                    "hypothesis_source": "separated_whisper",
                    "dry_run_priority": "preferred",
                    "operator_step": "Validate one exported case end-to-end before any cpWER-style claim.",
                    "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                    "validation_note": "Raw separated source is available, so this is the cleanest first dry-run candidate.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Checklist", rendered)
        self.assertIn("preferred", rendered)
        self.assertIn("meeteval_dry_run_receipt.json", rendered)

    def test_load_reference_payload_returns_segment_list(self) -> None:
        payload = load_reference_payload("NoOverlap")
        self.assertIn("segments", payload)
        self.assertGreater(len(payload["segments"]), 0)

    def test_load_hypothesis_payload_prefers_raw_separated_transcript(self) -> None:
        payload = load_hypothesis_payload("NoOverlap")
        self.assertIn("segments", payload)
        self.assertEqual(payload.get("hypothesis_source"), "separated_whisper")
        self.assertGreater(len(payload["segments"]), 0)


if __name__ == "__main__":
    unittest.main()
