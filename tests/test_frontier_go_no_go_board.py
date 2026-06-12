from __future__ import annotations

import unittest

from src.frontier_go_no_go_board import build_summary_row, classify_go_no_go_state


class FrontierGoNoGoBoardTest(unittest.TestCase):
    def test_classify_go_no_go_state_marks_receipt_ready_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("receipt_ready_to_fill"), "go")

    def test_classify_go_no_go_state_marks_blocked_as_no_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("blocked_by_license_confirmation"), "no_go")

    def test_classify_go_no_go_state_marks_narrow_audio_eval_ready_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("ready_for_narrow_audio_eval"), "go")

    def test_classify_go_no_go_state_marks_presentation_polish_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("presentation_polish_complete"), "go")

    def test_classify_go_no_go_state_marks_character_level_receipt_fill_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("character_level_receipt_fill_complete"), "go")

    def test_classify_go_no_go_state_marks_wave6_coordination_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave6_coordination_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave7_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave7_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave8_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave8_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave9_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave9_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave10_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave10_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave11_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave11_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave12_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave12_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave13_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave13_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave14_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave14_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave15_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave15_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave16_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave16_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave17_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave17_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave18_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave18_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave19_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave19_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave20_exploration_baseline_closure_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave20_exploration_baseline_closure_complete"), "go")

    def test_classify_go_no_go_state_marks_wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_external_validation_narrow_slice_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("external_validation_narrow_slice_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave15_external_validation_narrow_slice_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave15_external_validation_narrow_slice_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave19_external_validation_narrow_slice_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave19_external_validation_narrow_slice_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_cascade_benchmark_phase3_gate_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_phase3_gate_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_cascade_benchmark_phase4_gate_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_phase4_gate_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_cascade_benchmark_phase5_gate_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_phase5_gate_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_llm_critic_narrow_dry_run_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("llm_critic_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave15_llm_critic_narrow_dry_run_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave15_llm_critic_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave18_llm_critic_narrow_dry_run_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave18_llm_critic_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_speaker_profile_case_scope_coordination_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("speaker_profile_case_scope_coordination_complete"), "go")

    def test_classify_go_no_go_state_marks_lightoverlap_diagnostic_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("speaker_profile_lightoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave16_speaker_profile_lightoverlap_diagnostic_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave16_speaker_profile_lightoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave17_speaker_profile_midoverlap_diagnostic_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave17_speaker_profile_midoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_wave17_meeteval_cpwer_narrow_dry_run_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("wave17_meeteval_cpwer_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_midoverlap_diagnostic_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("speaker_profile_midoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_heavyoverlap_diagnostic_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("speaker_profile_heavyoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_oppositeoverlap_diagnostic_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("speaker_profile_oppositeoverlap_diagnostic_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_evidence_receipt_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_evidence_receipt_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_phase1_gate_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_phase1_gate_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_meeteval_narrow_dry_run_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("meeteval_cpwer_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_meeteval_official_narrow_dry_run_coordination_complete_as_go(
        self,
    ) -> None:
        self.assertEqual(
            classify_go_no_go_state("meeteval_official_narrow_dry_run_coordination_complete"),
            "go",
        )

    def test_classify_go_no_go_state_marks_phase2_gate_coordination_complete_as_go(self) -> None:
        self.assertEqual(
            classify_go_no_go_state("cascade_benchmark_phase2_gate_coordination_complete"),
            "go",
        )

    def test_build_summary_row_uses_queue_priority(self) -> None:
        rows = [
            {"frontier_name": "demo_excellence", "go_no_go_state": "go"},
            {"frontier_name": "external_validation", "go_no_go_state": "no_go"},
            {"frontier_name": "meeteval_compatibility", "go_no_go_state": "go"},
            {"frontier_name": "speaker_profile", "go_no_go_state": "go"},
        ]

        row = build_summary_row(rows)

        self.assertEqual(row["highest_priority_ready_frontier"], "meeteval_compatibility")
        self.assertEqual(row["highest_priority_blocked_frontier"], "external_validation")


if __name__ == "__main__":
    unittest.main()
