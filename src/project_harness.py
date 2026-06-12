from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


CORE_FILES = [
    "README.md",
    "REPORT.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/ambitious_research_agenda.md",
    "docs/agent_challenge_board.md",
    "docs/experiment_proposal_template.md",
    "docs/project_state.md",
    "docs/technical_implementation_plan_v2.md",
    "docs/roadmap.md",
    "docs/maintenance_harness.md",
    "docs/repo_evolver.md",
    "docs/markdown_audit.md",
    "docs/contribution.md",
    "docs/experiment_notes.md",
    "docs/video_script.md",
    "docs/contributions/README.md",
    "docs/contributions/WUFANGZHOU.md",
    "docs/contributions/TEAM_CONTRIBUTION_TEMPLATE.md",
    "docs/handoff/WUFANGZHOU_HANDOFF.md",
    "docs/backup_plan.md",
    "docs/skills/README.md",
    "docs/skills/skill_01_separation_phase_diagram.md",
    "docs/skills/skill_02_compute_aware_cascade.md",
    "docs/skills/skill_03_speaker_profile_voiceprint.md",
    "docs/skills/skill_04_meeteval_compatibility.md",
    "docs/skills/skill_05_agentic_llm_critic.md",
    "docs/skills/skill_06_github_demo_excellence.md",
    "references/reference_transcripts.json",
    "results/tables/cer_results.csv",
    "results/tables/routing_performance_v2.csv",
    "results/tables/error_type_summary.csv",
    "results/tables/speaker_cer_results.csv",
    "results/tables/cpcer_lite_results.csv",
    "results/tables/risk_aware_performance.csv",
]

GOLD_CASES = [
    "NoOverlap",
    "LightOverlap",
    "MidOverlap",
    "HeavyOverlap",
    "OppositeOverlap",
]

FRONTIER_SKILLS = [
    {
        "frontier_id": "speaker_profile",
        "evidence_path": "docs/skills/skill_03_speaker_profile_voiceprint.md",
        "expected_output": "speaker profile triage card",
        "next_step": "Use the triage card to justify a stronger profile method while keeping the signal scoped to risk detection.",
    },
    {
        "frontier_id": "meeteval_compatibility",
        "evidence_path": "docs/skills/skill_04_meeteval_compatibility.md",
        "expected_output": "MeetEval readiness card",
        "next_step": "Use the readiness card to stage one narrow dry run before claiming any benchmark bridge.",
    },
    {
        "frontier_id": "llm_critic",
        "evidence_path": "docs/skills/skill_05_agentic_llm_critic.md",
        "expected_output": "qualitative critic queue",
        "next_step": "Use the review queue to decide which critic-style review queue item should be read first.",
    },
    {
        "frontier_id": "external_validation",
        "evidence_path": "docs/ambitious_research_agenda.md",
        "expected_output": "external sanity-check prioritization card",
        "next_step": "Use the prioritization card to map one tiny sanity-check slice without claiming a completed benchmark.",
    },
    {
        "frontier_id": "demo_excellence",
        "evidence_path": "docs/skills/skill_06_github_demo_excellence.md",
        "expected_output": "demo-facing storyboard or walkthrough",
        "next_step": "Use the demo walkthrough to shape a short demo walk before any heavier app build.",
    },
]

WAVE_FRONTIER_MODULES = [
    {
        "frontier_id": "wave1_separation_phase_diagram",
        "module_path": "src/separation_phase_diagram.py",
        "expected_output": "results/figures/separation_phase_diagram.md",
        "next_step": "Run python -m src.separation_phase_diagram to refresh experimental/frontier phase outputs.",
    },
    {
        "frontier_id": "wave1_router_boundary_alignment",
        "module_path": "src/router_boundary_alignment.py",
        "expected_output": "results/figures/router_boundary_alignment.md",
        "next_step": "Run python -m src.router_boundary_alignment to audit router v2 against gold phase boundaries.",
    },
    {
        "frontier_id": "wave1_error_type_boundary_report",
        "module_path": "src/error_type_boundary_report.py",
        "expected_output": "results/figures/error_type_boundary_report.md",
        "next_step": "Run python -m src.error_type_boundary_report to explain separation harm via error types.",
    },
    {
        "frontier_id": "wave1_speaker_profile_spectral_baseline",
        "module_path": "src/speaker_profile_spectral_embedding_baseline.py",
        "expected_output": "results/figures/speaker_profile_spectral_embedding_baseline.md",
        "next_step": "Run python -m src.speaker_profile_spectral_embedding_baseline for the NoOverlap narrow baseline.",
    },
    {
        "frontier_id": "wave1_frontier_boundary_consolidated_report",
        "module_path": "src/frontier_boundary_consolidated_report.py",
        "expected_output": "results/figures/frontier_boundary_consolidated_report.md",
        "next_step": "Run python -m src.frontier_boundary_consolidated_report to merge Wave1 boundary findings.",
    },
    {
        "frontier_id": "wave2_meeteval_gold_cer_cpwer_reconciliation",
        "module_path": "src/meeteval_gold_cer_cpwer_reconciliation.py",
        "expected_output": "results/figures/meeteval_gold_cer_cpwer_reconciliation.md",
        "next_step": "Run python -m src.meeteval_gold_cer_cpwer_reconciliation to compare gold CER and cpWER.",
    },
    {
        "frontier_id": "wave2_synthetic_router_boundary_alignment",
        "module_path": "src/synthetic_router_boundary_alignment.py",
        "expected_output": "results/figures/synthetic_router_boundary_alignment.md",
        "next_step": "Run python -m src.synthetic_router_boundary_alignment for held-out synthetic router audit.",
    },
    {
        "frontier_id": "wave2_risk_aware_boundary_audit",
        "module_path": "src/risk_aware_boundary_audit.py",
        "expected_output": "results/figures/risk_aware_boundary_audit.md",
        "next_step": "Run python -m src.risk_aware_boundary_audit to audit the risk-aware selector.",
    },
    {
        "frontier_id": "wave2_cascade_boundary_bridge",
        "module_path": "src/cascade_boundary_bridge.py",
        "expected_output": "results/figures/cascade_boundary_bridge.md",
        "next_step": "Run python -m src.cascade_boundary_bridge to bridge cascade strategies to phase boundaries.",
    },
    {
        "frontier_id": "wave2_speaker_profile_multisignal_gold_sweep",
        "module_path": "src/speaker_profile_multisignal_gold_sweep.py",
        "expected_output": "results/figures/speaker_profile_multisignal_gold_sweep.md",
        "next_step": "Run python -m src.speaker_profile_multisignal_gold_sweep for all-gold multisignal sweep.",
    },
    {
        "frontier_id": "wave2_llm_critic_qualitative_brief_light_mid",
        "module_path": "src/llm_critic_qualitative_brief_light_mid.py",
        "expected_output": "results/figures/llm_critic_qualitative_brief_light_mid.md",
        "next_step": "Run python -m src.llm_critic_qualitative_brief_light_mid for qualitative/demo Light/Mid brief.",
    },
    {
        "frontier_id": "wave3_external_validation_license_confirmation",
        "module_path": "src/external_validation_license_confirmation.py",
        "expected_output": "results/figures/external_validation_license_confirmation.md",
        "next_step": "Run python -m src.external_validation_license_confirmation to record AISHELL-4 CC BY-SA research confirmation.",
    },
    {
        "frontier_id": "wave3_external_validation_mini_sanity_check",
        "module_path": "src/external_validation_mini_sanity_check.py",
        "expected_output": "results/figures/external_validation_mini_sanity_check.md",
        "next_step": "Run python -m src.external_validation_mini_sanity_check after license confirmation.",
    },
    {
        "frontier_id": "wave3_external_validation_audio_excerpt_staging_plan",
        "module_path": "src/external_validation_audio_excerpt_staging_plan.py",
        "expected_output": "results/figures/external_validation_audio_excerpt_staging_plan.md",
        "next_step": "Run python -m src.external_validation_audio_excerpt_staging_plan before local AISHELL-4 download.",
    },
    {
        "frontier_id": "wave3_external_validation_aishell4_excerpt_fetch",
        "module_path": "src/external_validation_aishell4_excerpt_fetch.py",
        "expected_output": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001.wav",
        "next_step": "Run python -m src.external_validation_aishell4_excerpt_fetch after license confirmation.",
    },
    {
        "frontier_id": "wave3_external_validation_staging_execution_receipt_fill",
        "module_path": "src/external_validation_staging_execution_receipt_fill.py",
        "expected_output": "results/tables/external_validation_staging_execution_receipt_fill.json",
        "next_step": "Run python -m src.external_validation_staging_execution_receipt_fill after excerpt fetch.",
    },
    {
        "frontier_id": "wave3_external_validation_narrow_audio_eval",
        "module_path": "src/external_validation_narrow_audio_eval.py",
        "expected_output": "results/tables/external_validation_narrow_audio_eval.json",
        "next_step": "Run python -m src.external_validation_narrow_audio_eval after execution receipt fill.",
    },
    {
        "frontier_id": "wave3_external_validation_narrow_audio_eval_receipt",
        "module_path": "src/external_validation_narrow_audio_eval_receipt.py",
        "expected_output": "results/tables/external_validation_narrow_audio_eval_receipt.json",
        "next_step": "Run python -m src.external_validation_narrow_audio_eval_receipt after narrow ASR eval.",
    },
    {
        "frontier_id": "wave4_speaker_profile_embedding_trial_execution_receipt_fill",
        "module_path": "src/speaker_profile_embedding_trial_execution_receipt_fill.py",
        "expected_output": "results/tables/speaker_profile_embedding_trial_execution_receipt_fill.json",
        "next_step": "Run python -m src.speaker_profile_embedding_trial_execution_receipt_fill after receipt readiness.",
    },
    {
        "frontier_id": "wave4_llm_critic_qualitative_writeback",
        "module_path": "src/llm_critic_qualitative_writeback.py",
        "expected_output": "results/tables/llm_critic_qualitative_writeback.json",
        "next_step": "Run python -m src.llm_critic_qualitative_writeback when qualitative_writeback_ready.",
    },
    {
        "frontier_id": "wave4_demo_presentation_writeback",
        "module_path": "src/demo_presentation_writeback.py",
        "expected_output": "results/tables/demo_presentation_writeback.json",
        "next_step": "Run python -m src.demo_presentation_writeback when presentation_writeback_ready.",
    },
    {
        "frontier_id": "wave5_meeteval_character_level_execution_receipt_fill",
        "module_path": "src/meeteval_cpwer_character_level_execution_receipt_fill.py",
        "expected_output": "results/tables/meeteval_cpwer_character_level_execution_receipt_fill.json",
        "next_step": "Run python -m src.meeteval_cpwer_character_level_execution_receipt_fill after character-level cpWER execution.",
    },
    {
        "frontier_id": "wave5_cascade_frontier_coordination_writeback",
        "module_path": "src/cascade_frontier_coordination_writeback.py",
        "expected_output": "results/tables/cascade_frontier_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_frontier_coordination_writeback after MeetEval character-level receipt fill.",
    },
    {
        "frontier_id": "wave5_separation_phase_coordination_writeback",
        "module_path": "src/separation_phase_coordination_writeback.py",
        "expected_output": "results/tables/separation_phase_coordination_writeback.json",
        "next_step": "Run python -m src.separation_phase_coordination_writeback after cascade coordination writeback.",
    },
    {
        "frontier_id": "wave5_demo_presentation_writeback",
        "module_path": "src/demo_wave5_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave5_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave5_presentation_writeback after phase coordination writeback.",
    },
    {
        "frontier_id": "wave6_frontier_coordination_closure_writeback",
        "module_path": "src/wave6_frontier_coordination_closure_writeback.py",
        "expected_output": "results/tables/wave6_frontier_coordination_closure_writeback.json",
        "next_step": "Run python -m src.wave6_frontier_coordination_closure_writeback after Wave5 coordination chain.",
    },
    {
        "frontier_id": "wave6_cascade_benchmark_readiness_coordination_writeback",
        "module_path": "src/cascade_benchmark_readiness_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_readiness_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_readiness_coordination_writeback after Wave6 closure.",
    },
    {
        "frontier_id": "wave6_demo_presentation_writeback",
        "module_path": "src/demo_wave6_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave6_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave6_presentation_writeback after benchmark coordination writeback.",
    },
    {
        "frontier_id": "wave7_exploration_baseline_closure_writeback",
        "module_path": "src/wave7_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave7_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave7_exploration_baseline_closure_writeback after Wave6 chain.",
    },
    {
        "frontier_id": "wave7_demo_presentation_writeback",
        "module_path": "src/demo_wave7_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave7_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave7_presentation_writeback after Wave7 closure writeback.",
    },
    {
        "frontier_id": "wave7_speaker_profile_case_scope_coordination_writeback",
        "module_path": "src/speaker_profile_case_scope_coordination_writeback.py",
        "expected_output": "results/tables/speaker_profile_case_scope_coordination_writeback.json",
        "next_step": "Run python -m src.speaker_profile_case_scope_coordination_writeback after Wave7 closure.",
    },
    {
        "frontier_id": "wave7_cascade_benchmark_manifest_coordination_writeback",
        "module_path": "src/cascade_benchmark_manifest_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_manifest_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_manifest_coordination_writeback after speaker profile case-scope.",
    },
    {
        "frontier_id": "wave8_exploration_baseline_closure_writeback",
        "module_path": "src/wave8_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave8_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave8_exploration_baseline_closure_writeback after Wave7 chain.",
    },
    {
        "frontier_id": "wave8_demo_presentation_writeback",
        "module_path": "src/demo_wave8_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave8_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave8_presentation_writeback after Wave8 closure writeback.",
    },
    {
        "frontier_id": "wave8_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.speaker_profile_lightoverlap_diagnostic_coordination_writeback after Wave8 closure.",
    },
    {
        "frontier_id": "wave8_cascade_benchmark_evidence_receipt_coordination_writeback",
        "module_path": "src/cascade_benchmark_evidence_receipt_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_evidence_receipt_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_evidence_receipt_coordination_writeback after LightOverlap coordination.",
    },
    {
        "frontier_id": "wave9_exploration_baseline_closure_writeback",
        "module_path": "src/wave9_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave9_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave9_exploration_baseline_closure_writeback after Wave8 chain.",
    },
    {
        "frontier_id": "wave9_demo_presentation_writeback",
        "module_path": "src/demo_wave9_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave9_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave9_presentation_writeback after Wave9 closure writeback.",
    },
    {
        "frontier_id": "wave9_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.speaker_profile_midoverlap_diagnostic_coordination_writeback after LightOverlap coordination.",
    },
    {
        "frontier_id": "wave9_cascade_benchmark_phase1_gate_coordination_writeback",
        "module_path": "src/cascade_benchmark_phase1_gate_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_phase1_gate_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_phase1_gate_coordination_writeback after MidOverlap coordination.",
    },
    {
        "frontier_id": "wave10_exploration_baseline_closure_writeback",
        "module_path": "src/wave10_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave10_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave10_exploration_baseline_closure_writeback after Wave9 chain.",
    },
    {
        "frontier_id": "wave10_demo_presentation_writeback",
        "module_path": "src/demo_wave10_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave10_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave10_presentation_writeback after Wave10 closure writeback.",
    },
    {
        "frontier_id": "wave10_meeteval_cpwer_narrow_dry_run_coordination_writeback",
        "module_path": "src/meeteval_cpwer_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/meeteval_cpwer_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.meeteval_cpwer_narrow_dry_run_coordination_writeback after demo wave10.",
    },
    {
        "frontier_id": "wave10_cascade_benchmark_phase2_gate_coordination_writeback",
        "module_path": "src/cascade_benchmark_phase2_gate_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_phase2_gate_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_phase2_gate_coordination_writeback after MeetEval coordination.",
    },
    {
        "frontier_id": "wave11_exploration_baseline_closure_writeback",
        "module_path": "src/wave11_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave11_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave11_exploration_baseline_closure_writeback after Wave10 chain.",
    },
    {
        "frontier_id": "wave11_demo_presentation_writeback",
        "module_path": "src/demo_wave11_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave11_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave11_presentation_writeback after Wave11 closure writeback.",
    },
    {
        "frontier_id": "wave11_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.external_validation_narrow_slice_coordination_writeback after demo wave11.",
    },
    {
        "frontier_id": "wave11_cascade_benchmark_phase3_gate_coordination_writeback",
        "module_path": "src/cascade_benchmark_phase3_gate_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_phase3_gate_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_phase3_gate_coordination_writeback after external validation coordination.",
    },
    {
        "frontier_id": "wave12_exploration_baseline_closure_writeback",
        "module_path": "src/wave12_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave12_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave12_exploration_baseline_closure_writeback after Wave11 chain.",
    },
    {
        "frontier_id": "wave12_demo_presentation_writeback",
        "module_path": "src/demo_wave12_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave12_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave12_presentation_writeback after Wave12 closure writeback.",
    },
    {
        "frontier_id": "wave12_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave12.",
    },
    {
        "frontier_id": "wave12_llm_critic_narrow_dry_run_coordination_writeback",
        "module_path": "src/llm_critic_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/llm_critic_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.llm_critic_narrow_dry_run_coordination_writeback after HeavyOverlap coordination.",
    },
    {
        "frontier_id": "wave13_exploration_baseline_closure_writeback",
        "module_path": "src/wave13_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave13_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave13_exploration_baseline_closure_writeback after Wave12 chain.",
    },
    {
        "frontier_id": "wave13_demo_presentation_writeback",
        "module_path": "src/demo_wave13_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave13_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave13_presentation_writeback after Wave13 closure writeback.",
    },
    {
        "frontier_id": "wave13_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave13.",
    },
    {
        "frontier_id": "wave13_cascade_benchmark_phase4_gate_coordination_writeback",
        "module_path": "src/cascade_benchmark_phase4_gate_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_phase4_gate_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_phase4_gate_coordination_writeback after OppositeOverlap coordination.",
    },
    {
        "frontier_id": "wave14_exploration_baseline_closure_writeback",
        "module_path": "src/wave14_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave14_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave14_exploration_baseline_closure_writeback after Wave13 chain.",
    },
    {
        "frontier_id": "wave14_demo_presentation_writeback",
        "module_path": "src/demo_wave14_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave14_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave14_presentation_writeback after Wave14 closure writeback.",
    },
    {
        "frontier_id": "wave14_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.meeteval_official_narrow_dry_run_coordination_writeback after demo wave14.",
    },
    {
        "frontier_id": "wave14_cascade_benchmark_phase5_gate_coordination_writeback",
        "module_path": "src/cascade_benchmark_phase5_gate_coordination_writeback.py",
        "expected_output": "results/tables/cascade_benchmark_phase5_gate_coordination_writeback.json",
        "next_step": "Run python -m src.cascade_benchmark_phase5_gate_coordination_writeback after MeetEval official coordination.",
    },
    {
        "frontier_id": "wave15_exploration_baseline_closure_writeback",
        "module_path": "src/wave15_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave15_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave15_exploration_baseline_closure_writeback after Wave14 chain.",
    },
    {
        "frontier_id": "wave15_demo_presentation_writeback",
        "module_path": "src/demo_wave15_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave15_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave15_presentation_writeback after Wave15 closure writeback.",
    },
    {
        "frontier_id": "wave15_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave15_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave15_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave15_external_validation_narrow_slice_coordination_writeback after demo wave15.",
    },
    {
        "frontier_id": "wave15_llm_critic_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave15_llm_critic_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave15_llm_critic_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave15_llm_critic_narrow_dry_run_coordination_writeback after external validation coordination.",
    },
    {
        "frontier_id": "wave16_exploration_baseline_closure_writeback",
        "module_path": "src/wave16_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave16_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave16_exploration_baseline_closure_writeback after Wave15 chain.",
    },
    {
        "frontier_id": "wave16_demo_presentation_writeback",
        "module_path": "src/demo_wave16_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave16_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave16_presentation_writeback after Wave16 closure writeback.",
    },
    {
        "frontier_id": "wave16_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave16_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave16_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave16_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave16.",
    },
    {
        "frontier_id": "wave17_exploration_baseline_closure_writeback",
        "module_path": "src/wave17_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave17_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave17_exploration_baseline_closure_writeback after Wave16 chain.",
    },
    {
        "frontier_id": "wave17_demo_presentation_writeback",
        "module_path": "src/demo_wave17_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave17_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave17_presentation_writeback after Wave17 closure writeback.",
    },
    {
        "frontier_id": "wave17_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave17_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave17_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave17_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave17.",
    },
    {
        "frontier_id": "wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback after MidOverlap coordination.",
    },
    {
        "frontier_id": "wave18_exploration_baseline_closure_writeback",
        "module_path": "src/wave18_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave18_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave18_exploration_baseline_closure_writeback after Wave17 chain.",
    },
    {
        "frontier_id": "wave18_demo_presentation_writeback",
        "module_path": "src/demo_wave18_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave18_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave18_presentation_writeback after Wave18 closure writeback.",
    },
    {
        "frontier_id": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave18.",
    },
    {
        "frontier_id": "wave18_llm_critic_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave18_llm_critic_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave18_llm_critic_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave18_llm_critic_narrow_dry_run_coordination_writeback after HeavyOverlap coordination.",
    },
    {
        "frontier_id": "wave19_exploration_baseline_closure_writeback",
        "module_path": "src/wave19_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave19_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave19_exploration_baseline_closure_writeback after Wave18 chain.",
    },
    {
        "frontier_id": "wave19_demo_presentation_writeback",
        "module_path": "src/demo_wave19_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave19_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave19_presentation_writeback after Wave19 closure writeback.",
    },
    {
        "frontier_id": "wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave19.",
    },
    {
        "frontier_id": "wave19_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave19_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave19_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave19_external_validation_narrow_slice_coordination_writeback after OppositeOverlap coordination.",
    },
    {
        "frontier_id": "wave20_exploration_baseline_closure_writeback",
        "module_path": "src/wave20_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave20_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave20_exploration_baseline_closure_writeback after Wave19 chain.",
    },
    {
        "frontier_id": "wave20_demo_presentation_writeback",
        "module_path": "src/demo_wave20_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave20_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave20_presentation_writeback after Wave20 closure writeback.",
    },
    {
        "frontier_id": "wave20_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave20_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave20_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave20_meeteval_official_narrow_dry_run_coordination_writeback after demo wave20.",
    },
    {
        "frontier_id": "wave21_exploration_baseline_closure_writeback",
        "module_path": "src/wave21_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave21_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave21_exploration_baseline_closure_writeback after Wave20 chain.",
    },
    {
        "frontier_id": "wave21_demo_presentation_writeback",
        "module_path": "src/demo_wave21_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave21_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave21_presentation_writeback after Wave21 closure writeback.",
    },
    {
        "frontier_id": "wave21_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave21_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave21_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave21_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave21.",
    },
    {
        "frontier_id": "wave22_exploration_baseline_closure_writeback",
        "module_path": "src/wave22_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave22_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave22_exploration_baseline_closure_writeback after Wave21 chain.",
    },
    {
        "frontier_id": "wave22_demo_presentation_writeback",
        "module_path": "src/demo_wave22_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave22_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave22_presentation_writeback after Wave22 closure writeback.",
    },
    {
        "frontier_id": "wave22_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave22_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave22_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave22_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave22.",
    },
    {
        "frontier_id": "wave23_exploration_baseline_closure_writeback",
        "module_path": "src/wave23_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave23_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave23_exploration_baseline_closure_writeback after Wave22 chain.",
    },
    {
        "frontier_id": "wave23_demo_presentation_writeback",
        "module_path": "src/demo_wave23_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave23_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave23_presentation_writeback after Wave23 closure writeback.",
    },
    {
        "frontier_id": "wave23_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave23_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave23_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave23_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave23.",
    },
    {
        "frontier_id": "wave24_exploration_baseline_closure_writeback",
        "module_path": "src/wave24_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave24_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave24_exploration_baseline_closure_writeback after Wave23 chain.",
    },
    {
        "frontier_id": "wave24_demo_presentation_writeback",
        "module_path": "src/demo_wave24_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave24_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave24_presentation_writeback after Wave24 closure writeback.",
    },
    {
        "frontier_id": "wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave24.",
    },
    {
        "frontier_id": "wave25_exploration_baseline_closure_writeback",
        "module_path": "src/wave25_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave25_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave25_exploration_baseline_closure_writeback after Wave24 chain.",
    },
    {
        "frontier_id": "wave25_demo_presentation_writeback",
        "module_path": "src/demo_wave25_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave25_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave25_presentation_writeback after Wave25 closure writeback.",
    },
    {
        "frontier_id": "wave25_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave25_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave25_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave25_external_validation_narrow_slice_coordination_writeback after demo wave25.",
    },
    {
        "frontier_id": "wave26_exploration_baseline_closure_writeback",
        "module_path": "src/wave26_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave26_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave26_exploration_baseline_closure_writeback after Wave25 chain.",
    },
    {
        "frontier_id": "wave26_demo_presentation_writeback",
        "module_path": "src/demo_wave26_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave26_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave26_presentation_writeback after Wave26 closure writeback.",
    },
    {
        "frontier_id": "wave26_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave26_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave26_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave26_meeteval_official_narrow_dry_run_coordination_writeback after demo wave26.",
    },
    {
        "frontier_id": "wave27_exploration_baseline_closure_writeback",
        "module_path": "src/wave27_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave27_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave27_exploration_baseline_closure_writeback after Wave26 chain.",
    },
    {
        "frontier_id": "wave27_demo_presentation_writeback",
        "module_path": "src/demo_wave27_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave27_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave27_presentation_writeback after Wave27 closure writeback.",
    },
    {
        "frontier_id": "wave27_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave27_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave27_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave27_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave27.",
    },
    {
        "frontier_id": "wave28_exploration_baseline_closure_writeback",
        "module_path": "src/wave28_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave28_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave28_exploration_baseline_closure_writeback after Wave27 chain.",
    },
    {
        "frontier_id": "wave28_demo_presentation_writeback",
        "module_path": "src/demo_wave28_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave28_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave28_presentation_writeback after Wave28 closure writeback.",
    },
    {
        "frontier_id": "wave28_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave28_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave28_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave28_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave28.",
    },
    {
        "frontier_id": "wave29_exploration_baseline_closure_writeback",
        "module_path": "src/wave29_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave29_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave29_exploration_baseline_closure_writeback after Wave28 chain.",
    },
    {
        "frontier_id": "wave29_demo_presentation_writeback",
        "module_path": "src/demo_wave29_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave29_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave29_presentation_writeback after Wave29 closure writeback.",
    },
    {
        "frontier_id": "wave29_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave29_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave29_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave29_external_validation_narrow_slice_coordination_writeback after demo wave29.",
    },
    {
        "frontier_id": "wave30_exploration_baseline_closure_writeback",
        "module_path": "src/wave30_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave30_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave30_exploration_baseline_closure_writeback after Wave29 chain.",
    },
    {
        "frontier_id": "wave30_demo_presentation_writeback",
        "module_path": "src/demo_wave30_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave30_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave30_presentation_writeback after Wave30 closure writeback.",
    },
    {
        "frontier_id": "wave30_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave30_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave30_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave30_meeteval_official_narrow_dry_run_coordination_writeback after demo wave30.",
    },
    {
        "frontier_id": "wave31_exploration_baseline_closure_writeback",
        "module_path": "src/wave31_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave31_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave31_exploration_baseline_closure_writeback after Wave30 chain.",
    },
    {
        "frontier_id": "wave31_demo_presentation_writeback",
        "module_path": "src/demo_wave31_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave31_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave31_presentation_writeback after Wave31 closure writeback.",
    },
    {
        "frontier_id": "wave31_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave31_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave31_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave31_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave31.",
    },
    {
        "frontier_id": "wave32_exploration_baseline_closure_writeback",
        "module_path": "src/wave32_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave32_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave32_exploration_baseline_closure_writeback after Wave31 chain.",
    },
    {
        "frontier_id": "wave32_demo_presentation_writeback",
        "module_path": "src/demo_wave32_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave32_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave32_presentation_writeback after Wave32 closure writeback.",
    },
    {
        "frontier_id": "wave32_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave32_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave32_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave32_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave32.",
    },
    {
        "frontier_id": "wave33_exploration_baseline_closure_writeback",
        "module_path": "src/wave33_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave33_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave33_exploration_baseline_closure_writeback after Wave32 chain.",
    },
    {
        "frontier_id": "wave33_demo_presentation_writeback",
        "module_path": "src/demo_wave33_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave33_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave33_presentation_writeback after Wave33 closure writeback.",
    },
    {
        "frontier_id": "wave33_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave33_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave33_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave33_external_validation_narrow_slice_coordination_writeback after demo wave33.",
    },
    {
        "frontier_id": "wave34_exploration_baseline_closure_writeback",
        "module_path": "src/wave34_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave34_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave34_exploration_baseline_closure_writeback after Wave33 chain.",
    },
    {
        "frontier_id": "wave34_demo_presentation_writeback",
        "module_path": "src/demo_wave34_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave34_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave34_presentation_writeback after Wave34 closure writeback.",
    },
    {
        "frontier_id": "wave34_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave34_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave34_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave34_meeteval_official_narrow_dry_run_coordination_writeback after demo wave34.",
    },
    {
        "frontier_id": "wave35_exploration_baseline_closure_writeback",
        "module_path": "src/wave35_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave35_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave35_exploration_baseline_closure_writeback after Wave34 chain.",
    },
    {
        "frontier_id": "wave35_demo_presentation_writeback",
        "module_path": "src/demo_wave35_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave35_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave35_presentation_writeback after Wave35 closure writeback.",
    },
    {
        "frontier_id": "wave35_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave35_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave35_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave35_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave35.",
    },
    {
        "frontier_id": "wave36_exploration_baseline_closure_writeback",
        "module_path": "src/wave36_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave36_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave36_exploration_baseline_closure_writeback after Wave35 chain.",
    },
    {
        "frontier_id": "wave36_demo_presentation_writeback",
        "module_path": "src/demo_wave36_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave36_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave36_presentation_writeback after Wave36 closure writeback.",
    },
    {
        "frontier_id": "wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave36.",
    },
    {
        "frontier_id": "wave37_exploration_baseline_closure_writeback",
        "module_path": "src/wave37_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave37_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave37_exploration_baseline_closure_writeback after Wave36 chain.",
    },
    {
        "frontier_id": "wave37_demo_presentation_writeback",
        "module_path": "src/demo_wave37_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave37_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave37_presentation_writeback after Wave37 closure writeback.",
    },
    {
        "frontier_id": "wave37_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave37_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave37_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave37_external_validation_narrow_slice_coordination_writeback after demo wave37.",
    },
    {
        "frontier_id": "wave38_exploration_baseline_closure_writeback",
        "module_path": "src/wave38_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave38_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave38_exploration_baseline_closure_writeback after Wave37 chain.",
    },
    {
        "frontier_id": "wave38_demo_presentation_writeback",
        "module_path": "src/demo_wave38_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave38_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave38_presentation_writeback after Wave38 closure writeback.",
    },
    {
        "frontier_id": "wave38_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave38_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave38_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave38_meeteval_official_narrow_dry_run_coordination_writeback after demo wave38.",
    },
    {
        "frontier_id": "wave39_exploration_baseline_closure_writeback",
        "module_path": "src/wave39_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave39_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave39_exploration_baseline_closure_writeback after Wave38 chain.",
    },
    {
        "frontier_id": "wave39_demo_presentation_writeback",
        "module_path": "src/demo_wave39_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave39_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave39_presentation_writeback after Wave39 closure writeback.",
    },
    {
        "frontier_id": "wave39_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave39_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave39_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave39_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave39.",
    },
    {
        "frontier_id": "wave40_exploration_baseline_closure_writeback",
        "module_path": "src/wave40_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave40_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave40_exploration_baseline_closure_writeback after Wave39 chain.",
    },
    {
        "frontier_id": "wave40_demo_presentation_writeback",
        "module_path": "src/demo_wave40_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave40_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave40_presentation_writeback after Wave40 closure writeback.",
    },
    {
        "frontier_id": "wave40_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave40_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave40_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave40_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave40.",
    },
    {
        "frontier_id": "wave41_exploration_baseline_closure_writeback",
        "module_path": "src/wave41_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave41_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave41_exploration_baseline_closure_writeback after Wave40 chain.",
    },
    {
        "frontier_id": "wave41_demo_presentation_writeback",
        "module_path": "src/demo_wave41_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave41_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave41_presentation_writeback after Wave41 closure writeback.",
    },
    {
        "frontier_id": "wave41_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave41_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave41_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave41_external_validation_narrow_slice_coordination_writeback after demo wave41.",
    },
    {
        "frontier_id": "wave42_exploration_baseline_closure_writeback",
        "module_path": "src/wave42_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave42_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave42_exploration_baseline_closure_writeback after Wave41 chain.",
    },
    {
        "frontier_id": "wave42_demo_presentation_writeback",
        "module_path": "src/demo_wave42_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave42_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave42_presentation_writeback after Wave42 closure writeback.",
    },
    {
        "frontier_id": "wave42_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave42_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave42_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave42_meeteval_official_narrow_dry_run_coordination_writeback after demo wave42.",
    },
    {
        "frontier_id": "wave43_exploration_baseline_closure_writeback",
        "module_path": "src/wave43_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave43_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave43_exploration_baseline_closure_writeback after Wave42 chain.",
    },
    {
        "frontier_id": "wave43_demo_presentation_writeback",
        "module_path": "src/demo_wave43_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave43_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave43_presentation_writeback after Wave43 closure writeback.",
    },
    {
        "frontier_id": "wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave43.",
    },
    {
        "frontier_id": "wave44_exploration_baseline_closure_writeback",
        "module_path": "src/wave44_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave44_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave44_exploration_baseline_closure_writeback after Wave43 chain.",
    },
    {
        "frontier_id": "wave44_demo_presentation_writeback",
        "module_path": "src/demo_wave44_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave44_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave44_presentation_writeback after Wave44 closure writeback.",
    },
    {
        "frontier_id": "wave44_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave44_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave44_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave44_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave44.",
    },
    {
        "frontier_id": "wave45_exploration_baseline_closure_writeback",
        "module_path": "src/wave45_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave45_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave45_exploration_baseline_closure_writeback after Wave44 chain.",
    },
    {
        "frontier_id": "wave45_demo_presentation_writeback",
        "module_path": "src/demo_wave45_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave45_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave45_presentation_writeback after Wave45 closure writeback.",
    },
    {
        "frontier_id": "wave45_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave45_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave45_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave45_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave45.",
    },
    {
        "frontier_id": "wave46_exploration_baseline_closure_writeback",
        "module_path": "src/wave46_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave46_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave46_exploration_baseline_closure_writeback after Wave45 chain.",
    },
    {
        "frontier_id": "wave46_demo_presentation_writeback",
        "module_path": "src/demo_wave46_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave46_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave46_presentation_writeback after Wave46 closure writeback.",
    },
    {
        "frontier_id": "wave46_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave46_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave46_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave46_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave46.",
    },
    {
        "frontier_id": "wave47_exploration_baseline_closure_writeback",
        "module_path": "src/wave47_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave47_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave47_exploration_baseline_closure_writeback after Wave46 chain.",
    },
    {
        "frontier_id": "wave47_demo_presentation_writeback",
        "module_path": "src/demo_wave47_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave47_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave47_presentation_writeback after Wave47 closure writeback.",
    },
    {
        "frontier_id": "wave47_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave47_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave47_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave47_external_validation_narrow_slice_coordination_writeback after demo wave47.",
    },
    {
        "frontier_id": "wave48_exploration_baseline_closure_writeback",
        "module_path": "src/wave48_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave48_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave48_exploration_baseline_closure_writeback after Wave47 chain.",
    },
    {
        "frontier_id": "wave48_demo_presentation_writeback",
        "module_path": "src/demo_wave48_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave48_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave48_presentation_writeback after Wave48 closure writeback.",
    },
    {
        "frontier_id": "wave48_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave48_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave48_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave48_meeteval_official_narrow_dry_run_coordination_writeback after demo wave48.",
    },
    {
        "frontier_id": "wave49_exploration_baseline_closure_writeback",
        "module_path": "src/wave49_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave49_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave49_exploration_baseline_closure_writeback after Wave48 chain.",
    },
    {
        "frontier_id": "wave49_demo_presentation_writeback",
        "module_path": "src/demo_wave49_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave49_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave49_presentation_writeback after Wave49 closure writeback.",
    },
    {
        "frontier_id": "wave49_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave49_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave49_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave49_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave49.",
    },
    {
        "frontier_id": "wave50_exploration_baseline_closure_writeback",
        "module_path": "src/wave50_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave50_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave50_exploration_baseline_closure_writeback after Wave49 chain.",
    },
    {
        "frontier_id": "wave50_demo_presentation_writeback",
        "module_path": "src/demo_wave50_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave50_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave50_presentation_writeback after Wave50 closure writeback.",
    },
    {
        "frontier_id": "wave50_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave50_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave50_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave50_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave50.",
    },
    {
        "frontier_id": "wave51_exploration_baseline_closure_writeback",
        "module_path": "src/wave51_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave51_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave51_exploration_baseline_closure_writeback after Wave50 chain.",
    },
    {
        "frontier_id": "wave51_demo_presentation_writeback",
        "module_path": "src/demo_wave51_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave51_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave51_presentation_writeback after Wave51 closure writeback.",
    },
    {
        "frontier_id": "wave51_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave51_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave51_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave51_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave51.",
    },
    {
        "frontier_id": "wave52_exploration_baseline_closure_writeback",
        "module_path": "src/wave52_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave52_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave52_exploration_baseline_closure_writeback after Wave51 chain.",
    },
    {
        "frontier_id": "wave52_demo_presentation_writeback",
        "module_path": "src/demo_wave52_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave52_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave52_presentation_writeback after Wave52 closure writeback.",
    },
    {
        "frontier_id": "wave52_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave52_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave52_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave52_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave52.",
    },
    {
        "frontier_id": "wave53_exploration_baseline_closure_writeback",
        "module_path": "src/wave53_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave53_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave53_exploration_baseline_closure_writeback after Wave52 chain.",
    },
    {
        "frontier_id": "wave53_demo_presentation_writeback",
        "module_path": "src/demo_wave53_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave53_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave53_presentation_writeback after Wave53 closure writeback.",
    },
    {
        "frontier_id": "wave53_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave53_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave53_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave53_external_validation_narrow_slice_coordination_writeback after demo wave53.",
    },
    {
        "frontier_id": "wave54_exploration_baseline_closure_writeback",
        "module_path": "src/wave54_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave54_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave54_exploration_baseline_closure_writeback after Wave53 chain.",
    },
    {
        "frontier_id": "wave54_demo_presentation_writeback",
        "module_path": "src/demo_wave54_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave54_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave54_presentation_writeback after Wave54 closure writeback.",
    },
    {
        "frontier_id": "wave54_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave54_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave54_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave54_meeteval_official_narrow_dry_run_coordination_writeback after demo wave54.",
    },
    {
        "frontier_id": "wave55_exploration_baseline_closure_writeback",
        "module_path": "src/wave55_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave55_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave55_exploration_baseline_closure_writeback after Wave54 chain.",
    },
    {
        "frontier_id": "wave55_demo_presentation_writeback",
        "module_path": "src/demo_wave55_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave55_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave55_presentation_writeback after Wave55 closure writeback.",
    },
    {
        "frontier_id": "wave55_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave55_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave55_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave55_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave55.",
    },
    {
        "frontier_id": "wave56_exploration_baseline_closure_writeback",
        "module_path": "src/wave56_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave56_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave56_exploration_baseline_closure_writeback after Wave55 chain.",
    },
    {
        "frontier_id": "wave56_demo_presentation_writeback",
        "module_path": "src/demo_wave56_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave56_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave56_presentation_writeback after Wave56 closure writeback.",
    },
    {
        "frontier_id": "wave56_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave56_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave56_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave56_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave56.",
    },
    {
        "frontier_id": "wave57_exploration_baseline_closure_writeback",
        "module_path": "src/wave57_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave57_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave57_exploration_baseline_closure_writeback after Wave56 chain.",
    },
    {
        "frontier_id": "wave57_demo_presentation_writeback",
        "module_path": "src/demo_wave57_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave57_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave57_presentation_writeback after Wave57 closure writeback.",
    },
    {
        "frontier_id": "wave57_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave57_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave57_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave57_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave57.",
    },
    {
        "frontier_id": "wave58_exploration_baseline_closure_writeback",
        "module_path": "src/wave58_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave58_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave58_exploration_baseline_closure_writeback after Wave57 chain.",
    },
    {
        "frontier_id": "wave58_demo_presentation_writeback",
        "module_path": "src/demo_wave58_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave58_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave58_presentation_writeback after Wave58 closure writeback.",
    },
    {
        "frontier_id": "wave58_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave58_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave58_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave58_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave58.",
    },
    {
        "frontier_id": "wave59_exploration_baseline_closure_writeback",
        "module_path": "src/wave59_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave59_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave59_exploration_baseline_closure_writeback after Wave58 chain.",
    },
    {
        "frontier_id": "wave59_demo_presentation_writeback",
        "module_path": "src/demo_wave59_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave59_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave59_presentation_writeback after Wave59 closure writeback.",
    },
    {
        "frontier_id": "wave59_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave59_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave59_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave59_external_validation_narrow_slice_coordination_writeback after demo wave59.",
    },
    {
        "frontier_id": "wave60_exploration_baseline_closure_writeback",
        "module_path": "src/wave60_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave60_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave60_exploration_baseline_closure_writeback after Wave59 chain.",
    },
    {
        "frontier_id": "wave60_demo_presentation_writeback",
        "module_path": "src/demo_wave60_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave60_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave60_presentation_writeback after Wave60 closure writeback.",
    },
    {
        "frontier_id": "wave60_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave60_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave60_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave60_meeteval_official_narrow_dry_run_coordination_writeback after demo wave60.",
    },
    {
        "frontier_id": "wave61_exploration_baseline_closure_writeback",
        "module_path": "src/wave61_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave61_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave61_exploration_baseline_closure_writeback after Wave60 chain.",
    },
    {
        "frontier_id": "wave61_demo_presentation_writeback",
        "module_path": "src/demo_wave61_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave61_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave61_presentation_writeback after Wave61 closure writeback.",
    },
    {
        "frontier_id": "wave61_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave61_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave61_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave61_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave61.",
    },
    {
        "frontier_id": "wave62_exploration_baseline_closure_writeback",
        "module_path": "src/wave62_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave62_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave62_exploration_baseline_closure_writeback after Wave61 chain.",
    },
    {
        "frontier_id": "wave62_demo_presentation_writeback",
        "module_path": "src/demo_wave62_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave62_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave62_presentation_writeback after Wave62 closure writeback.",
    },
    {
        "frontier_id": "wave62_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave62_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave62_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave62_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave62.",
    },
    {
        "frontier_id": "wave63_exploration_baseline_closure_writeback",
        "module_path": "src/wave63_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave63_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave63_exploration_baseline_closure_writeback after Wave62 chain.",
    },
    {
        "frontier_id": "wave63_demo_presentation_writeback",
        "module_path": "src/demo_wave63_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave63_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave63_presentation_writeback after Wave63 closure writeback.",
    },
    {
        "frontier_id": "wave63_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave63_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave63_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave63_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave63.",
    },
    {
        "frontier_id": "wave64_exploration_baseline_closure_writeback",
        "module_path": "src/wave64_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave64_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave64_exploration_baseline_closure_writeback after Wave63 chain.",
    },
    {
        "frontier_id": "wave64_demo_presentation_writeback",
        "module_path": "src/demo_wave64_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave64_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave64_presentation_writeback after Wave64 closure writeback.",
    },
    {
        "frontier_id": "wave64_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave64_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave64_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave64_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave64.",
    },
    {
        "frontier_id": "wave65_exploration_baseline_closure_writeback",
        "module_path": "src/wave65_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave65_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave65_exploration_baseline_closure_writeback after Wave64 chain.",
    },
    {
        "frontier_id": "wave65_demo_presentation_writeback",
        "module_path": "src/demo_wave65_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave65_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave65_presentation_writeback after Wave65 closure writeback.",
    },
    {
        "frontier_id": "wave65_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave65_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave65_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave65_external_validation_narrow_slice_coordination_writeback after demo wave65.",
    },
    {
        "frontier_id": "wave66_exploration_baseline_closure_writeback",
        "module_path": "src/wave66_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave66_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave66_exploration_baseline_closure_writeback after Wave65 chain.",
    },
    {
        "frontier_id": "wave66_demo_presentation_writeback",
        "module_path": "src/demo_wave66_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave66_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave66_presentation_writeback after Wave66 closure writeback.",
    },
    {
        "frontier_id": "wave66_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave66_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave66_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave66_meeteval_official_narrow_dry_run_coordination_writeback after demo wave66.",
    },
    {
        "frontier_id": "wave67_exploration_baseline_closure_writeback",
        "module_path": "src/wave67_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave67_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave67_exploration_baseline_closure_writeback after Wave66 chain.",
    },
    {
        "frontier_id": "wave67_demo_presentation_writeback",
        "module_path": "src/demo_wave67_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave67_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave67_presentation_writeback after Wave67 closure writeback.",
    },
    {
        "frontier_id": "wave67_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave67_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave67_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave67_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave67.",
    },
    {
        "frontier_id": "wave68_exploration_baseline_closure_writeback",
        "module_path": "src/wave68_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave68_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave68_exploration_baseline_closure_writeback after Wave67 chain.",
    },
    {
        "frontier_id": "wave68_demo_presentation_writeback",
        "module_path": "src/demo_wave68_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave68_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave68_presentation_writeback after Wave68 closure writeback.",
    },
    {
        "frontier_id": "wave68_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave68_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave68_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave68_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave68.",
    },
    {
        "frontier_id": "wave69_exploration_baseline_closure_writeback",
        "module_path": "src/wave69_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave69_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave69_exploration_baseline_closure_writeback after Wave68 chain.",
    },
    {
        "frontier_id": "wave69_demo_presentation_writeback",
        "module_path": "src/demo_wave69_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave69_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave69_presentation_writeback after Wave69 closure writeback.",
    },
    {
        "frontier_id": "wave69_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave69_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave69_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave69_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave69.",
    },
    {
        "frontier_id": "wave70_exploration_baseline_closure_writeback",
        "module_path": "src/wave70_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave70_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave70_exploration_baseline_closure_writeback after Wave69 chain.",
    },
    {
        "frontier_id": "wave70_demo_presentation_writeback",
        "module_path": "src/demo_wave70_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave70_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave70_presentation_writeback after Wave70 closure writeback.",
    },
    {
        "frontier_id": "wave70_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave70_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave70_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave70_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave70.",
    },
    {
        "frontier_id": "wave71_exploration_baseline_closure_writeback",
        "module_path": "src/wave71_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave71_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave71_exploration_baseline_closure_writeback after Wave70 chain.",
    },
    {
        "frontier_id": "wave71_demo_presentation_writeback",
        "module_path": "src/demo_wave71_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave71_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave71_presentation_writeback after Wave71 closure writeback.",
    },
    {
        "frontier_id": "wave71_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave71_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave71_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave71_external_validation_narrow_slice_coordination_writeback after demo wave71.",
    },
    {
        "frontier_id": "wave72_exploration_baseline_closure_writeback",
        "module_path": "src/wave72_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave72_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave72_exploration_baseline_closure_writeback after Wave71 chain.",
    },
    {
        "frontier_id": "wave72_demo_presentation_writeback",
        "module_path": "src/demo_wave72_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave72_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave72_presentation_writeback after Wave72 closure writeback.",
    },
    {
        "frontier_id": "wave72_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave72_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave72_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave72_meeteval_official_narrow_dry_run_coordination_writeback after demo wave72.",
    },
    {
        "frontier_id": "wave73_exploration_baseline_closure_writeback",
        "module_path": "src/wave73_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave73_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave73_exploration_baseline_closure_writeback after Wave72 chain.",
    },
    {
        "frontier_id": "wave73_demo_presentation_writeback",
        "module_path": "src/demo_wave73_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave73_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave73_presentation_writeback after Wave73 closure writeback.",
    },
    {
        "frontier_id": "wave73_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave73_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave73_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave73_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave73.",
    },
    {
        "frontier_id": "wave74_exploration_baseline_closure_writeback",
        "module_path": "src/wave74_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave74_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave74_exploration_baseline_closure_writeback after Wave73 chain.",
    },
    {
        "frontier_id": "wave74_demo_presentation_writeback",
        "module_path": "src/demo_wave74_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave74_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave74_presentation_writeback after Wave74 closure writeback.",
    },
    {
        "frontier_id": "wave74_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave74_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave74_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave74_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave74.",
    },
    {
        "frontier_id": "wave75_exploration_baseline_closure_writeback",
        "module_path": "src/wave75_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave75_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave75_exploration_baseline_closure_writeback after Wave74 chain.",
    },
    {
        "frontier_id": "wave75_demo_presentation_writeback",
        "module_path": "src/demo_wave75_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave75_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave75_presentation_writeback after Wave75 closure writeback.",
    },
    {
        "frontier_id": "wave75_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave75_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave75_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave75_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave75.",
    },
    {
        "frontier_id": "wave76_exploration_baseline_closure_writeback",
        "module_path": "src/wave76_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave76_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave76_exploration_baseline_closure_writeback after Wave75 chain.",
    },
    {
        "frontier_id": "wave76_demo_presentation_writeback",
        "module_path": "src/demo_wave76_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave76_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave76_presentation_writeback after Wave76 closure writeback.",
    },
    {
        "frontier_id": "wave76_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave76_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave76_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave76_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave76.",
    },
    {
        "frontier_id": "wave77_exploration_baseline_closure_writeback",
        "module_path": "src/wave77_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave77_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave77_exploration_baseline_closure_writeback after Wave76 chain.",
    },
    {
        "frontier_id": "wave77_demo_presentation_writeback",
        "module_path": "src/demo_wave77_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave77_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave77_presentation_writeback after Wave77 closure writeback.",
    },
    {
        "frontier_id": "wave77_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave77_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave77_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave77_external_validation_narrow_slice_coordination_writeback after demo wave77.",
    },
    {
        "frontier_id": "wave78_exploration_baseline_closure_writeback",
        "module_path": "src/wave78_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave78_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave78_exploration_baseline_closure_writeback after Wave77 chain.",
    },
    {
        "frontier_id": "wave78_demo_presentation_writeback",
        "module_path": "src/demo_wave78_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave78_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave78_presentation_writeback after Wave78 closure writeback.",
    },
    {
        "frontier_id": "wave78_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave78_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave78_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave78_meeteval_official_narrow_dry_run_coordination_writeback after demo wave78.",
    },
    {
        "frontier_id": "wave79_exploration_baseline_closure_writeback",
        "module_path": "src/wave79_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave79_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave79_exploration_baseline_closure_writeback after Wave78 chain.",
    },
    {
        "frontier_id": "wave79_demo_presentation_writeback",
        "module_path": "src/demo_wave79_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave79_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave79_presentation_writeback after Wave79 closure writeback.",
    },
    {
        "frontier_id": "wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave79.",
    },
    {
        "frontier_id": "wave80_exploration_baseline_closure_writeback",
        "module_path": "src/wave80_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave80_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave80_exploration_baseline_closure_writeback after Wave79 chain.",
    },
    {
        "frontier_id": "wave80_demo_presentation_writeback",
        "module_path": "src/demo_wave80_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave80_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave80_presentation_writeback after Wave80 closure writeback.",
    },
    {
        "frontier_id": "wave80_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave80_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave80_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave80_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave80.",
    },
    {
        "frontier_id": "wave81_exploration_baseline_closure_writeback",
        "module_path": "src/wave81_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave81_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave81_exploration_baseline_closure_writeback after Wave80 chain.",
    },
    {
        "frontier_id": "wave81_demo_presentation_writeback",
        "module_path": "src/demo_wave81_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave81_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave81_presentation_writeback after Wave81 closure writeback.",
    },
    {
        "frontier_id": "wave81_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave81_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave81_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave81_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave81.",
    },
    {
        "frontier_id": "wave82_exploration_baseline_closure_writeback",
        "module_path": "src/wave82_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave82_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave82_exploration_baseline_closure_writeback after Wave81 chain.",
    },
    {
        "frontier_id": "wave82_demo_presentation_writeback",
        "module_path": "src/demo_wave82_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave82_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave82_presentation_writeback after Wave82 closure writeback.",
    },
    {
        "frontier_id": "wave82_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave82_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave82_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave82_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave82.",
    },
    {
        "frontier_id": "wave83_exploration_baseline_closure_writeback",
        "module_path": "src/wave83_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave83_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave83_exploration_baseline_closure_writeback after Wave82 chain.",
    },
    {
        "frontier_id": "wave83_demo_presentation_writeback",
        "module_path": "src/demo_wave83_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave83_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave83_presentation_writeback after Wave83 closure writeback.",
    },
    {
        "frontier_id": "wave83_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave83_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave83_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave83_external_validation_narrow_slice_coordination_writeback after demo wave83.",
    },
    {
        "frontier_id": "wave84_exploration_baseline_closure_writeback",
        "module_path": "src/wave84_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave84_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave84_exploration_baseline_closure_writeback after Wave83 chain.",
    },
    {
        "frontier_id": "wave84_demo_presentation_writeback",
        "module_path": "src/demo_wave84_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave84_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave84_presentation_writeback after Wave84 closure writeback.",
    },
    {
        "frontier_id": "wave84_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave84_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave84_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave84_meeteval_official_narrow_dry_run_coordination_writeback after demo wave84.",
    },
    {
        "frontier_id": "wave85_exploration_baseline_closure_writeback",
        "module_path": "src/wave85_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave85_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave85_exploration_baseline_closure_writeback after Wave84 chain.",
    },
    {
        "frontier_id": "wave85_demo_presentation_writeback",
        "module_path": "src/demo_wave85_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave85_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave85_presentation_writeback after Wave85 closure writeback.",
    },
    {
        "frontier_id": "wave85_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave85_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave85_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave85_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave85.",
    },
    {
        "frontier_id": "wave86_exploration_baseline_closure_writeback",
        "module_path": "src/wave86_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave86_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave86_exploration_baseline_closure_writeback after Wave85 chain.",
    },
    {
        "frontier_id": "wave86_demo_presentation_writeback",
        "module_path": "src/demo_wave86_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave86_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave86_presentation_writeback after Wave86 closure writeback.",
    },
    {
        "frontier_id": "wave86_speaker_profile_midoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave86_speaker_profile_midoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave86_speaker_profile_midoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave86_speaker_profile_midoverlap_diagnostic_coordination_writeback after demo wave86.",
    },
    {
        "frontier_id": "wave87_exploration_baseline_closure_writeback",
        "module_path": "src/wave87_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave87_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave87_exploration_baseline_closure_writeback after Wave86 chain.",
    },
    {
        "frontier_id": "wave87_demo_presentation_writeback",
        "module_path": "src/demo_wave87_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave87_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave87_presentation_writeback after Wave87 closure writeback.",
    },
    {
        "frontier_id": "wave87_speaker_profile_heavyoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave87_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave87_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave87_speaker_profile_heavyoverlap_diagnostic_coordination_writeback after demo wave87.",
    },
    {
        "frontier_id": "wave88_exploration_baseline_closure_writeback",
        "module_path": "src/wave88_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave88_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave88_exploration_baseline_closure_writeback after Wave87 chain.",
    },
    {
        "frontier_id": "wave88_demo_presentation_writeback",
        "module_path": "src/demo_wave88_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave88_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave88_presentation_writeback after Wave88 closure writeback.",
    },
    {
        "frontier_id": "wave88_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave88_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave88_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave88_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback after demo wave88.",
    },
    {
        "frontier_id": "wave89_exploration_baseline_closure_writeback",
        "module_path": "src/wave89_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave89_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave89_exploration_baseline_closure_writeback after Wave88 chain.",
    },
    {
        "frontier_id": "wave89_demo_presentation_writeback",
        "module_path": "src/demo_wave89_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave89_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave89_presentation_writeback after Wave89 closure writeback.",
    },
    {
        "frontier_id": "wave89_external_validation_narrow_slice_coordination_writeback",
        "module_path": "src/wave89_external_validation_narrow_slice_coordination_writeback.py",
        "expected_output": "results/tables/wave89_external_validation_narrow_slice_coordination_writeback.json",
        "next_step": "Run python -m src.wave89_external_validation_narrow_slice_coordination_writeback after demo wave89.",
    },
    {
        "frontier_id": "wave90_exploration_baseline_closure_writeback",
        "module_path": "src/wave90_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave90_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave90_exploration_baseline_closure_writeback after Wave89 chain.",
    },
    {
        "frontier_id": "wave90_demo_presentation_writeback",
        "module_path": "src/demo_wave90_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave90_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave90_presentation_writeback after Wave90 closure writeback.",
    },
    {
        "frontier_id": "wave90_meeteval_official_narrow_dry_run_coordination_writeback",
        "module_path": "src/wave90_meeteval_official_narrow_dry_run_coordination_writeback.py",
        "expected_output": "results/tables/wave90_meeteval_official_narrow_dry_run_coordination_writeback.json",
        "next_step": "Run python -m src.wave90_meeteval_official_narrow_dry_run_coordination_writeback after demo wave90.",
    },
    {
        "frontier_id": "wave91_exploration_baseline_closure_writeback",
        "module_path": "src/wave91_exploration_baseline_closure_writeback.py",
        "expected_output": "results/tables/wave91_exploration_baseline_closure_writeback.json",
        "next_step": "Run python -m src.wave91_exploration_baseline_closure_writeback after Wave90 chain.",
    },
    {
        "frontier_id": "wave91_demo_presentation_writeback",
        "module_path": "src/demo_wave91_presentation_writeback.py",
        "expected_output": "results/tables/demo_wave91_presentation_writeback.json",
        "next_step": "Run python -m src.demo_wave91_presentation_writeback after Wave91 closure writeback.",
    },
    {
        "frontier_id": "wave91_speaker_profile_lightoverlap_diagnostic_coordination_writeback",
        "module_path": "src/wave91_speaker_profile_lightoverlap_diagnostic_coordination_writeback.py",
        "expected_output": "results/tables/wave91_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json",
        "next_step": "Run python -m src.wave91_speaker_profile_lightoverlap_diagnostic_coordination_writeback after demo wave91.",
    },
]


def exists(rel_path: str) -> bool:
    return (PROJECT_ROOT / rel_path).exists()


def inspect_gold_cases() -> dict[str, bool]:
    ref_path = PROJECT_ROOT / "references" / "reference_transcripts.json"
    if not ref_path.exists():
        return {case: False for case in GOLD_CASES}
    try:
        data = json.loads(ref_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {case: False for case in GOLD_CASES}
    if not isinstance(data, dict):
        return {case: False for case in GOLD_CASES}

    # The file may be stored either as a direct case_id -> record mapping or under a nested "cases" key.
    cases = data.get("cases", {})
    if not isinstance(cases, dict) or not cases:
        cases = data

    result: dict[str, bool] = {}
    for case in GOLD_CASES:
        entry = cases.get(case)
        if isinstance(entry, dict):
            result[case] = str(entry.get("status", "")).strip() == "verified_reference"
        else:
            result[case] = False
    return result


def inspect_synthetic_separation() -> dict[str, str]:
    if (PROJECT_ROOT / "resources" / "synthetic_overlap").exists():
        return {"status": "synthetic_overlap"}
    if (PROJECT_ROOT / "resources" / "synthetic_overlap_v2").exists():
        return {"status": "synthetic_overlap_v2"}
    return {"status": "missing"}


def module_delivery_status(module_path: str, output_path: str) -> str:
    if not exists(module_path):
        return "module_missing"
    if exists(output_path):
        return "module_delivered"
    return "module_present"


def build_wave_frontier_status_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for module in WAVE_FRONTIER_MODULES:
        module_path = str(module["module_path"])
        output_path = str(module["expected_output"])
        rows.append(
            {
                "frontier_id": str(module["frontier_id"]),
                "status": module_delivery_status(module_path, output_path),
                "evidence_path": module_path,
                "expected_output": output_path,
                "next_step": str(module["next_step"]),
            }
        )
    return rows


def build_frontier_status_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for frontier in FRONTIER_SKILLS:
        evidence_path = str(frontier["evidence_path"])
        rows.append(
            {
                "frontier_id": str(frontier["frontier_id"]),
                "status": "documented_skill" if exists(evidence_path) else "missing_skill",
                "evidence_path": evidence_path,
                "expected_output": str(frontier["expected_output"]),
                "next_step": str(frontier["next_step"]),
            }
        )
    rows.extend(build_wave_frontier_status_rows())
    return rows


def frontier_priority(frontier_id: str) -> int:
    if frontier_id.startswith("wave1_"):
        return 60
    if frontier_id.startswith("wave2_"):
        return 61
    if frontier_id.startswith("wave3_"):
        return 62
    if frontier_id.startswith("wave4_"):
        return 63
    if frontier_id.startswith("wave5_"):
        return 64
    if frontier_id.startswith("wave6_"):
        return 65
    if frontier_id.startswith("wave7_"):
        return 66
    if frontier_id.startswith("wave8_"):
        return 67
    if frontier_id.startswith("wave9_"):
        return 68
    if frontier_id.startswith("wave10_"):
        return 69
    if frontier_id.startswith("wave11_"):
        return 70
    if frontier_id.startswith("wave12_"):
        return 71
    if frontier_id.startswith("wave13_"):
        return 72
    if frontier_id.startswith("wave14_"):
        return 73
    if frontier_id.startswith("wave15_"):
        return 74
    if frontier_id.startswith("wave16_"):
        return 75
    if frontier_id.startswith("wave17_"):
        return 76
    priority_order = {
        "meeteval_compatibility": 1,
        "external_validation": 2,
        "speaker_profile": 3,
        "llm_critic": 4,
        "demo_excellence": 5,
    }
    return priority_order.get(frontier_id, 99)


def build_frontier_execution_queue_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    sorted_rows = sorted(rows, key=lambda row: (frontier_priority(str(row.get("frontier_id", ""))), str(row.get("frontier_id", ""))))
    queue_rows: list[dict[str, str]] = []
    for index, row in enumerate(sorted_rows, start=1):
        frontier_id = str(row.get("frontier_id", ""))
        next_step = str(row.get("next_step", ""))
        why_now = next_step
        queue_rows.append(
            {
                "queue_order": str(index),
                "frontier_id": frontier_id,
                "status": str(row.get("status", "")),
                "entry_artifact": str(row.get("expected_output", "")),
                "why_now": why_now,
            }
        )
    return queue_rows


def build_frontier_execution_queue_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue",
        "",
        "This generated queue orders the next breadth-first frontier moves without claiming that the queued work has already been completed.",
        "",
        "| queue_order | frontier_id | status | entry_artifact | why_now |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['status']} | {row['entry_artifact']} | {row['why_now']} |"
        )
    return lines


def build_frontier_execution_queue_checklist_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    checklist_rows: list[dict[str, str]] = []
    for row in rows:
        frontier_id = str(row.get("frontier_id", ""))
        checklist_rows.append(
            {
                "checklist_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "entry_artifact": str(row.get("entry_artifact", "")),
                "why_now": str(row.get("why_now", "")),
                "checklist_goal": f"Verify the execution queue entry for {frontier_id} before opening the next frontier artifact.",
                "queue_note": "Read the queue order first, then keep the entry artifact and why-now note visible while you confirm priority.",
                "next_gate": "Confirm this queue row before moving to the next frontier entry.",
            }
        )
    return checklist_rows


def build_frontier_execution_queue_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Checklist",
        "",
        "This generated checklist turns the execution queue into a row-by-row verification path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | entry_artifact | why_now | checklist_goal | queue_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['why_now']} | {row['checklist_goal']} | {row['queue_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_status_checklist_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    checklist_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        frontier_id = str(row.get("frontier_id", ""))
        checklist_rows.append(
            {
                "checklist_order": str(index),
                "frontier_id": frontier_id,
                "status": str(row.get("status", "")),
                "evidence_path": str(row.get("evidence_path", "")),
                "expected_output": str(row.get("expected_output", "")),
                "next_step": str(row.get("next_step", "")),
                "checklist_goal": f"Verify the frontier status entry for {frontier_id} before it is converted into queue order.",
                "status_note": "Read the evidence path first, then confirm the expected output and next step before advancing.",
                "next_gate": "Confirm this status row before building the execution queue.",
            }
        )
    return checklist_rows


def build_frontier_status_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Status Checklist",
        "",
        "This generated checklist turns the frontier status table into a row-by-row verification path. It remains coordination-only and does not claim any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | status | evidence_path | expected_output | next_step | checklist_goal | status_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['status']} | {row['evidence_path']} | {row['expected_output']} | {row['next_step']} | {row['checklist_goal']} | {row['status_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_focus_card_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    head = rows[0]
    return [
        {
            "queue_order": str(head.get("queue_order", "")),
            "current_frontier": str(head.get("frontier_id", "")),
            "entry_artifact": str(head.get("entry_artifact", "")),
            "current_action": str(head.get("why_now", "")),
        }
    ]


def build_frontier_focus_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Focus Card",
        "",
        "This generated card highlights the single current breadth-first frontier starting point.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"- Queue order: `{row['queue_order']}`",
                f"- Current frontier: `{row['current_frontier']}`",
                f"- Entry artifact: `{row['entry_artifact']}`",
                f"- Current action: {row['current_action']}",
            ]
        )
    return lines


def build_frontier_focus_card_checklist_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    head = rows[0]
    frontier_id = str(head.get("current_frontier", ""))
    return [
        {
            "checklist_order": str(head.get("queue_order", "")),
            "current_frontier": frontier_id,
            "entry_artifact": str(head.get("entry_artifact", "")),
            "current_action": str(head.get("current_action", "")),
            "checklist_goal": f"Confirm the current focus card for {frontier_id} before reading farther.",
            "focus_note": "Read the queue head first, then keep the entry artifact and current action visible while you decide the next pass.",
            "next_gate": "Confirm the focus card snapshot before moving to the next frontier.",
        }
    ]


def build_frontier_focus_card_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Focus Card Checklist",
        "",
        "This generated checklist turns the focus card into a one-glance verification path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | entry_artifact | current_action | checklist_goal | focus_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['entry_artifact']} | {row['current_action']} | {row['checklist_goal']} | {row['focus_note']} | {row['next_gate']} |"
        )
    return lines


def frontier_next_artifact(frontier_id: str) -> tuple[str, str]:
    mapping = {
        "meeteval_compatibility": (
            "results/figures/meeteval_cpwer_bridge_handoff.md",
            "results/tables/meeteval_cpwer_bridge_receipt.json",
        ),
        "external_validation": (
            "results/figures/external_validation_prioritization.md",
            "results/tables/external_validation_slice_receipt.json",
        ),
        "speaker_profile": (
            "results/figures/speaker_profile_triage.md",
            "results/tables/speaker_profile_method_receipt.json",
        ),
        "llm_critic": (
            "results/figures/llm_critic_review_queue.md",
            "results/tables/llm_critic_review_receipt.json",
        ),
        "demo_excellence": (
            "results/figures/demo_walkthrough.md",
            "results/tables/demo_walkthrough_receipt.json",
        ),
    }
    return mapping.get(frontier_id, ("", ""))


FRONTIER_RECEIPT_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "preflight_step",
    "next_gate",
]

FRONTIER_PICKLIST_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "parallelism_note",
    "next_gate",
]

FRONTIER_RECEIPT_BOARD_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "board_note",
    "next_gate",
]

FRONTIER_HANDOFF_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "next_artifact",
    "receipt_target",
    "checklist_goal",
    "execution_intent",
    "next_gate",
]

FRONTIER_COORDINATION_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "entry_artifact",
    "pickup_artifact",
    "receipt_target",
    "checklist_goal",
    "coordination_note",
    "next_gate",
]

FRONTIER_WRITEBACK_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "entry_artifact",
    "receipt_target",
    "checklist_goal",
    "writeback_note",
    "next_gate",
]

FRONTIER_FOCUS_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "entry_artifact",
    "current_action",
    "checklist_goal",
    "focus_note",
    "next_gate",
]

FRONTIER_QUEUE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "entry_artifact",
    "why_now",
    "checklist_goal",
    "queue_note",
    "next_gate",
]

FRONTIER_STATUS_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_id",
    "status",
    "evidence_path",
    "expected_output",
    "next_step",
    "checklist_goal",
    "status_note",
    "next_gate",
]


def build_frontier_handoff_packet_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    next_artifact, expected_evidence = frontier_next_artifact(frontier_id)
    return [
        {
            "queue_order": str(head.get("queue_order", "")),
            "current_frontier": frontier_id,
            "next_artifact": next_artifact,
            "execution_intent": f"Run a single narrow dry run handoff step for {frontier_id} before any broader claim.",
            "expected_evidence": expected_evidence,
            "handoff_scope": "Coordination-only packet; not a claim of completed frontier execution.",
        }
    ]


def build_frontier_handoff_packet_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Handoff Packet",
        "",
        "This generated packet points the current frontier queue head at the single next artifact to open. It does not claim that the frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | next_artifact | execution_intent | expected_evidence | handoff_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['next_artifact']} | {row['execution_intent']} | {row['expected_evidence']} | {row['handoff_scope']} |"
        )
    return lines


def build_frontier_handoff_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    next_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "next_artifact": next_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the handoff packet to stage the next frontier pass for {frontier_id}.",
            "execution_intent": "Open the next artifact first, then keep the receipt target visible for the narrow follow-up step.",
            "next_gate": "Confirm the handoff packet snapshot before advancing the queue.",
        }
    ]


def build_frontier_handoff_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Handoff Checklist",
        "",
        "This generated checklist turns the handoff packet into an ordered open-artifact path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | next_artifact | receipt_target | checklist_goal | execution_intent | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['next_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['execution_intent']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_packet_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "current_frontier": frontier_id,
            "prerequisite_artifact": prerequisite_artifact,
            "receipt_target": receipt_target,
            "execution_note": "Open the handoff first, then write back to the receipt target after the narrow next step.",
            "packet_scope": "Coordination-only packet; not a claim of completed frontier execution.",
        }
    ]


def build_frontier_receipt_packet_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Packet",
        "",
        "This generated packet points the current frontier queue head at its receipt-level writeback target. It does not claim that the frontier work has already been executed.",
        "",
        "| current_frontier | prerequisite_artifact | receipt_target | execution_note | packet_scope |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['execution_note']} | {row['packet_scope']} |"
        )
    return lines


def build_frontier_receipt_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "prerequisite_artifact": prerequisite_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Write back the receipt for {frontier_id} before any broader frontier claim.",
            "preflight_step": "Open the prerequisite artifact and confirm the receipt target before the writeback step.",
            "next_gate": "Fill the receipt target and confirm the frontier writeback before advancing the queue.",
        }
    ]


def build_frontier_receipt_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Checklist",
        "",
        "This generated checklist turns the frontier receipt packet into an ordered writeback path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | prerequisite_artifact | receipt_target | checklist_goal | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_map_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    map_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        prerequisite_artifact, receipt_target = frontier_next_artifact(frontier_id)
        map_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "current_frontier": frontier_id,
                "prerequisite_artifact": prerequisite_artifact,
                "receipt_target": receipt_target,
                "map_note": "Open the prerequisite artifact first, then use the receipt target for writeback.",
                "map_scope": "Coordination-only map; not a claim of completed frontier execution.",
            }
        )
    return map_rows


def build_frontier_receipt_map_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Map",
        "",
        "This generated map shows the receipt path for each current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | prerequisite_artifact | receipt_target | map_note | map_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['map_note']} | {row['map_scope']} |"
        )
    return lines


FRONTIER_RECEIPT_MAP_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "map_note",
    "next_gate",
]


def build_frontier_receipt_map_checklist_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    checklist_rows: list[dict[str, str]] = []
    for row in rows:
        frontier_id = str(row.get("current_frontier", ""))
        checklist_rows.append(
            {
                "checklist_order": str(row.get("queue_order", "")),
                "current_frontier": frontier_id,
                "prerequisite_artifact": str(row.get("prerequisite_artifact", "")),
                "receipt_target": str(row.get("receipt_target", "")),
                "checklist_goal": f"Verify the receipt map entry for {frontier_id} before opening the next frontier artifact.",
                "map_note": str(row.get("map_note", "")),
                "next_gate": "Confirm this map row before moving to the next receipt path.",
            }
        )
    return checklist_rows


def build_frontier_receipt_map_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Map Checklist",
        "",
        "This generated checklist turns the receipt map into a row-by-row verification path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | prerequisite_artifact | receipt_target | checklist_goal | map_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['map_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_parallel_picklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    picklist_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        picklist_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "current_frontier": frontier_id,
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "pickup_note": "Safe to pick up in parallel after checking queue order and opening the pickup artifact first.",
                "picklist_scope": "Coordination-only picklist; not a claim of completed frontier execution.",
            }
        )
    return picklist_rows


def build_frontier_parallel_picklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Parallel Picklist",
        "",
        "This generated picklist shows which current frontiers can be picked up independently while keeping the breadth-first queue visible. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | current_frontier | pickup_artifact | receipt_target | pickup_note | picklist_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['current_frontier']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['pickup_note']} | {row['picklist_scope']} |"
        )
    return lines


def build_frontier_parallel_picklist_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "current_frontier": frontier_id,
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Pick up {frontier_id} in parallel only after confirming queue order.",
            "parallelism_note": "Check the queue head first, then open the pickup artifact before any parallel action.",
            "next_gate": "Complete the pickup artifact and keep the receipt target visible for writeback.",
        }
    ]


def build_frontier_parallel_picklist_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Parallel Picklist Checklist",
        "",
        "This generated checklist turns the parallel picklist into an ordered pickup path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | current_frontier | pickup_artifact | receipt_target | checklist_goal | parallelism_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['current_frontier']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['parallelism_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_receipt_board_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    board_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        board_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "board_status": str(row.get("status", "")),
                "board_note": "Use this board as the single breadth-first receipt snapshot before moving to the next queue head.",
                "board_scope": "Coordination-only board; not a claim of completed frontier execution.",
            }
        )
    return board_rows


def build_frontier_receipt_board_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Board",
        "",
        "This generated board consolidates the current frontier queue, pickup artifact, and receipt target into one breadth-first snapshot. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | pickup_artifact | receipt_target | board_status | board_note | board_scope |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['board_status']} | {row['board_note']} | {row['board_scope']} |"
        )
    return lines


def build_frontier_receipt_board_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the receipt board to stage the next frontier pass for {frontier_id}.",
            "board_note": "Open the board snapshot first, then keep the pickup artifact visible while writing back.",
            "next_gate": "Confirm the board snapshot and receipt target before the next queue head advances.",
        }
    ]


def build_frontier_receipt_board_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Receipt Board Checklist",
        "",
        "This generated checklist turns the receipt board into an ordered snapshot path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | pickup_artifact | receipt_target | checklist_goal | board_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['board_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_coordination_matrix_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    matrix_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        matrix_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "status": str(row.get("status", "")),
                "entry_artifact": str(row.get("entry_artifact", "")),
                "pickup_artifact": pickup_artifact,
                "receipt_target": receipt_target,
                "coordination_note": "Coordinate this frontier by opening the pickup artifact first and writing back to the receipt target after the narrow next step.",
                "coordination_scope": "Coordination-only matrix; not a claim of completed frontier execution.",
            }
        )
    return matrix_rows


def build_frontier_coordination_matrix_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Coordination Matrix",
        "",
        "This generated matrix combines queue order, entry artifact, pickup artifact, and receipt target for every current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | status | entry_artifact | pickup_artifact | receipt_target | coordination_note | coordination_scope |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['status']} | {row['entry_artifact']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['coordination_note']} | {row['coordination_scope']} |"
        )
    return lines


def build_frontier_coordination_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "entry_artifact": str(head.get("entry_artifact", "")),
            "pickup_artifact": pickup_artifact,
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the coordination matrix to stage the next frontier pass for {frontier_id}.",
            "coordination_note": "Open the entry artifact first, then keep the pickup artifact and receipt target visible for the next step.",
            "next_gate": "Confirm the coordination matrix snapshot before advancing the queue.",
        }
    ]


def build_frontier_coordination_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Coordination Checklist",
        "",
        "This generated checklist turns the coordination matrix into an ordered scan path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | entry_artifact | pickup_artifact | receipt_target | checklist_goal | coordination_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['pickup_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['coordination_note']} | {row['next_gate']} |"
        )
    return lines


def build_frontier_writeback_index_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    index_rows: list[dict[str, str]] = []
    for row in queue_rows:
        frontier_id = str(row.get("frontier_id", ""))
        pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
        index_rows.append(
            {
                "queue_order": str(row.get("queue_order", "")),
                "frontier_id": frontier_id,
                "entry_artifact": str(row.get("entry_artifact", "")),
                "receipt_target": receipt_target,
                "writeback_note": f"Open {pickup_artifact} first, then write back to {receipt_target}.",
                "writeback_scope": "Coordination-only index; not a claim of completed frontier execution.",
            }
        )
    return index_rows


def build_frontier_writeback_index_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Writeback Index",
        "",
        "This generated index isolates the writeback target for each current frontier. It does not claim that any frontier work has already been executed.",
        "",
        "| queue_order | frontier_id | entry_artifact | receipt_target | writeback_note | writeback_scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['receipt_target']} | {row['writeback_note']} | {row['writeback_scope']} |"
        )
    return lines


def build_frontier_writeback_checklist_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not queue_rows:
        return []

    head = queue_rows[0]
    frontier_id = str(head.get("frontier_id", ""))
    pickup_artifact, receipt_target = frontier_next_artifact(frontier_id)
    return [
        {
            "checklist_order": "1",
            "frontier_id": frontier_id,
            "entry_artifact": str(head.get("entry_artifact", "")),
            "receipt_target": receipt_target,
            "checklist_goal": f"Use the writeback index to complete the frontier writeback path for {frontier_id}.",
            "writeback_note": f"Open {pickup_artifact} first, then write back to {receipt_target} after the narrow next step.",
            "next_gate": "Confirm the writeback index snapshot before advancing the queue.",
        }
    ]


def build_frontier_writeback_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Writeback Checklist",
        "",
        "This generated checklist turns the writeback index into an ordered closeout path. It remains coordination-only and does not claim that any frontier work has already been executed.",
        "",
        "| checklist_order | frontier_id | entry_artifact | receipt_target | checklist_goal | writeback_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_id']} | {row['entry_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['writeback_note']} | {row['next_gate']} |"
        )
    return lines


def write_frontier_coordination_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_coordination_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_coordination_checklist.csv"
    json_path = tables_dir / "frontier_coordination_checklist.json"
    md_path = figures_dir / "frontier_coordination_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_COORDINATION_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_coordination_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_writeback_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_writeback_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_writeback_checklist.csv"
    json_path = tables_dir / "frontier_writeback_checklist.json"
    md_path = figures_dir / "frontier_writeback_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_WRITEBACK_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_writeback_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def build_report() -> dict[str, object]:
    missing_core = [path for path in CORE_FILES if not exists(path)]
    gold_status = inspect_gold_cases()
    synthetic_status = inspect_synthetic_separation()
    frontier_status = build_frontier_status_rows()
    report = {
        "project_root": ".",
        "core_files_present": len(missing_core) == 0,
        "missing_core_files": missing_core,
        "gold_cases": gold_status,
        "synthetic_status": synthetic_status,
        "gold_and_synthetic_separated": synthetic_status["status"] in {"synthetic_overlap", "synthetic_overlap_v2"},
        "frontier_status": frontier_status,
    }
    return report


def write_report(report: dict[str, object]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    json_path = tables_dir / "project_harness_report.json"
    md_path = figures_dir / "project_harness_report.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_lines = []
    for case, ok in report["gold_cases"].items():
        gold_lines.append(f"- {case}: {'present' if ok else 'missing'}")

    lines = [
        "# Project Harness Report",
        "",
        "## Core Files",
        "",
        f"- core_files_present: {report['core_files_present']}",
        "",
        "### Missing Core Files",
    ]
    missing = report["missing_core_files"]
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Gold Cases",
        "",
    ] + gold_lines + [
        "",
        "## Synthetic Separation",
        "",
        f"- status: {report['synthetic_status']['status']}",
        f"- gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}",
        "",
        "## Frontier Status",
        "",
        "| frontier_id | status | evidence_path | expected_output | next_step |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["frontier_status"]:
        lines.append(
            f"| {row['frontier_id']} | {row['status']} | {row['evidence_path']} | {row['expected_output']} | {row['next_step']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The repository keeps gold references and synthetic resources separate.",
        "- The core maintenance files are in place for future agents.",
        "- The frontier status table makes breadth-first experimental directions visible, including delivered Wave1/Wave2 frontier modules.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_status_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    checklist_rows = build_frontier_status_checklist_rows(frontier_status)
    csv_path = tables_dir / "frontier_status_checklist.csv"
    json_path = tables_dir / "frontier_status_checklist.json"
    md_path = figures_dir / "frontier_status_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_STATUS_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_status_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_queue(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    json_path = tables_dir / "frontier_execution_queue.json"
    md_path = figures_dir / "frontier_execution_queue.md"
    json_path.write_text(json.dumps(queue_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_execution_queue_lines(queue_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_execution_queue_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_execution_queue_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_execution_queue_checklist.csv"
    json_path = tables_dir / "frontier_execution_queue_checklist.json"
    md_path = figures_dir / "frontier_execution_queue_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_QUEUE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_execution_queue_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_focus_card(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    focus_rows = build_frontier_focus_card_rows(queue_rows)
    json_path = tables_dir / "frontier_focus_card.json"
    md_path = figures_dir / "frontier_focus_card.md"
    json_path.write_text(json.dumps(focus_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_focus_card_lines(focus_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_focus_card_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    focus_rows = build_frontier_focus_card_rows(queue_rows)
    checklist_rows = build_frontier_focus_card_checklist_rows(focus_rows)
    csv_path = tables_dir / "frontier_focus_card_checklist.csv"
    json_path = tables_dir / "frontier_focus_card_checklist.json"
    md_path = figures_dir / "frontier_focus_card_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_FOCUS_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_focus_card_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_handoff_packet(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    handoff_rows = build_frontier_handoff_packet_rows(queue_rows)
    json_path = tables_dir / "frontier_handoff_packet.json"
    md_path = figures_dir / "frontier_handoff_packet.md"
    json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_handoff_packet_lines(handoff_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_packet(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    receipt_rows = build_frontier_receipt_packet_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_packet.json"
    md_path = figures_dir / "frontier_receipt_packet.md"
    json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_packet_lines(receipt_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_receipt_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_receipt_checklist.csv"
    json_path = tables_dir / "frontier_receipt_checklist.json"
    md_path = figures_dir / "frontier_receipt_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_RECEIPT_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_handoff_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_handoff_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_handoff_checklist.csv"
    json_path = tables_dir / "frontier_handoff_checklist.json"
    md_path = figures_dir / "frontier_handoff_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_HANDOFF_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_handoff_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_parallel_picklist_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_parallel_picklist_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_parallel_picklist_checklist.csv"
    json_path = tables_dir / "frontier_parallel_picklist_checklist.json"
    md_path = figures_dir / "frontier_parallel_picklist_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_PICKLIST_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_parallel_picklist_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_receipt_map(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    receipt_map_rows = build_frontier_receipt_map_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_map.json"
    md_path = figures_dir / "frontier_receipt_map.md"
    json_path.write_text(json.dumps(receipt_map_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_map_lines(receipt_map_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_map_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    receipt_map_rows = build_frontier_receipt_map_rows(queue_rows)
    checklist_rows = build_frontier_receipt_map_checklist_rows(receipt_map_rows)
    csv_path = tables_dir / "frontier_receipt_map_checklist.csv"
    json_path = tables_dir / "frontier_receipt_map_checklist.json"
    md_path = figures_dir / "frontier_receipt_map_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_RECEIPT_MAP_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_map_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_parallel_picklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    picklist_rows = build_frontier_parallel_picklist_rows(queue_rows)
    json_path = tables_dir / "frontier_parallel_picklist.json"
    md_path = figures_dir / "frontier_parallel_picklist.md"
    json_path.write_text(json.dumps(picklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_parallel_picklist_lines(picklist_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_board(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    board_rows = build_frontier_receipt_board_rows(queue_rows)
    json_path = tables_dir / "frontier_receipt_board.json"
    md_path = figures_dir / "frontier_receipt_board.md"
    json_path.write_text(json.dumps(board_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_board_lines(board_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_receipt_board_checklist(frontier_status: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    checklist_rows = build_frontier_receipt_board_checklist_rows(queue_rows)
    csv_path = tables_dir / "frontier_receipt_board_checklist.csv"
    json_path = tables_dir / "frontier_receipt_board_checklist.json"
    md_path = figures_dir / "frontier_receipt_board_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_RECEIPT_BOARD_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_receipt_board_checklist_lines(checklist_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def write_frontier_coordination_matrix(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    matrix_rows = build_frontier_coordination_matrix_rows(queue_rows)
    json_path = tables_dir / "frontier_coordination_matrix.json"
    md_path = figures_dir / "frontier_coordination_matrix.md"
    json_path.write_text(json.dumps(matrix_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_coordination_matrix_lines(matrix_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def write_frontier_writeback_index(frontier_status: list[dict[str, str]]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    queue_rows = build_frontier_execution_queue_rows(frontier_status)
    index_rows = build_frontier_writeback_index_rows(queue_rows)
    json_path = tables_dir / "frontier_writeback_index.json"
    md_path = figures_dir / "frontier_writeback_index.md"
    json_path.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_writeback_index_lines(index_rows)) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    report = build_report()
    json_path, md_path = write_report(report)
    status_checklist_csv_path, status_checklist_json_path, status_checklist_md_path = write_frontier_status_checklist(report["frontier_status"])
    queue_json_path, queue_md_path = write_frontier_queue(report["frontier_status"])
    queue_checklist_csv_path, queue_checklist_json_path, queue_checklist_md_path = write_frontier_execution_queue_checklist(report["frontier_status"])
    focus_json_path, focus_md_path = write_frontier_focus_card(report["frontier_status"])
    focus_checklist_csv_path, focus_checklist_json_path, focus_checklist_md_path = write_frontier_focus_card_checklist(report["frontier_status"])
    handoff_json_path, handoff_md_path = write_frontier_handoff_packet(report["frontier_status"])
    handoff_checklist_csv_path, handoff_checklist_json_path, handoff_checklist_md_path = write_frontier_handoff_checklist(report["frontier_status"])
    receipt_json_path, receipt_md_path = write_frontier_receipt_packet(report["frontier_status"])
    receipt_checklist_csv_path, receipt_checklist_json_path, receipt_checklist_md_path = write_frontier_receipt_checklist(report["frontier_status"])
    receipt_map_json_path, receipt_map_md_path = write_frontier_receipt_map(report["frontier_status"])
    receipt_map_checklist_csv_path, receipt_map_checklist_json_path, receipt_map_checklist_md_path = write_frontier_receipt_map_checklist(report["frontier_status"])
    parallel_picklist_json_path, parallel_picklist_md_path = write_frontier_parallel_picklist(report["frontier_status"])
    parallel_picklist_checklist_csv_path, parallel_picklist_checklist_json_path, parallel_picklist_checklist_md_path = write_frontier_parallel_picklist_checklist(report["frontier_status"])
    receipt_board_json_path, receipt_board_md_path = write_frontier_receipt_board(report["frontier_status"])
    receipt_board_checklist_csv_path, receipt_board_checklist_json_path, receipt_board_checklist_md_path = write_frontier_receipt_board_checklist(report["frontier_status"])
    coordination_matrix_json_path, coordination_matrix_md_path = write_frontier_coordination_matrix(report["frontier_status"])
    coordination_checklist_csv_path, coordination_checklist_json_path, coordination_checklist_md_path = write_frontier_coordination_checklist(report["frontier_status"])
    writeback_index_json_path, writeback_index_md_path = write_frontier_writeback_index(report["frontier_status"])
    writeback_checklist_csv_path, writeback_checklist_json_path, writeback_checklist_md_path = write_frontier_writeback_checklist(report["frontier_status"])
    print(f"Wrote harness report: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote harness summary: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier status checklist CSV: {status_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier status checklist JSON: {status_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier status checklist note: {status_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue JSON: {queue_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue note: {queue_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue checklist CSV: {queue_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue checklist JSON: {queue_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier queue checklist note: {queue_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus JSON: {focus_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus note: {focus_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus checklist CSV: {focus_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus checklist JSON: {focus_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier focus checklist note: {focus_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff JSON: {handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff note: {handoff_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist CSV: {handoff_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist JSON: {handoff_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier handoff checklist note: {handoff_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist CSV: {receipt_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist JSON: {receipt_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt checklist note: {receipt_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map JSON: {receipt_map_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map note: {receipt_map_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map checklist CSV: {receipt_map_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map checklist JSON: {receipt_map_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt map checklist note: {receipt_map_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist JSON: {parallel_picklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist note: {parallel_picklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist CSV: {parallel_picklist_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist JSON: {parallel_picklist_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier parallel picklist checklist note: {parallel_picklist_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board JSON: {receipt_board_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board note: {receipt_board_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist CSV: {receipt_board_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist JSON: {receipt_board_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier receipt board checklist note: {receipt_board_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination matrix JSON: {coordination_matrix_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination matrix note: {coordination_matrix_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist CSV: {coordination_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist JSON: {coordination_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier coordination checklist note: {coordination_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback index JSON: {writeback_index_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback index note: {writeback_index_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist CSV: {writeback_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist JSON: {writeback_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier writeback checklist note: {writeback_checklist_md_path.relative_to(PROJECT_ROOT)}")
    print(f"gold_cases_present: {all(report['gold_cases'].values())}")
    print(f"gold_and_synthetic_separated: {report['gold_and_synthetic_separated']}")


if __name__ == "__main__":
    main()
