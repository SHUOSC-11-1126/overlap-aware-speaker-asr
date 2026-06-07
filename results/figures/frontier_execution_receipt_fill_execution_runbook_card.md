# Frontier Execution Receipt Fill Execution Runbook Card

This generated runbook card condenses the first fill execution action into a one-page execution card. It remains experimental/frontier coordination only and does not claim benchmark execution.

- Recommended frontier: `meeteval_compatibility`
- Recommended action: `Execute the real frontier run, then update execution_status in results/tables/meeteval_cpwer_execution_receipt.json and attach the fill evidence note.`
- Required evidence: `results/figures/frontier_execution_receipt_fill_execution_handoff.md; results/figures/frontier_execution_receipt_fill_execution_handoff_bridge_checklist.md`
- Completion signal: `execution_status in results/tables/meeteval_cpwer_execution_receipt.json is no longer template_only`
- Urgency: 3/3 frontiers awaiting fill execution
- Runbook note: Start with meeteval_compatibility because it is handoff_order=1 and all receipts remain template_only. No benchmark execution is claimed until the execution receipt is filled.
