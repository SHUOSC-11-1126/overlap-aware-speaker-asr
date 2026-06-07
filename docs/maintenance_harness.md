# Maintenance Harness

This document describes how to keep the project healthy while still encouraging ambitious experimentation.

## Result Labeling Policy

- gold
- silver
- frontier
- demo
- oracle
- external sanity-check

## Experimental Branch Policy

- Stable outputs remain stable.
- Experimental outputs use versioned paths.
- High-risk ideas are allowed if they are labeled and documented.

## Experiment Proposal Template

Before starting a new experiment, write:

- Question
- Hypothesis
- Method
- Inputs
- Outputs
- Metrics
- Compute cost
- Failure modes
- Owner

## Reproducibility Policy

- Do not overwrite verified references.
- Do not overwrite gold results unless explicitly rerunning a documented stage.
- Prefer versioned outputs for new experimental branches.
- Keep synthetic silver separate from gold.

## Innovation Encouragement

Agents are encouraged to attempt difficult extensions. A failed but well-documented experiment is valuable if it clarifies a boundary or failure mode.

## Documentation Freshness Policy

- Every major stage completion must update `docs/project_state.md`.
- If the core conclusion changes, update `README.md` and `REPORT.md` together.
- If a new experimental branch is added, explicitly label it as `gold`, `silver`, `frontier`, `demo`, or `external`.
- If a new module is not part of the core line, place it in `docs/skills/` or future work.
- Do not promote exploratory results directly into a final claim.
- If contribution records, handoff notes, or backup plans are added, link them from `docs/README.md` and `README.md`.

## Recommended Command Discipline

```powershell
python -m src.adaptive_router_v2
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.evaluate_cpcer_lite --case all
python -m src.risk_aware_selector --case all
python -m src.router_ablation
python -m src.router_ablation_split
python -m src.project_harness
python -m src.frontier_execution_receipt_fill_execution_completion_summary
python -m src.frontier_execution_receipt_fill_execution_completion_summary_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_operator_brief
python -m src.frontier_execution_receipt_fill_execution_receipt_bridge
python -m src.frontier_execution_receipt_fill_execution_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_handoff_packet
python -m src.frontier_execution_receipt_fill_execution_evidence_receipt
python -m src.frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_runbook_card
python -m src.frontier_execution_receipt_fill_execution_completion_dashboard
python -m src.frontier_execution_receipt_fill_execution_milestone_card
python -m src.frontier_execution_receipt_fill_execution_execution_receipt_bridge
python -m src.frontier_execution_receipt_fill_execution_execution_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_phase_checkpoint_card
python -m src.frontier_execution_receipt_fill_execution_runbook_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_frontier_bridge
python -m src.frontier_execution_receipt_fill_execution_frontier_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_dashboard_bridge_checklist
python -m src.meeteval_cpwer_execution_preflight_batch
python -m src.meeteval_cpwer_execution_preflight_batch_bridge_checklist
python -m src.meeteval_cpwer_execution_receipt_batch_scaffold
python -m src.meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist
python -m src.meeteval_cpwer_execution_status_batch
python -m src.meeteval_cpwer_execution_status_batch_bridge_checklist
python -m src.meeteval_cpwer_execution_status_batch_completion_summary
python -m src.meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist
python -m src.meeteval_cpwer_execution_status_batch_handoff
python -m src.meeteval_cpwer_execution_status_batch_handoff_bridge_checklist
python -m src.meeteval_cpwer_official_execution --case preferred
python -m src.frontier_execution_receipt_fill_execution_handoff_bridge_checklist
```

## Maintenance Goal

Healthy experimentation, not restriction.
